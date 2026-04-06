import urllib.request, json

BASE = 'http://127.0.0.1:5173'
ROUTES = ['/', '/dashboard', '/experiments', '/optimization', '/chat',
          '/diagnostics', '/agents', '/knowledge', '/templates', '/settings']

print('=== Route loading test ===')
all_ok = True
for route in ROUTES:
    try:
        r = urllib.request.urlopen(BASE + route, timeout=5)
        html = r.read().decode('utf-8', errors='replace')
        if '<div id="root">' in html and '<script' in html:
            print(f'  {route:20s} OK')
        else:
            print(f'  {route:20s} WARN')
            all_ok = False
    except Exception as e:
        print(f'  {route:20s} FAIL ({e})')
        all_ok = False

print('\n=== API proxy test ===')
try:
    r = urllib.request.urlopen(BASE + '/api/system/config', timeout=5)
    data = json.loads(r.read())
    dc = len(data.get('dilution_channels', []))
    fc = len(data.get('flush_channels', []))
    p = len(data.get('pumps', []))
    print(f'  config: {dc} dilution, {fc} flush, {p} pumps')
except Exception as e:
    print(f'  config FAIL: {e}')
    all_ok = False

try:
    r = urllib.request.urlopen(BASE + '/health', timeout=5)
    print(f'  health: {r.status}')
except Exception as e:
    print(f'  health FAIL: {e}')

print('\n' + ('ALL PASSED' if all_ok else 'SOME FAILURES'))
