import ast
path = r'D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\agent_cluster\worktrees\feat_fix-b3-b7\AutoHySeeker\tests\test_optimization.py'
with open(path, 'r', encoding='utf-8') as f:
    source = f.read()
tree = ast.parse(source)
classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
funcs = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
print(f"Syntax OK")
print(f"Classes: {len(classes)}")
print(f"Test methods: {len([f for f in funcs if f.startswith('test_')])}")
for c in classes:
    print(f"  - {c}")
