import json
import re
from datetime import datetime
import gspread
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google.oauth2.credentials import Credentials as OAuth2Credentials
import pytz

from config import (
    GOOGLE_TOKEN_JSON, LOCAL_TOKEN_PATH, SCOPES,
    SPREADSHEET_ID, SHEET_NAMES
)


def get_gspread_client():
    """Google Sheets 認証してクライアント返却"""
    token_json = GOOGLE_TOKEN_JSON
    if token_json:
        try:
            token_data = json.loads(token_json)
        except json.JSONDecodeError:
            raise ValueError("GOOGLE_TOKEN_JSON is not valid JSON")
    else:
        with open(LOCAL_TOKEN_PATH, "r") as f:
            token_data = json.load(f)

    if token_data.get("type") == "service_account":
        creds = ServiceAccountCredentials.from_service_account_info(token_data, scopes=SCOPES)
    else:
        creds = OAuth2Credentials.from_authorized_user_info(token_data)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())

    return gspread.authorize(creds)


def get_spreadsheet(client: gspread.Client):
    """スプレッドシート取得"""
    return client.open_by_key(SPREADSHEET_ID)


def get_config(client: gspread.Client) -> dict:
    """設定シートから全設定を取得"""
    ss = get_spreadsheet(client)
    sheet = ss.worksheet(SHEET_NAMES["config"])
    rows = sheet.get_all_values()

    config = {}
    for row in rows[1:]:  # ヘッダー行をスキップ
        if len(row) >= 2:
            key = row[0].strip()
            value = row[1].strip() if row[1] else None
            config[key] = value

    return config


def get_hotels(client: gspread.Client) -> list[dict]:
    """ホテル一覧を取得（監視有効=TRUEの行のみ）"""
    ss = get_spreadsheet(client)
    sheet = ss.worksheet(SHEET_NAMES["hotels"])
    rows = sheet.get_all_values()

    hotels = []
    for idx, row in enumerate(rows[1:], start=2):  # ヘッダー行(1)をスキップ
        if len(row) < 6:  # 最小限のカラム確認
            continue

        hotel_name = row[0].strip()
        hotel_url = row[1].strip()

        # C列: 施設番号（hotelNo）
        hotel_no = row[2].strip() if len(row) > 2 else ""
        if not hotel_no:
            hotel_no = extract_hotel_no_from_url(hotel_url)
            if hotel_no:
                sheet.update_cell(idx, 3, hotel_no)

        # D列: 予約価格
        reserved_price_str = row[3].strip() if len(row) > 3 else "0"
        try:
            reserved_price = int(reserved_price_str)
        except ValueError:
            reserved_price = 0

        # E列: キャンセル無料期間最終日
        cancel_deadline = row[4].strip() if len(row) > 4 else ""

        # F列: 予約済み
        reserved_str = row[5].strip().upper() if len(row) > 5 else "FALSE"
        reserved = reserved_str == "TRUE"

        # G列: 監視有効
        monitoring_str = row[6].strip().upper() if len(row) > 6 else ""
        if not monitoring_str:
            monitoring = True
            sheet.update_cell(idx, 7, "TRUE")
        else:
            monitoring = monitoring_str == "TRUE"

        if not monitoring:
            continue  # 監視有効=FALSEはスキップ

        if not hotel_no or not hotel_name:
            continue

        hotels.append({
            "row_index": idx,
            "hotel_name": hotel_name,
            "hotel_url": hotel_url,
            "hotel_no": hotel_no,
            "reserved_price": reserved_price,
            "cancel_deadline": cancel_deadline,
            "reserved": reserved,
            "monitoring": monitoring
        })

    return hotels


def extract_hotel_no_from_url(url: str) -> str:
    """URLからhotelNoを抽出"""
    match = re.search(r'/HOTEL/(\d+)/', url)
    if match:
        return match.group(1)
    return ""


def update_hotel_prices(client: gspread.Client, row_idx: int, current_price: int | None, min_price: int | None, updated_at: str):
    """ホテル一覧シートの価格情報を更新（G・H・I列）"""
    ss = get_spreadsheet(client)
    sheet = ss.worksheet(SHEET_NAMES["hotels"])

    current_price_str = str(current_price) if current_price is not None else "-"
    min_price_str = str(min_price) if min_price is not None else ""

    sheet.update_cell(row_idx, 8, current_price_str)  # H列: 現在価格
    sheet.update_cell(row_idx, 9, min_price_str)      # I列: 最安価格
    sheet.update_cell(row_idx, 10, updated_at)        # J列: 最終取得日時


def append_log(client: gspread.Client, log_entry: dict):
    """実行ログにエントリを追記"""
    ss = get_spreadsheet(client)
    sheet = ss.worksheet(SHEET_NAMES["logs"])

    row = [
        log_entry.get("timestamp", ""),
        log_entry.get("hotel_count", ""),
        log_entry.get("success_count", ""),
        log_entry.get("error_count", ""),
        log_entry.get("notification_count", ""),
        log_entry.get("error_detail", ""),
        log_entry.get("status", "")
    ]

    sheet.append_row(row)
