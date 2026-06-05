import time
import requests
from logger import log_error, log_debug

from config import (
    RAKUTEN_APP_ID, RAKUTEN_ACCESS_KEY, RAKUTEN_API_URL, REQUEST_HEADERS,
    REQUEST_TIMEOUT, MAX_RETRY, BREAKFAST_KEYWORDS
)


def fetch_vacant_plans(
    hotel_no: str,
    checkin_date: str,
    checkout_date: str,
    adults: int,
    rooms: int = 1,
    breakfast_required: bool = True
) -> list[dict] | None:
    """
    楽天トラベル空室ホテル検索APIを呼び出し、プラン一覧を返す
    breakfast_required=True の場合は朝食付きプランのみを抽出
    失敗時は None を返す
    """
    params = {
        "applicationId": RAKUTEN_APP_ID,
        "accessKey": RAKUTEN_ACCESS_KEY,
        "hotelNo": hotel_no,
        "checkinDate": checkin_date.replace("/", "-"),
        "checkoutDate": checkout_date.replace("/", "-"),
        "adultNum": adults,
        "roomNum": rooms,
        "hits": 30,
        "format": "json"
    }


    try:
        response = _call_api_with_retry(params)
        if response is None:
            return None

        plans = _extract_breakfast_plans(response, breakfast_required)
        return plans

    except Exception as e:
        log_error(f"fetch_vacant_plans exception: {hotel_no} - {str(e)}")
        return None


def _call_api_with_retry(params: dict) -> dict | None:
    """
    APIを呼び出しリトライロジック付き
    成功時は レスポンスJSON（dict）を返す
    失敗時は None を返す
    """
    for attempt in range(MAX_RETRY):
        try:
            response = requests.get(
                RAKUTEN_API_URL,
                params=params,
                headers=REQUEST_HEADERS,
                timeout=REQUEST_TIMEOUT
            )

            if response.status_code == 429:
                wait_time = 2 ** attempt
                log_debug(f"HTTP 429 Rate Limit - waiting {wait_time} seconds")
                time.sleep(wait_time)
                continue

            if 400 <= response.status_code < 500:
                if response.status_code != 429:
                    log_error(f"HTTP {response.status_code}: {response.text[:100]}")
                    return None

            if 500 <= response.status_code < 600:
                log_debug(f"HTTP {response.status_code} - retrying...")
                if attempt < MAX_RETRY - 1:
                    time.sleep(1)
                    continue
                return None

            if response.status_code == 200:
                return response.json()

        except requests.exceptions.Timeout:
            log_error(f"Request timeout - attempt {attempt + 1}/{MAX_RETRY}")
            if attempt < MAX_RETRY - 1:
                time.sleep(1)
                continue
            return None

        except Exception as e:
            log_error(f"API request error: {str(e)}")
            return None

    return None


def _extract_breakfast_plans(api_response: dict, breakfast_required: bool = True) -> list[dict] | None:
    """
    APIレスポンスからプラン情報を抽出
    roomInfo内のroomBasicInfoとdailyChargeは別要素として交互に並んでいる
    breakfast_required=True の場合は withBreakfastFlag=1 またはキーワード一致で絞り込み
    """
    try:
        if "hotels" not in api_response or not api_response["hotels"]:
            return None

        plans = []

        for hotel_data in api_response["hotels"]:
            if "hotel" not in hotel_data or not hotel_data["hotel"]:
                continue

            for hotel_info in hotel_data["hotel"]:
                if "roomInfo" not in hotel_info:
                    continue

                room_items = hotel_info["roomInfo"]

                # roomBasicInfo と dailyCharge は交互に並んでいる
                # roomBasicInfo を先に収集し、対応する dailyCharge とペアにする
                basic_info = None
                for item in room_items:
                    if "roomBasicInfo" in item:
                        basic_info = item["roomBasicInfo"]
                    elif "dailyCharge" in item and basic_info is not None:
                        daily_charge = item["dailyCharge"]
                        plan_name = basic_info.get("planName", "")

                        # 価格取得（優先順位: rakutenCharge > total）
                        price = daily_charge.get("rakutenCharge") or daily_charge.get("total")
                        if price is None:
                            basic_info = None
                            continue

                        # 朝食判定: フラグ優先、なければキーワード
                        with_breakfast_flag = basic_info.get("withBreakfastFlag", 0)
                        breakfast_select_flag = basic_info.get("breakfastSelectFlag", 0)
                        has_breakfast = (with_breakfast_flag == 1 or breakfast_select_flag == 1
                                         or _check_breakfast(plan_name))

                        if breakfast_required and not has_breakfast:
                            basic_info = None
                            continue

                        plans.append({
                            "price": int(price),
                            "plan_name": plan_name,
                            "has_breakfast": has_breakfast
                        })
                        basic_info = None

        plans.sort(key=lambda x: x["price"])
        return plans  # 空リスト [] も正常（朝食プランなし）

    except Exception as e:
        log_error(f"Error parsing API response: {str(e)}")
        return None


def _check_breakfast(plan_name: str) -> bool:
    """planNameに朝食判定キーワードが含まれているかチェック"""
    plan_lower = plan_name.lower()
    for keyword in BREAKFAST_KEYWORDS:
        if keyword.lower() in plan_lower:
            return True
    return False
