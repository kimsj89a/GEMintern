import httpx
import dart_fss as dart
from dartwings.config import DART_API_KEY, DART_BASE_URL

_corp_list = None
_stock_to_corp: dict[str, str] = {}
_corp_to_name: dict[str, str] = {}


def init_corp_list():
    global _corp_list, _stock_to_corp, _corp_to_name
    dart.set_api_key(api_key=DART_API_KEY)
    _corp_list = dart.get_corp_list()
    for corp in _corp_list.corps:
        code = getattr(corp, "stock_code", None)
        if code and code.strip():
            _stock_to_corp[code.strip()] = corp.corp_code
            _corp_to_name[corp.corp_code] = corp.corp_name


def search_corps(query: str, limit: int = 20) -> list[dict]:
    if _corp_list is None:
        init_corp_list()
    results = _corp_list.find_by_corp_name(query, exactly=False)
    if not results:
        return []
    # 모든 결과에서 상장사만 먼저, 그 다음 비상장사
    listed = []
    unlisted = []
    for corp in results:
        stock_code = getattr(corp, "stock_code", None) or ""
        item = {
            "corpName": corp.corp_name,
            "stockCode": stock_code.strip(),
            "corpCode": corp.corp_code,
        }
        if stock_code.strip():
            listed.append(item)
        else:
            unlisted.append(item)
    return (listed + unlisted)[:limit]


def stock_code_to_corp_code(stock_code: str) -> str | None:
    if _corp_list is None:
        init_corp_list()
    return _stock_to_corp.get(stock_code)


def get_company_info(corp_code: str) -> dict:
    url = f"{DART_BASE_URL}/company.json"
    params = {"crtfc_key": DART_API_KEY, "corp_code": corp_code}
    resp = httpx.get(url, params=params, timeout=30)
    data = resp.json()
    if data.get("status") != "000":
        return {}
    return {
        "corpName": data.get("corp_name", ""),
        "corpNameEng": data.get("corp_name_eng", ""),
        "ceoName": data.get("ceo_nm", ""),
        "corpCls": data.get("corp_cls", ""),
        "stockCode": data.get("stock_code", ""),
        "bizrNo": data.get("bizr_no", ""),
        "address": data.get("adres", ""),
        "homepage": data.get("hm_url", ""),
        "estDt": data.get("est_dt", ""),
        "accMonth": data.get("acc_mt", ""),
    }


def get_financial_statements(corp_code: str, bsns_year: str, reprt_code: str = "11011") -> list[dict]:
    url = f"{DART_BASE_URL}/fnlttSinglAcnt.json"
    params = {
        "crtfc_key": DART_API_KEY,
        "corp_code": corp_code,
        "bsns_year": bsns_year,
        "reprt_code": reprt_code,
    }
    resp = httpx.get(url, params=params, timeout=30)
    data = resp.json()
    if data.get("status") != "000":
        return []
    return data.get("list", [])


def get_dividend_info(corp_code: str, bsns_year: str) -> list[dict]:
    url = f"{DART_BASE_URL}/alotMatter.json"
    params = {
        "crtfc_key": DART_API_KEY,
        "corp_code": corp_code,
        "bsns_year": bsns_year,
        "reprt_code": "11011",
    }
    resp = httpx.get(url, params=params, timeout=30)
    data = resp.json()
    if data.get("status") != "000":
        return []
    return data.get("list", [])


def get_disclosures(corp_code: str, bgn_de: str, end_de: str, page_count: int = 100) -> list[dict]:
    url = f"{DART_BASE_URL}/list.json"
    params = {
        "crtfc_key": DART_API_KEY,
        "corp_code": corp_code,
        "bgn_de": bgn_de,
        "end_de": end_de,
        "page_count": str(page_count),
        "sort": "date",
        "sort_mth": "desc",
    }
    resp = httpx.get(url, params=params, timeout=30)
    data = resp.json()
    if data.get("status") != "000":
        return []
    return data.get("list", [])
