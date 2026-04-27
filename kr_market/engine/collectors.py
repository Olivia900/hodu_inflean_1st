import ast
import re
import sys
from datetime import date, timedelta
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import requests
from bs4 import BeautifulSoup

from kr_market.engine.config import SignalConfig

NAVER_RISE_URL = "https://finance.naver.com/sise/sise_rise.naver"
NAVER_FIELD_SUBMIT_URL = "https://finance.naver.com/sise/field_submit.naver"
NAVER_SISE_JSON_URL = "https://api.finance.naver.com/siseJson.naver"
NAVER_ITEM_REFERER = "https://finance.naver.com/item/sise.naver?code={code}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}

MARKET_SOSOK = {"KOSPI": 0, "KOSDAQ": 1}


def get_top_gainers(
    market: str, config: SignalConfig | None = None
) -> list[dict]:
    rows = _fetch_raw_gainers(market)
    if config is None:
        return rows
    return apply_signal_filter(rows, config)


def apply_signal_filter(
    rows: list[dict], config: SignalConfig
) -> list[dict]:
    filtered: list[dict] = []
    for row in rows:
        name = row["name"]

        if any(kw in name for kw in config.exclude_keywords):
            continue

        if config.exclude_preferred and name.endswith("우"):
            continue

        price = row["price"]
        if price < config.min_price or price > config.max_price:
            continue

        change = row["change_rate"]
        if change < config.min_change_pct or change > config.max_change_pct:
            continue

        if row["trade_value"] < config.min_trading_value:
            continue

        filtered.append(row)

    return filtered


def get_chart_data(code: str, days: int = 60) -> list[dict]:
    if not re.fullmatch(r"\d{6}", code):
        raise ValueError(f"code must be 6 digits, got {code!r}")

    end = date.today()
    # 거래일 기준 days를 확보하려면 캘린더일 기준 ~2배 + 여유 30일 필요
    start = end - timedelta(days=days * 2 + 30)

    headers = {**HEADERS, "Referer": NAVER_ITEM_REFERER.format(code=code)}
    response = requests.get(
        NAVER_SISE_JSON_URL,
        params={
            "symbol": code,
            "requestType": 1,
            "startTime": start.strftime("%Y%m%d"),
            "endTime": end.strftime("%Y%m%d"),
            "timeframe": "day",
        },
        headers=headers,
        timeout=10,
    )
    response.raise_for_status()

    text = response.text.strip()
    if not text:
        return []
    parsed = ast.literal_eval(text)
    if len(parsed) < 2:
        return []

    rows: list[dict] = []
    for entry in parsed[1:]:
        if len(entry) < 5:
            continue
        date_str = str(entry[0])
        if len(date_str) != 8 or not date_str.isdigit():
            continue
        open_ = int(entry[1])
        high = int(entry[2])
        low = int(entry[3])
        close = int(entry[4])
        # 거래정지일은 OHL이 0으로 기록되므로 차트 계산에서 제외
        if min(open_, high, low, close) <= 0:
            continue
        rows.append(
            {
                "date": f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}",
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "volume": int(entry[5]) if len(entry) > 5 else 0,
            }
        )

    rows.sort(key=lambda r: r["date"])
    rows = rows[-days:]
    _attach_moving_averages(rows, [5, 10, 20])
    return rows


def is_uptrend(row: dict) -> bool:
    ma5, ma10, ma20 = row.get("ma5"), row.get("ma10"), row.get("ma20")
    if ma5 is None or ma10 is None or ma20 is None:
        return False
    return ma5 > ma10 > ma20


def analyze_chart(code: str, days: int = 250) -> dict | None:
    chart = get_chart_data(code, days=days)
    if not chart:
        return None

    last = chart[-1]
    high_52w = max(r["high"] for r in chart)
    low_52w = min(r["low"] for r in chart)
    current = last["close"]

    return {
        "current_price": current,
        "ma5": last["ma5"],
        "ma10": last["ma10"],
        "ma20": last["ma20"],
        "is_uptrend": is_uptrend(last),
        "high_52w": high_52w,
        "low_52w": low_52w,
        "pct_from_high": current / high_52w * 100 if high_52w else 0.0,
        "data_points": len(chart),
    }


def analyze_stocks(
    stocks: list[dict], days: int = 250, max_workers: int = 6
) -> list[dict]:
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(analyze_chart, s["code"], days): s for s in stocks
        }
        total = len(stocks)
        completed = 0
        for fut in as_completed(futures):
            stock = futures[fut]
            completed += 1
            try:
                analysis = fut.result()
            except Exception as exc:
                print(
                    f"  [에러] {stock['name']} ({stock['code']}): {exc}",
                    flush=True,
                )
                continue
            if analysis is None:
                continue
            results.append({**stock, **analysis})
            print(
                f"  분석 진행: {completed}/{total}", end="\r", flush=True
            )
    print()
    return results


def _attach_moving_averages(rows: list[dict], windows: list[int]) -> None:
    closes = [r["close"] for r in rows]
    for n in windows:
        key = f"ma{n}"
        for i in range(len(rows)):
            if i + 1 < n:
                rows[i][key] = None
            else:
                rows[i][key] = sum(closes[i + 1 - n : i + 1]) / n


