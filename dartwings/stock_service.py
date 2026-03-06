from datetime import datetime, timedelta
from pykrx import stock
import time

_price_cache: dict[str, tuple[float, dict]] = {}
CACHE_TTL = 300  # 5 minutes


def _get_recent_trading_date() -> str:
    today = datetime.today()
    for delta in range(7):
        date = (today - timedelta(days=delta)).strftime("%Y%m%d")
        tickers = stock.get_market_ticker_list(date, market="ALL")
        if tickers:
            return date
    return today.strftime("%Y%m%d")


def get_current_price(stock_code: str) -> dict:
    cache_key = f"price_{stock_code}"
    now = time.time()
    if cache_key in _price_cache:
        ts, data = _price_cache[cache_key]
        if now - ts < CACHE_TTL:
            return data

    date = _get_recent_trading_date()
    prev_date = (datetime.strptime(date, "%Y%m%d") - timedelta(days=7)).strftime("%Y%m%d")

    df = stock.get_market_ohlcv_by_date(prev_date, date, stock_code)
    if df.empty:
        return {"current": 0, "change": 0, "volume": 0}

    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    change = ((last["종가"] - prev["종가"]) / prev["종가"] * 100) if prev["종가"] else 0

    result = {
        "current": int(last["종가"]),
        "change": round(change, 2),
        "volume": int(last["거래량"]),
        "high": int(last["고가"]),
        "low": int(last["저가"]),
        "open": int(last["시가"]),
    }
    _price_cache[cache_key] = (now, result)
    return result


def get_price_history(stock_code: str, days: int = 365) -> dict:
    end = _get_recent_trading_date()
    start = (datetime.strptime(end, "%Y%m%d") - timedelta(days=days)).strftime("%Y%m%d")
    df = stock.get_market_ohlcv_by_date(start, end, stock_code)
    if df.empty:
        return {"dates": [], "closes": []}
    return {
        "dates": [d.strftime("%Y-%m-%d") for d in df.index],
        "closes": [int(v) for v in df["종가"].tolist()],
    }


def get_market_cap(stock_code: str) -> int:
    date = _get_recent_trading_date()
    prev = (datetime.strptime(date, "%Y%m%d") - timedelta(days=7)).strftime("%Y%m%d")
    df = stock.get_market_cap_by_date(prev, date, stock_code)
    if df.empty:
        return 0
    return int(df.iloc[-1]["시가총액"])


def get_fundamentals(stock_code: str) -> dict:
    end = _get_recent_trading_date()
    start = (datetime.strptime(end, "%Y%m%d") - timedelta(days=14)).strftime("%Y%m%d")
    df = stock.get_market_fundamental_by_date(start, end, stock_code)
    if df.empty:
        return {"per": 0, "pbr": 0, "eps": 0, "bps": 0, "div": 0}
    # 가장 최근 유효(PER > 0) 데이터 사용
    nonzero = df[df["PER"] > 0]
    row = nonzero.iloc[-1] if not nonzero.empty else df.iloc[-1]
    return {
        "per": round(float(row.get("PER", 0)), 2),
        "pbr": round(float(row.get("PBR", 0)), 2),
        "eps": int(row.get("EPS", 0)),
        "bps": int(row.get("BPS", 0)),
        "div": round(float(row.get("DIV", 0)), 2),
    }
