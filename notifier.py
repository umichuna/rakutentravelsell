import time
import requests

from config import DISCORD_WEBHOOK_URL
from logger import log_error


def notify_price_drop(drop_info: dict, email_address: str | None = None):
    """値下がり通知を Discord（常時）+ Gmail（設定時のみ）で送信"""
    message = build_discord_message(drop_info)
    send_discord(DISCORD_WEBHOOK_URL, message)

    if email_address:
        subject = build_email_subject(drop_info)
        body = build_email_body(drop_info)
        send_gmail_with_retry(email_address, subject, body)


def notify_error(message: str):
    """エラー通知を Discord で送信"""
    send_discord(DISCORD_WEBHOOK_URL, f"❌ エラーが発生しました\n{message}")


def notify_cancel_deadline(hotel_info: dict):
    """キャンセル無料期間の前日通知を Discord で送信"""
    message = build_cancel_deadline_message(hotel_info)
    send_discord(DISCORD_WEBHOOK_URL, message)


def send_discord(webhook_url: str, message: str) -> bool:
    """Discord Webhook でメッセージを送信"""
    for attempt in range(3):
        try:
            response = requests.post(
                webhook_url,
                json={"content": message},
                timeout=10
            )
            if response.status_code == 204:
                return True
            else:
                log_error(f"Discord API error: {response.status_code}")
        except Exception as e:
            log_error(f"Discord send attempt {attempt + 1} failed: {str(e)}")
            if attempt < 2:
                time.sleep(1)
    return False


def send_gmail_with_retry(to_address: str, subject: str, body: str) -> bool:
    """Gmail で送信（GAS Web App 経由）"""
    from config import GAS_GMAIL_WEBHOOK_URL

    if not GAS_GMAIL_WEBHOOK_URL:
        log_error("GAS_GMAIL_WEBHOOK_URL not configured")
        return False

    payload = {
        "to": to_address,
        "subject": subject,
        "body": body
    }

    for attempt in range(3):
        try:
            response = requests.post(
                GAS_GMAIL_WEBHOOK_URL,
                json=payload,
                timeout=15
            )
            data = response.json()
            if data.get("status") == "ok":
                return True
            else:
                log_error(f"GAS Gmail error: {data.get('message', 'Unknown error')}")
        except Exception as e:
            log_error(f"GAS Gmail attempt {attempt + 1} failed: {str(e)}")
            if attempt < 2:
                time.sleep(1)
    return False


def build_discord_message(drop_info: dict) -> str:
    """Discord 用の値下がり通知メッセージを組み立て"""
    return f"""🏨 ホテル価格 値下がり検知
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏩 ホテル名：{drop_info['hotel_name']}
💰 予約価格：{drop_info['reserved_price']:,} 円
📉 現在価格：{drop_info['best_price']:,} 円
💸 差 額：-{drop_info['drop_amount']:,} 円（-{drop_info['drop_percent']}%）
📋 プラン：{drop_info['best_plan_name']}
🔗 ホテル URL：{drop_info['hotel_url']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
予約変更後はスプレッドシートの「予約価格」を更新してください。"""


def build_email_subject(drop_info: dict) -> str:
    """Gmail 用の件名を組み立て"""
    return f"【ホテル価格監視】値下がり検知｜{drop_info['hotel_name']}｜-{drop_info['drop_amount']:,} 円（-{drop_info['drop_percent']}%）"


def build_email_body(drop_info: dict) -> str:
    """Gmail 用の本文を組み立て"""
    return f"""ホテル名 ：{drop_info['hotel_name']}
予約価格 ：{drop_info['reserved_price']:,} 円
現在価格 ：{drop_info['best_price']:,} 円
差額 ：-{drop_info['drop_amount']:,} 円（-{drop_info['drop_percent']}%）
プラン ：{drop_info['best_plan_name']}
ホテル URL ：{drop_info['hotel_url']}

予約変更後はスプレッドシートの「予約価格」欄を
新しい金額に更新してください。"""


def build_cancel_deadline_message(hotel_info: dict) -> str:
    """キャンセル無料期間前日通知の Discord メッセージを組み立て"""
    checkin = hotel_info.get("checkin", "")
    reserved_price = hotel_info.get("reserved_price", "")
    cancel_deadline = hotel_info.get("cancel_deadline", "")

    return f"""⚠️ キャンセル無料期間 明日で終了
──────────────────────────
🏨 ホテル名：{hotel_info['hotel_name']}
📅 キャンセル無料期間最終日：{cancel_deadline}（明日）
📍 チェックイン：{checkin}
💰 予約価格：{reserved_price:,} 円
──────────────────────────
明日以降のキャンセルは有料になります。ご注意ください。"""
