import os, sys
sys.path.insert(0, "OpenViking")
os.environ["OPENVIKING_CONFIG_FILE"] = "OpenViking/.local_dev/ov.conf"
from openviking.sync_client import SyncOpenViking
client = SyncOpenViking(path="data/openviking")
client.initialize()

# Verify literature dir
result = client.ls("viking://resources/literature/", simple=True)
print("Papers in literature/:", len(result), "items")
for item in result[:3]:
    print(" ", item)

# Try find with correct target_uri
print("\n--- find: 'reverse current' in literature/ ---")
r = client.find("reverse current", target_uri="viking://resources/literature", limit=3)
print("total:", r.total)
print("resources:", len(r.resources))
for res in r.resources[:5]:
    print("  resource:", type(res), repr(res)[:200])

# Also try search (with intent analysis)
print("\n--- search: 'reverse current' ---")
r2 = client.search("reverse current", target_uri="viking://resources/literature", limit=3)
print("total:", r2.total)
print("resources:", len(r2.resources))
for res in r2.resources[:5]:
    print("  resource:", type(res), repr(res)[:200])
