"""Diagnostic script: test OpenViking initialization with local sentence-transformers config."""
import os, sys, traceback
from pathlib import Path

# 使用绝对路径，避免 cwd 影响
_SCRIPT_DIR = Path(__file__).resolve().parent
LOG = _SCRIPT_DIR / "_test_ov_init.log"

def p(msg):
    """Print and immediately flush to both stdout and log file."""
    print(msg, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

# 初始化日志文件
LOG.write_text("=== DIAGNOSTIC START ===\n", encoding="utf-8")

_BASE = _SCRIPT_DIR.parent
OV_CONF = _BASE / "OpenViking" / ".local_dev" / "ov.conf"
OV_DATA = _BASE / "data" / "openviking"

p(f"Script: {__file__}")
p(f"Config: {OV_CONF} (exists={OV_CONF.exists()})")
p(f"Data:   {OV_DATA}")

os.environ["OPENVIKING_CONFIG_FILE"] = str(OV_CONF)
OV_DATA.mkdir(parents=True, exist_ok=True)
p(f"Data dir created: {OV_DATA.exists()}")

p("--- Step 1: import SyncOpenViking ---")
try:
    from openviking.sync_client import SyncOpenViking
    p("SyncOpenViking import OK")
except BaseException:
    p(traceback.format_exc())
    sys.exit(1)

p("--- Step 2: SyncOpenViking(path=...) ---")
try:
    client = SyncOpenViking(path=str(OV_DATA))
    p("client created OK")
except BaseException:
    p(traceback.format_exc())
    sys.exit(1)

p("--- Step 3: client.initialize() ---")
try:
    client.initialize()
    p("client.initialize() OK")
except BaseException:
    p(traceback.format_exc())
    sys.exit(1)

p("=== ALL STEPS PASSED ===")
sys.exit(0)

p("\nAll checks passed - ready to import")
LOG.write_text(buf.getvalue(), encoding="utf-8")
