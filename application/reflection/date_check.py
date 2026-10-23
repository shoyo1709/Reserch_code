from datetime import date, datetime


# 「YYYY-MM-DD」の形式の日付かどうかを判定する
def is_valid_date_format(date_str):
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except (TypeError, ValueError):
        return False
    return True


# 「YYYY-MM-DD」の形式で、かつ今日以前の日付かどうかを判定する
def is_valid_past_date(date_str):
    if not is_valid_date_format(date_str):
        return False
    return datetime.strptime(date_str, "%Y-%m-%d").date() <= date.today()