def _fetch_raw_gainers(market: str) -> list[dict]:
    market = market.upper()
    if market not in MARKET_SOSOK:
        raise ValueError(f"market must be 'KOSPI' or 'KOSDAQ', got {market!r}")

    sosok = MARKET_SOSOK[market]
    return_url = f"http://finance.naver.com/sise/sise_rise.naver?sosok={sosok}"

    session = requests.Session()
    session.headers.update(HEADERS)

    session.post(
        NAVER_FIELD_SUBMIT_URL,
        data=[
            ("menu", "up"),
            ("returnUrl", return_url),
            ("fieldIds", "quant"),
            ("fieldIds", "amount"),
            ("fieldIds", "ask_buy"),
            ("fieldIds", "ask_sell"),
        ],
        timeout=10,
    )

    response = session.get(NAVER_RISE_URL, params={"sosok": sosok}, timeout=10)
    response.raise_for_status()
    response.encoding = "euc-kr"

    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.select_one("table.type_2")
    if table is None:
        return []

    results: list[dict] = []
    for row in table.select("tr"):
        cells = row.find_all("td")
        if len(cells) < 9:
            continue

        name_link = cells[1].find("a")
        if name_link is None:
            continue

        href = name_link.get("href", "")
        code_match = re.search(r"code=(\d{6})", href)
        if code_match is None:
            continue

        results.append(
            {
                "name": name_link.get_text(strip=True),
                "code": code_match.group(1),
                "price": _to_int(cells[2].get_text(strip=True)),
                "change_rate": _to_float(
                    cells[4].get_text(strip=True).replace("%", "")
                ),
                "volume": _to_int(cells[5].get_text(strip=True)),
                # 거래대금은 백만원 단위로 표시되므로 원 단위로 환산
                "trade_value": _to_int(cells[6].get_text(strip=True)) * 1_000_000,
            }
        )

    return results


def _to_int(text: str) -> int:
    cleaned = text.replace(",", "").replace("+", "").strip()
    if not cleaned or cleaned == "-":
        return 0
    try:
        return int(cleaned)
    except ValueError:
        return 0


def _to_float(text: str) -> float:
    cleaned = text.replace(",", "").replace("+", "").strip()
    if not cleaned or cleaned == "-":
        return 0.0
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


if __name__ == "__main__":
    config = SignalConfig()

    raw_kospi = get_top_gainers("KOSPI")
    raw_kosdaq = get_top_gainers("KOSDAQ")
    for item in raw_kospi:
        item["market"] = "KOSPI"
    for item in raw_kosdaq:
        item["market"] = "KOSDAQ"
    raw_all = raw_kospi + raw_kosdaq

    filtered = apply_signal_filter(raw_all, config)
    filtered.sort(key=lambda x: x["change_rate"], reverse=True)

    print(
        f"필터 전: 코스피 {len(raw_kospi)} + 코스닥 {len(raw_kosdaq)} "
        f"= {len(raw_all)}개"
    )
    print(f"필터 후: {len(filtered)}개  (제외 {len(raw_all) - len(filtered)}개)")
    print("-" * 100)
    print("필터 조건:")
    print(
        f"  · 거래대금 ≥ {config.min_trading_value:,}원 / "
        f"등락률 {config.min_change_pct}~{config.max_change_pct}% / "
        f"가격 {config.min_price:,}~{config.max_price:,}원"
    )
    print(
        f"  · 제외 키워드 {len(config.exclude_keywords)}개, "
        f"우선주 제외={config.exclude_preferred}"
    )
    print("-" * 100)
    for i, item in enumerate(filtered[:15], 1):
        print(
            f"{i:>2}. [{item['market']:<6}] {item['name']} ({item['code']}) | "
            f"현재가: {item['price']:>10,}원 | "
            f"등락률: {item['change_rate']:+6.2f}% | "
            f"거래량: {item['volume']:>14,}주 | "
            f"거래대금: {item['trade_value']:>17,}원"
        )

    if not filtered:
        sys.exit(0)

    print()
    print(
        f"[차트 분석] 필터 통과 {len(filtered)}종목에 대해 "
        "정배열·52주 고저 분석 시작 (250거래일)"
    )
    analyzed = analyze_stocks(filtered, days=250, max_workers=6)
    analyzed.sort(key=lambda x: x["change_rate"], reverse=True)

    uptrend_cnt = sum(1 for a in analyzed if a["is_uptrend"])
    print(
        f"  분석 완료: {len(analyzed)}종목 / 정배열(MA5>MA10>MA20) "
        f"{uptrend_cnt}종목"
    )
    print("-" * 130)
    print(
        f"{'시장':<6} {'종목명':<14} {'코드':<6} "
        f"{'현재가':>9} {'등락률':>7} {'정배열':>4} "
        f"{'52W최고':>10} {'52W최저':>10} {'고가대비':>8} {'데이터':>5}"
    )
    print("-" * 130)
    for a in analyzed:
        name_disp = a["name"][:14]
        uptrend = "○" if a["is_uptrend"] else "·"
        print(
            f"{a['market']:<6} {name_disp:<14} {a['code']:<6} "
            f"{a['current_price']:>9,} "
            f"{a['change_rate']:>+6.2f}% "
            f"{uptrend:>4} "
            f"{a['high_52w']:>10,} {a['low_52w']:>10,} "
            f"{a['pct_from_high']:>7.1f}% "
            f"{a['data_points']:>5}일"
        )
