from datetime import datetime
import pytz


def get_jst_now():
    """JST の現在時刻を datetime.datetime で返す"""
    return datetime.now(pytz.timezone("Asia/Tokyo"))


def format_jst_timestamp(dt=None) -> str:
    """YYYY-MM-DD HH:MM:SS JST の形式でタイムスタンプを返す"""
    if dt is None:
        dt = get_jst_now()
    return dt.strftime("%Y-%m-%d %H:%M:%S JST")


def log_info(message: str):
    """情報ログを標準出力"""
    timestamp = format_jst_timestamp()
    print(f"[INFO] {timestamp} - {message}")


def log_error(message: str):
    """エラーログを標準出力"""
    timestamp = format_jst_timestamp()
    print(f"[ERROR] {timestamp} - {message}")


def log_debug(message: str):
    """デバッグログを標準出力"""
    timestamp = format_jst_timestamp()
    print(f"[DEBUG] {timestamp} - {message}")
