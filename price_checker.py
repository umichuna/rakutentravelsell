def check_price_drop(hotel: dict, plans: list[dict] | None) -> dict | None:
    """
    価格が下落しているか判定する
    hotel: sheets.get_hotels() が返すdict
    plans: rakuten_api.fetch_vacant_plans() が返すlist
    戻り値: 下落があれば詳細dict、なければNone
    """
    if plans is None or len(plans) == 0:
        return None

    # 最安プランを取得
    best_plan = plans[0]
    best_price = best_plan["price"]
    reserved_price = hotel["reserved_price"]

    # 値下がり判定: 予約済み=TRUE かつ 現在価格 < 予約価格
    if not hotel.get("reserved"):
        return None

    if best_price >= reserved_price:
        return None

    # 下落あり
    drop_amount = reserved_price - best_price
    drop_percent = (drop_amount / reserved_price) * 100

    return {
        "hotel_name": hotel["hotel_name"],
        "hotel_no": hotel["hotel_no"],
        "hotel_url": hotel["hotel_url"],
        "checkin": hotel.get("checkin", ""),
        "checkout": hotel.get("checkout", ""),
        "reserved_price": reserved_price,
        "best_price": best_price,
        "best_plan_name": best_plan["plan_name"],
        "drop_amount": int(drop_amount),
        "drop_percent": round(drop_percent, 1)
    }


def get_min_price(plans: list[dict] | None) -> int | None:
    """プランリストから最安価格を返す"""
    if plans is None or len(plans) == 0:
        return None
    return plans[0]["price"]
