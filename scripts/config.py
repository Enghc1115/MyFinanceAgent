from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
REPORTS_DIR = PROJECT_ROOT / "reports"

# (前缀, Sina代码, 显示名) — 用于 get_market_data.py
INDICES_CONFIG = [
    ("sh",   "sh000001", "上证指数"),
    ("sz",   "sz399001", "深证成指"),
    ("cyb",  "sz399006", "创业板指"),
    ("kc50", "sh000688", "科创50"),
    ("bj50", "bj899050", "北证50"),
]

DEEP_REPORTS_DIR = REPORTS_DIR / "deep"
SLIDES_DIR = REPORTS_DIR / "slides"
DEEP_DATA_DIR = DATA_DIR / "deep"
SECTOR_FLOW_DIR = DATA_DIR / "sector_flow"
ARCHIVE_DIR = DATA_DIR / "archive"
LOGS_DIR = PROJECT_ROOT / "logs"
