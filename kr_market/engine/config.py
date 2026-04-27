from dataclasses import dataclass, field


@dataclass
class SignalConfig:
    # 필터링 조건
    min_trading_value: int = 5_000_000_000
    min_change_pct: float = 5.0
    max_change_pct: float = 30.0
    min_price: int = 1_000
    max_price: int = 500_000

    # 제외 조건
    exclude_etf: bool = True
    exclude_spac: bool = True
    exclude_preferred: bool = True

    # 종목명 제외 키워드
    exclude_keywords: list[str] = field(
        default_factory=lambda: [
            "스팩",
            "SPAC",
            "ETF",
            "ETN",
            "리츠",
            "우B",
            "우C",
            "1우",
            "2우",
            "3우",
            "인버스",
            "레버리지",
        ]
    )
