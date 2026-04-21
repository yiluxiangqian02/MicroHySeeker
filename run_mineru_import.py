"""Run the full MinerU -> OpenViking import pipeline.

Usage (standalone):
    python run_mineru_import.py [mineru_output_dir] [--workspace DIR] [--target URI] [--batch-name NAME]

If mineru_output_dir is omitted, defaults to <script_dir>/AutoHySeeker/MinerU/output.
"""
import os, sys
from pathlib import Path

# ── Resolve workspace root relative to this script ───────────────────────────
_SCRIPT_DIR = Path(__file__).resolve().parent
_AUTOHYSEEKER = _SCRIPT_DIR / "AutoHySeeker"
_DEFAULT_OPENVIKING = _AUTOHYSEEKER / "OpenViking"

# ── Native DLL setup (must happen before any openviking import) ───────────────
_ov_bin = _DEFAULT_OPENVIKING / "openviking" / "bin"
if _ov_bin.exists():
    os.add_dll_directory(str(_ov_bin))

_ov_conf = _DEFAULT_OPENVIKING / ".local_dev" / "ov.conf"
if _ov_conf.exists() and not os.environ.get("OPENVIKING_CONFIG_FILE"):
    os.environ["OPENVIKING_CONFIG_FILE"] = str(_ov_conf)

_pyagfs = _DEFAULT_OPENVIKING / "third_party" / "agfs" / "agfs-sdk" / "python"
for _extra in (_pyagfs, _DEFAULT_OPENVIKING):
    _s = str(_extra)
    if _extra.exists() and _s not in sys.path:
        sys.path.insert(0, _s)

from openviking.pipeline.mineru_import import build_argument_parser, run_pipeline
import json

parser = build_argument_parser()

# ── Build argv: if first positional arg is missing, inject default ────────────
_argv = sys.argv[1:]
# Check if a positional (non-flag) argument was provided
_has_positional = any(not a.startswith("--") for a in _argv)
if not _has_positional:
    _default_mineru = str(_AUTOHYSEEKER / "MinerU" / "output")
    _argv = [_default_mineru] + _argv

# Inject --workspace default if not provided
if "--workspace" not in _argv:
    _argv += ["--workspace", str(_DEFAULT_OPENVIKING)]

args = parser.parse_args(_argv)
print("Starting MinerU -> OpenViking pipeline...")
print(f"  mineru_dir : {args.mineru_output_dir if hasattr(args, 'mineru_output_dir') else _argv[0]}")
print(f"  workspace  : {args.workspace if hasattr(args, 'workspace') else _DEFAULT_OPENVIKING}")

try:
    result = run_pipeline(args)
    print("=== PIPELINE RESULT ===")
    print(json.dumps({
        "status": result.get("status"),
        "batch_name": result.get("batch_name"),
        "prepared_count": result.get("prepared_count"),
        "openviking_status": result.get("openviking_result", {}).get("status"),
        "root_uri": result.get("openviking_result", {}).get("root_uri"),
        "errors": result.get("openviking_result", {}).get("errors", []),
    }, indent=2, default=str))
except Exception as e:
    import traceback
    traceback.print_exc()
    print("PIPELINE ERROR:", type(e).__name__, str(e)[:1000])
    sys.exit(1)
