"""Check what metadata is stored in vectordb for matched URIs."""
import os, sys, json
sys.path.insert(0, "OpenViking")
os.environ["OPENVIKING_CONFIG_FILE"] = "OpenViking/.local_dev/ov.conf"
from openviking.sync_client import SyncOpenViking
import asyncio
from pathlib import Path

client = SyncOpenViking(path="data/openviking")
client.initialize()

# Do a search and then inspect result fields
results = client.find("reverse current", target_uri="viking://resources/literature", limit=3)

print("=== Matched resource fields ===")
for item in results.resources[:2]:
    print("uri:", item.uri)
    print("context_type:", item.context_type)
    print("level:", item.level)
    print("abstract:", repr(item.abstract)[:200])
    print("score:", item.score)
    print("relations:", item.relations[:2] if item.relations else [])
    print("ALL fields:", [f for f in dir(item) if not f.startswith("_")])
    print()

# Also check the raw vectordb record for one uri
svc = client._async_client._client._service
storage = svc.search._retriever.storage

loop = asyncio.new_event_loop()
try:
    from openviking_cli.utils.config import get_openviking_config
    coll = get_openviking_config().storage.vectordb.name
    # filter by URI
    uri = results.resources[0].uri
    records = loop.run_until_complete(storage.filter(
        collection=coll,
        filter={"op": "and", "conds": [{"op": "must", "field": "uri", "conds": [uri]}]},
        limit=1
    ))
    if records:
        print("=== Raw vectordb record ===")
        print(json.dumps({k: v for k, v in records[0].items() if k != "vector" and k != "sparse_vector"}, indent=2, ensure_ascii=False, default=str)[:800])
finally:
    loop.close()

# Also check evidence_links.json
CLEAN_ROOT = Path("LiteratureClean")
ev_file = CLEAN_ROOT / "2026_he_heterointerface_enabled_anti_reverse_current_electrodes_43767e" / "evidence_links.json"
if ev_file.exists():
    ev = json.loads(ev_file.read_text())
    print("\n=== evidence_links.json (first item) ===")
    items = ev if isinstance(ev, list) else ev.get("links", ev.get("evidence_links", []))
    for item in items[:2]:
        print(json.dumps(item, indent=2, ensure_ascii=False, default=str)[:600])
        print()
