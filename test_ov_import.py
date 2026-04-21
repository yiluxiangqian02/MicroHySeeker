import os, sys, traceback, shutil
from pathlib import Path

os.add_dll_directory(r'D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\OpenViking\openviking\bin')
sys.path.insert(0, r'D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\OpenViking\third_party\agfs\agfs-sdk\python')
sys.path.insert(0, r'D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\OpenViking')
os.environ['OPENVIKING_CONFIG_FILE'] = r'D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\OpenViking\.local_dev\ov.conf'

from openviking.pipeline.mineru_import import import_staged_directory

# Use a simple staged dir with just one test file
stage_dir = Path(r'D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\OpenViking\.tmp_test_import')
stage_dir.mkdir(parents=True, exist_ok=True)
test_doc = stage_dir / 'test_doc'
test_doc.mkdir(exist_ok=True)
(test_doc / 'test.md').write_text('# Test\nThis is a test document for OpenViking import.', encoding='utf-8')

try:
    result = import_staged_directory(
        stage_dir=stage_dir,
        workspace=Path(r'D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\OpenViking'),
        target='viking://resources/literature/mineru_pipeline/',
        timeout=60.0,
        reason='test'
    )
    print('SUCCESS:', result)
except Exception as e:
    traceback.print_exc()
    print('ERROR:', type(e).__name__, str(e)[:500])
finally:
    shutil.rmtree(stage_dir, ignore_errors=True)
