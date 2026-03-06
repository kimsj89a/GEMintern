def parse_amount(raw: str | None) -> int:
    if not raw:
        return 0
    cleaned = raw.replace(",", "").strip()
    if not cleaned or cleaned == "-":
        return 0
    try:
        return int(cleaned)
    except ValueError:
        return 0


def extract_key_financials(fs_list: list[dict], fs_div: str = "CFS") -> dict:
    target_accounts = {
        "매출액": "revenue",
        "영업이익": "operatingProfit",
        "당기순이익": "netIncome",
        "자산총계": "totalAssets",
        "자본총계": "totalEquity",
        "부채총계": "totalDebt",
    }
    result = {}
    # CFS(연결) 우선, 없으면 OFS(개별) 사용
    cfs_items = [i for i in fs_list if i.get("fs_div") == "CFS"]
    ofs_items = [i for i in fs_list if i.get("fs_div") == "OFS"]
    items = cfs_items if cfs_items else ofs_items

    for item in items:
        account_nm = item.get("account_nm", "")
        for ko_name, en_key in target_accounts.items():
            if en_key not in result and ko_name in account_nm:
                result[en_key] = parse_amount(item.get("thstrm_amount"))
                break
    return result


def calc_valuation_multiples(financials: dict, market_cap: int) -> dict:
    revenue = financials.get("revenue", 0)
    op_profit = financials.get("operatingProfit", 0)
    net_income = financials.get("netIncome", 0)
    total_equity = financials.get("totalEquity", 0)
    total_debt = financials.get("totalDebt", 0)

    roe = round(net_income / total_equity * 100, 2) if total_equity else 0
    debt_ratio = round(total_debt / total_equity * 100, 2) if total_equity else 0
    op_margin = round(op_profit / revenue * 100, 2) if revenue else 0
    net_margin = round(net_income / revenue * 100, 2) if revenue else 0

    return {
        "roe": roe,
        "debtRatio": debt_ratio,
        "operatingMargin": op_margin,
        "netMargin": net_margin,
    }


def calc_dcf(financials_by_year: list[dict], market_cap: int, shares: int) -> dict:
    op_profits = [f.get("operatingProfit", 0) for f in financials_by_year if f.get("operatingProfit")]
    if len(op_profits) < 2 or shares == 0:
        return {"fairValue": 0, "currentPrice": 0, "upside": 0, "assumptions": {}}

    growth_rates = []
    for i in range(1, len(op_profits)):
        if op_profits[i - 1] and op_profits[i - 1] > 0:
            gr = (op_profits[i] - op_profits[i - 1]) / op_profits[i - 1]
            growth_rates.append(gr)

    avg_growth = sum(growth_rates) / len(growth_rates) if growth_rates else 0.05
    avg_growth = max(min(avg_growth, 0.30), -0.10)

    discount_rate = 0.10
    terminal_growth = 0.02
    last_fcf = op_profits[-1] * 0.7  # rough FCF proxy

    dcf_sum = 0
    for yr in range(1, 6):
        projected = last_fcf * (1 + avg_growth) ** yr
        dcf_sum += projected / (1 + discount_rate) ** yr

    terminal_value = (last_fcf * (1 + avg_growth) ** 5 * (1 + terminal_growth)) / (discount_rate - terminal_growth)
    terminal_pv = terminal_value / (1 + discount_rate) ** 5

    equity_value = dcf_sum + terminal_pv
    fair_price = int(equity_value / shares) if shares else 0

    return {
        "fairValue": fair_price,
        "assumptions": {
            "growthRate": round(avg_growth * 100, 1),
            "discountRate": 10.0,
            "terminalGrowthRate": 2.0,
        },
    }


def calc_srim(bps: int, roe: float, required_return: float = 8.0) -> dict:
    if bps == 0 or roe == 0:
        return {"fairValue": 0, "assumptions": {}}

    excess_return = (roe - required_return) / 100 * bps
    if required_return == 0:
        return {"fairValue": bps, "assumptions": {}}

    fair_value = int(bps + excess_return / (required_return / 100))

    return {
        "fairValue": fair_value,
        "assumptions": {
            "roe": roe,
            "requiredReturn": required_return,
            "bps": bps,
        },
    }
