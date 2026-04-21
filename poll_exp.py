import json, requests, time

exp_id = 'exp_20260415_150850_450513'
for i in range(60):
    time.sleep(5)
    r = requests.get(f'http://127.0.0.1:8200/api/experiments/detail/{exp_id}/progress')
    data = r.json()
    status = data.get('status')
    step_status = data.get('step_status', '')
    logs = data.get('logs', [])
    last_log = logs[-1]['message'] if logs else 'no log'
    print(f'[{i*5}s] status={status} step_status={step_status} last_log={last_log[:80]}')
    if status in ('completed', 'failed', 'stopped'):
        print('FINAL LOGS:')
        for log in logs:
            print(f"  [{log['level']}] {log['message']}")
        break
