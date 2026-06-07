import json
from pathlib import Path

for pid in [
    '2017_yosuke_relationship_between_the_redox_reactions_on_a_bipolar_pl_eb3da9',
    '2025_sha_10000h_stable_intermittent_alkaline_seawater_electrolysi_333f5c',
]:
    lc = Path('LiteratureClean') / pid
    tm = lc / 'table_manifest.json'
    data = json.loads(tm.read_text(encoding='utf-8'))
    print(f'{pid}: {len(data)} entries')
    for k, v in list(data.items())[:3]:
        cap = v.get('caption', '')[:60]
        ip = v.get('image_path', '')
        md = v.get('markdown', '')[:40]
        print(f'  {k}: caption={cap!r}, image={ip!r}, md={md!r}')
    td = lc / 'tables'
    if td.exists():
        files = list(td.iterdir())
        print(f'  tables/ files: {[f.name for f in files]}')
    print()



