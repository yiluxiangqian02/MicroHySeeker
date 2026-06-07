import os, sys
sys.path.insert(0, "OpenViking")
os.environ["OPENVIKING_CONFIG_FILE"] = "OpenViking/.local_dev/ov.conf"
from openviking.sync_client import SyncOpenViking
import asyncio

client = SyncOpenViking(path="data/openviking")
client.initialize()

svc = client._async_client._client._service
storage = svc.search._retriever.storage
print("storage type:", type(storage))
print("storage dir:", [x for x in dir(storage) if not x.startswith("__")])

loop = asyncio.new_event_loop()
try:
    for cname in ["context", "literature", "default", "microhyseeker"]:
        try:
            exists = loop.run_until_complete(storage.collection_exists(cname))
            print(f"  collection '{cname}' exists: {exists}")
        except Exception as e:
            print(f"  collection '{cname}': error: {e}")
finally:
    loop.close()
