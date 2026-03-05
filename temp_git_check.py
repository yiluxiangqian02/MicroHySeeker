import subprocess, os
os.chdir(r'D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\agent_cluster\worktrees\feat_fix-b1-paths')

# Check status
r = subprocess.run(['git', '--no-pager', 'status'], capture_output=True, text=True)
print("=== STATUS ===")
print(r.stdout)
print(r.stderr)

# Check diff
r = subprocess.run(['git', '--no-pager', 'diff', '--name-only'], capture_output=True, text=True)
print("=== DIFF FILES ===")
print(r.stdout)
print(r.stderr)

# Check staged
r = subprocess.run(['git', '--no-pager', 'diff', '--cached', '--name-only'], capture_output=True, text=True)
print("=== STAGED FILES ===")
print(r.stdout)
print(r.stderr)

# Log
r = subprocess.run(['git', '--no-pager', 'log', '--oneline', '-5'], capture_output=True, text=True)
print("=== LOG ===")
print(r.stdout)
print(r.stderr)
