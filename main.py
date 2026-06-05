from config import validate_config
from logger import log_info, log_error, get_jst_now, format_jst_timestamp
from sheets import (
    get_gspread_client, get_config, get_hotels, update_hotel_prices,
    append_log
)
from rakuten_api import fetch_vacant_plans
from price_checker import check_price_drop, get_min_price
from sale_checker import is_cancel_deadline_tomorrow
from notifier import notify_price_drop, notify_error, notify_cancel_deadline


def main():
    log_info("=" * 50)
    log_info("ホテル価格監視システム開始")
    log_info("=" * 50)

    validate_config()

    try:
        client = get_gspread_client()
        log_info("Google Sheets認証成功")
    except Exception as e:
        log_error(f"Google Sheets認証失敗: {str(e)}")
        notify_error(f"Google Sheets認証失敗: {str(e)}")
        return

    try:
        config = get_config(client)
        log_info("設定シート取得成功")
    except Exception as e:
        log_error(f"設定シート取得失敗: {str(e)}")
        notify_error(f"設定シート取得失敗: {str(e)}")
        return

    # 全体監視有効チェック
    monitoring_enabled = config.get("全体監視有効", "TRUE").upper() == "TRUE"
    if not monitoring_enabled:
        log_info("全体監視が無効です。処理を中止します。")
        return

    email_address = config.get("通知先メールアドレス")
    if email_address and email_address.strip() == "":
        email_address = None

    try:
        hotels = get_hotels(client)
        log_info(f"ホテル一覧取得成功（監視対象数: {len(hotels)}）")
    except Exception as e:
        log_error(f"ホテル一覧取得失敗: {str(e)}")
        notify_error(f"ホテル一覧取得失敗: {str(e)}")
        return

    if not hotels:
        log_info("監視対象ホテルがありません")
        return

    # 処理統計
    total_count = len(hotels)
    success_count = 0
    error_count = 0
    notification_count = 0
    error_messages = []

    # 設定シートから日程を取得
    checkin = config.get("チェックイン日", "")
    checkout = config.get("チェックアウト日", "")
    adults = int(config.get("大人人数", "2") or "2")
    rooms = int(config.get("部屋数", "1") or "1")

    for hotel in hotels:
        try:
            log_info(f"処理中: {hotel['hotel_name']}")

            # ホテル個別の日程があればそれを使い、なければ設定シートのグローバル値を使う
            hotel_checkin = hotel.get("hotel_checkin") or checkin
            hotel_checkout = hotel.get("hotel_checkout") or checkout
            hotel["checkin"] = hotel_checkin
            hotel["checkout"] = hotel_checkout

            # API呼び出し
            plans = fetch_vacant_plans(
                hotel["hotel_no"],
                hotel_checkin,
                hotel_checkout,
                adults,
                rooms,
            )

            # 現在価格・最安価格を取得
            current_price = get_min_price(plans) if plans else None
            jst_now = get_jst_now()
            timestamp_str = jst_now.strftime("%Y/%m/%d %H:%M:%S")

            if plans is None:
                log_error(f"API取得失敗: {hotel['hotel_name']}")
                update_hotel_prices(client, hotel["row_index"], None, None, timestamp_str)
                error_count += 1
                error_messages.append(f"{hotel['hotel_name']}: API取得失敗")
                continue

            if len(plans) == 0:
                log_info(f"プランなし（空室なし）: {hotel['hotel_name']}")
                update_hotel_prices(client, hotel["row_index"], None, None, timestamp_str)
                success_count += 1
                continue

            success_count += 1

            # 価格判定
            drop_info = check_price_drop(hotel, plans)

            if drop_info:
                log_info(f"値下がり検知: {hotel['hotel_name']} (-{drop_info['drop_amount']}円)")
                notify_price_drop(drop_info, email_address)
                notification_count += 1

            # キャンセル無料期間の前日判定
            if hotel.get("reserved") and is_cancel_deadline_tomorrow(hotel.get("cancel_deadline", "")):
                log_info(f"[CANCEL] キャンセル無料期間最終日が明日: {hotel['hotel_name']}")
                notify_cancel_deadline(hotel)
                notification_count += 1

            # スプレッドシート更新
            update_hotel_prices(client, hotel["row_index"], current_price, current_price, timestamp_str)

        except Exception as e:
            log_error(f"ホテル処理エラー: {hotel['hotel_name']} - {str(e)}")
            error_count += 1
            error_messages.append(f"{hotel['hotel_name']}: {str(e)}")

    # 実行ログ記録
    status = "SUCCESS" if error_count == 0 else ("PARTIAL_ERROR" if success_count > 0 else "FAILED")
    log_entry = {
        "timestamp": format_jst_timestamp(),
        "hotel_count": total_count,
        "success_count": success_count,
        "error_count": error_count,
        "notification_count": notification_count,
        "error_detail": "\n".join(error_messages) if error_messages else "",
        "status": status
    }

    try:
        append_log(client, log_entry)
        log_info("実行ログ記録完了")
    except Exception as e:
        log_error(f"実行ログ記録失敗: {str(e)}")

    log_info("=" * 50)
    log_info(f"処理完了 - 成功: {success_count}/{total_count}, 通知: {notification_count}, エラー: {error_count}")
    log_info(f"ステータス: {status}")
    log_info("=" * 50)


if __name__ == "__main__":
    main()
