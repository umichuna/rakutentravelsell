import os
import sys
from pathlib import Path

RAKUTEN_APP_ID = os.environ.get("RAKUTEN_APP_ID")
RAKUTEN_ACCESS_KEY = os.environ.get("RAKUTEN_ACCESS_KEY")
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS") or None
GAS_GMAIL_WEBHOOK_URL = os.environ.get("GAS_GMAIL_WEBHOOK_URL") or None
GOOGLE_TOKEN_JSON = os.environ.get("GOOGLE_TOKEN_JSON")
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")

LOCAL_TOKEN_PATH = Path.home() / "OneDrive" / "ドキュメント" / "Python" / "import" / "token.json"

RAKUTEN_API_URL = "https://app.rakuten.co.jp/services/api/Travel/VacantHotelSearch/20170426"
REQUEST_HEADERS = {
    "Referer": "https://github.com/",
    "Origin": "https://github.com/"
}
REQUEST_TIMEOUT = 30
MAX_RETRY = 3

BREAKFAST_KEYWORDS = [
    "朝食付き", "朝食バイキング", "朝食込み", "朝食あり",
    "ブレックファスト", "breakfast", "朝食・夕食付き", "2食付き"
]

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

SHEET_NAMES = {
    "config": "設定",
    "hotels": "ホテル一覧",
    "logs": "実行ログ"
}


def validate_config():
    missing = []
    if not RAKUTEN_APP_ID:
        missing.append("RAKUTEN_APP_ID")
    if not RAKUTEN_ACCESS_KEY:
        missing.append("RAKUTEN_ACCESS_KEY")
    if not DISCORD_WEBHOOK_URL:
        missing.append("DISCORD_WEBHOOK_URL")
    if not SPREADSHEET_ID:
        missing.append("SPREADSHEET_ID")
    if not GOOGLE_TOKEN_JSON and not LOCAL_TOKEN_PATH.exists():
        missing.append("GOOGLE_TOKEN_JSON (or local token.json)")

    if missing:
        print(f"❌ 必須環境変数が不足しています: {', '.join(missing)}")
        sys.exit(1)
