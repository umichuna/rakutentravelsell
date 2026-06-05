from datetime import datetime, date, timedelta
import pytz


def get_jst_today() -> date:
    """JST の今日の日付を返す"""
    jst = pytz.timezone("Asia/Tokyo")
    return datetime.now(jst).date()


def get_jst_tomorrow() -> date:
    """JST の明日の日付を返す"""
    return get_jst_today() + timedelta(days=1)


def is_zero_or_five_day(target_date: date | None = None) -> bool:
    """日付が5・10・15・20・25・30日か判定"""
    if target_date is None:
        target_date = get_jst_today()

    day = target_date.day
    return day in [5, 10, 15, 20, 25, 30]


def should_notify_05_day() -> bool:
    """当日または前日が5/0のつく日なら True"""
    today = get_jst_today()
    tomorrow = today + timedelta(days=1)

    return is_zero_or_five_day(today) or is_zero_or_five_day(tomorrow)


def is_cancel_deadline_tomorrow(deadline_str: str) -> bool:
    """キャンセル無料期間の最終日が明日か判定"""
    if not deadline_str or deadline_str.strip() == "":
        return False

    try:
        deadline_date = datetime.strptime(deadline_str, "%Y/%m/%d").date()
        return deadline_date == get_jst_tomorrow()
    except (ValueError, AttributeError):
        return False
