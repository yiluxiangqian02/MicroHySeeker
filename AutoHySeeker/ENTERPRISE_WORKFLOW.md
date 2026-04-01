# 企业级分支协作标准流程

## 当前架构

```
autohyseeker (主分支 - 永远稳定)
│
├── feat/A (你的分支) → PR → autohyseeker
└── feat/B (同事的分支) → PR → autohyseeker
```

**原则：autohyseeker 是受保护的稳定分支，所有改动都通过分支隔离 + PR 流程**

---

## 完整工作流

### 第1步：初始化（已完成✅）

```bash
git fetch origin
# feat/A 和 feat/B 都已从 autohyseeker 拉取
# base commit: bfaefcb1 (融合版本1)
```

### 第2步：日常开发（你和同事分别操作）

**你的工作流（A部分）：**
```bash
git checkout feat/A

# 循环：改代码 → 提交 → 推送
while 还没完成:
    # 编辑文件（只改 A 相关部分）
    code src/agents/data_analyst.py  # 举例
    
    # 小功能单元提交
    git add src/agents/data_analyst.py
    git commit -m "feat: A部分 - 数据分析器初始框架"
    
    # 实时推送到远端（便于交流和备份）
    git push origin feat/A
    
    # 继续下个功能...
```

**同事的工作流（B部分）：**
```bash
git checkout feat/B
# 同理，编辑 B 相关部分，频繁 commit + push
```

---

### 第3步：完成开发后提 PR（Pull Request）

**你完成 A 部分后：**

#### 方法 A：使用命令行（适合 GitHub CLI）
```bash
# 安装 GitHub CLI（如果还没有）
# https://cli.github.com/

git push origin feat/A
gh pr create --base autohyseeker --head feat/A \
  --title "feat: A部分完成" \
  --body "### 改动说明
- 添加 xxx 功能
- 修复 xxx bug
- 共 N 个 commit"
```

#### 方法 B：使用 GitHub 网页（最直观）
1. 打开 https://github.com/yiluxiangqian02/MicroHySeeker
2. 切到 `feat/A` 分支
3. 点击 "Pull requests" 标签页
4. 点击 "New pull request"
5. 选择：
   - base: `autohyseeker`
   - compare: `feat/A`
6. 编写 PR 标题和描述
7. 点击 "Create pull request"

**PR 描述建议模板：**
```markdown
## 改动内容
- 实现了 XX 功能
- 修复了 YY bug
- 添加了 ZZ 测试

## 改动文件
- src/agents/data_analyst.py (新增)
- frontend/src/pages/Dashboard.tsx (修改)

## 测试情况
- [x] 本地测试通过
- [x] 没有新的 lint 错误

## 备注
如有疑问请 mention @同事名
```

---

## ⚠️ 关键：第一个 merge vs 第二个 merge（最常见的疑问）

### 原理：三路合并

当 feat/B 要 merge 时，autohyseeker 已经包含了 feat/A 的改动。Git 用"三路合并"来处理：

```
      A0 (common base - 两个分支的共同祖先)
     /  \
    /    \
feat/A   feat/B
(改动1)  (改动2)
  ↓        ↓
merge    merge
  ↓        ↓
autohyseeker (最终包含两个改动)
```

Git 的逻辑：
1. **对比两个分支相对于 A0 的改动**
2. 如果改的文件**不重叠** → ✅ 自动合并成功
3. 如果改的文件**有重叠** → ⚠️ 冲突，需要手动解决

### 例子 1：A 改 agents，B 改 frontend（不重叠）✅

```
A0: config/
├── agents/
├── frontend/

你 (feat/A):     他 (feat/B):
├── agents/ ← 改  ├── frontend/ ← 改
├── frontend/     ├── agents/

合并结果自动成功：
✅ agents/(你改) + frontend/(他改)
```

### 例子 2：A 改 config.py，B 也改 config.py（重叠）⚠️

```
A0: 
├── config.py (v1)

你 (feat/A):
├── config.py (v1 → v2 你的改动)

他 (feat/B):
├── config.py (v1 → v3 他的改动)

合并时：
Git 说："嘿，我看到 config.py 从 v1 分别变成了 v2 和 v3"
Git 问："该保留哪个？"
→ ⚠️ 冲突需要手动决定
```

### 关键答案：第二个 merge 不会基于第一个 merge，而是基于 A0

```
feat/B 永远基于 A0（初始状态）
即使 feat/A 已经 merge 了
feat/B merge 时用"三路合并"来理解 autohyseeker 的新内容
```

---

### 第4步：Code Review 和冲突处理

**情况1：没有冲突 ✅**
```bash
# GitHub 会自动提示"This branch has no conflicts with the base branch"
# 直接点 "Squash and merge" 或 "Merge pull request" 即可
```

**情况2：有冲突 ⚠️**

#### 方法 A：网页上解决（简单冲突用）
```bash
# GitHub PR 页面会显示 "This branch has conflicts..."
# 点击 "Resolve conflicts" 按钮
# 找到冲突标记：
# <<<<<<<< feat/B (你的改动)
# ...
# ========
# ...
# >>>>>>>> autohyseeker (对方的改动)
# 手动编辑，只保留需要的部分，删除 <<< === >>> 标记
# 点 "Mark as resolved"
# GitHub 自动检测无冲突，可以 merge
```

#### 方法 B：本地解决（推荐，更安全）✅

这是**最后一个人必须做**的步骤：

```bash
# 假设你是第二个 merge 的，你的分支是 feat/B
git fetch origin

# 同步最新的 autohyseeker（已经包含第一个人的 merge）
git rebase origin/autohyseeker

# Git 检查 feat/B 相对于 A0 的改动和 autohyseeker 相对于 A0 的改动
# 如果有冲突，Git 会暂停并列出冲突文件

# 手动编辑冲突文件
# 打开文件，找到 <<<<<<<, =======, >>>>>>>
# 根据实际需要保留内容，删除冲突标记

git add <冲突文件>
git rebase --continue  # 注意：rebase 不是 merge，所以是 --continue

# 推送回去
git push -f origin feat/B  # 注意：-f 是因为 rebase 改了历史

# GitHub PR 页面自动刷新，显示"This branch can be automatically merged"
# 现在点击 merge 即可
```

**本地解决 vs 网页解决的区别：**
- 网页：快速，但看不到全貌
- 本地：可以运行测试、看代码上下文、更安全


---

### 第5步：合并（Merge）

**A 部分的同学操作：**
```bash
# 在 GitHub PR 页面点击 "Merge pull request"
# 选择 merge 方式：

# 推荐：Squash and merge
# - 所有 A 相关的 commit 合并成 1 个
# - autohyseeker 历史更干净
# - 命令行也可以：
git checkout autohyseeker
git pull origin autohyseeker
git merge --squash feat/A
git commit -m "feat: A部分完成"
git push origin autohyseeker
```

**B 部分的同学操作（在 A merge 之后）：**
```bash
git checkout feat/B
git fetch origin
git rebase origin/autohyseeker  # 同步 A 的改动到本地

# 如果有冲突，手动解决
# 解决后：
git rebase --continue
git push -f origin feat/B  # 注意这里是 -f（强制），因为 rebase 改了历史

# 然后提 PR，重复第3-5步
```

---

## 冲突避免 Tips

### ✅ 怎样减少冲突

1. **明确职责边界**
   - A 只改：`src/agents/` 下的某些文件
   - B 只改：`frontend/src/components/` 下的某些文件
   - **共同文件（如 `config.json`）要提前沟通**

2. **频繁同步**
   - 不要等 A 完全做完再开始 B
   - B 可以先开发 "不依赖 A" 的部分
   - 遇到依赖，B 的分支就先 rebase 以获取 A 的最新代码

3. **分支保护规则**（可选，企业级推荐）
   - 在 GitHub 设置 autohyseeker 为 protected branch
   - 要求：必须通过 PR + review 才能 merge
   - 要求：PR merge 前必须通过 CI 检查
   - 设置地址：https://github.com/yiluxiangqian02/MicroHySeeker/settings/branches

---

## 快速参考

| 场景 | 命令 |
|------|------|
| 查看所有本地分支 | `git branch` |
| 查看远端分支 | `git branch -r` |
| 切换到 A 分支 | `git checkout feat/A` |
| 看 A 比 autohyseeker 多了什么 | `git diff autohyseeker...feat/A` |
| 看 A 新增的文件 | `git diff --name-status autohyseeker feat/A` |
| 看某文件在 A 中的改动 | `git diff autohyseeker feat/A -- src/file.py` |
| 推送 A 分支 | `git push origin feat/A` |
| 提交后撤销最后一个 commit | `git reset --soft HEAD~1` |
| 强制同步远端分支 | `git fetch origin && git reset --hard origin/feat/A` |
| 删除本地分支（完成后） | `git branch -d feat/A` |
| 删除远端分支（完成后） | `git push origin --delete feat/A` |

---

## 完整例子

### 你完成 A 部分（从开始到 merge）

```bash
# Day 1：开始开发
git checkout feat/A
echo "# A 部分初始化" > src/agents/a_module.py
git add src/agents/a_module.py
git commit -m "feat: A部分 - 初始框架"
git push origin feat/A

# Day 2：继续开发
# ... 在 src/agents/a_module.py 中编辑 ...
git add src/agents/a_module.py
git commit -m "feat: A部分 - 添加核心逻辑"
git push origin feat/A

# Day 3：完成，提 PR
git push origin feat/A  # 确保最新推送
# 打开浏览器：https://github.com/yiluxiangqian02/MicroHySeeker/pulls
# 点"New pull request"或"Compare & pull request"
# base: autohyseeker, compare: feat/A
# 填写描述，点"Create pull request"

# 等待同事或自己 review，确认无冲突
# 点"Merge pull request" → "Squash and merge" → "Confirm squash and merge"

# 完成！autohyseeker 现在包含 A 部分
```

---

## 常见问题

**Q: 我改了一半，同事部分已经推到 autohyseeker，我怎么拿到他的改动？**
```bash
git checkout feat/A
git fetch origin
git rebase origin/autohyseeker
# 如果有冲突，手动解决后 git rebase --continue
git push -f origin feat/A  # 更新远端
```

**Q: 我提了 PR 后又发现有 bug，怎么办？**
```bash
# 继续在同一分支改，然后 push
git add .
git commit -m "fix: 修复 PR 中的 bug"
git push origin feat/A
# GitHub PR 会自动更新，无需重新创建
```

**Q: 能直接 force push 吗？**
```bash
# 尽量避免。如果非要 force push，确保你确实想改历史
# 通常只在 rebase 之后才用 -f
git push -f origin feat/A

# 如果你和同事都在用这个分支，force push 会害死他
# ❌ 不要这样做
```

**Q: feat/A 和 autohyseeker 越来越不同步，现在提 PR 冲突太多了，怎么办？**
```bash
# 这说明应该更早 rebase
git checkout feat/A
git rebase origin/autohyseeker  # 把 autohyseeker 的新改动接到 A 底部

# 手动解决冲突...
git rebase --continue
git push -f origin feat/A  # 强制更新（因为 rebase 改了历史）
```

**Q: 第一个人 merge 后，第二个人 merge 会不会冲突？**
```bash
# 答：可能会，取决于改的文件是否重叠

# 场景 A：不重叠 ✅
# 第一个人改 src/agents/
# 第二个人改 frontend/src/
# 结果：自动合并成功，不需要任何额外操作

# 场景 B：有重叠 ⚠️
# 第一个人改 src/config.py
# 第二个人也改 src/config.py
# 结果：第二个人的 PR 会显示冲突
#       第二个人需要 rebase + 手动解决冲突 + push
# 命令：
git fetch origin
git checkout feat/B
git rebase origin/autohyseeker  # 同步最新的 autohyseeker
# Git 会显示冲突，手动解决...
git add src/config.py
git rebase --continue
git push -f origin feat/B
# 现在 PR 页面显示"可合并"
```

**Q: 如果两个人改同一个文件不同部分，会冲突吗？**
```bash
# 答：通常不会。Git 很聪明，能识别不同的行。

# 例子：config.py
# 初始状态：
#   line 1: name = "default"
#   line 2: version = "1.0"

# 第一个人改 line 1
# 第二个人改 line 2

# 结果：Git 自动合并，两个改动都保留 ✅

# 但如果改的是同一行，就会冲突 ⚠️
```

**Q: Squash merge vs Merge commit，用哪个？**
```bash
# 推荐：Squash and merge
# 原因：
# - Squash：把 feat/A 的所有 commit 合并成 1 个
#   好处：autohyseeker 历史简洁，容易回滚整个功能
# - Merge commit：保留 feat/A 所有 commit，增加一个 merge commit
#   好处：完整保留开发过程，但历史会变复杂

# 你们的建议：用 Squash
git checkout autohyseeker
git pull origin autohyseeker
git merge --squash feat/A
git commit -m "feat: A部分完成"
git push origin autohyseeker
```

---

## 完整流程示例（两个人都 merge 的情况）

### Day 1：你完成 A 并 merge

```bash
# 你
git checkout feat/A
echo "# A 模块初始化" > src/agents/a_module.py
git add src/agents/a_module.py
git commit -m "feat: A部分 - 初始框架"
git push origin feat/A

# 创建 PR → review → merge
# 现在 autohyseeker 包含了 A 的改动
```

### Day 2：同事完成 B 并 merge

```bash
# 同事（在完成 B 代码后）
git checkout feat/B

# 重要：同步最新的 autohyseeker（已包含你的改动）
git fetch origin
git rebase origin/autohyseeker

# 如果有冲突（因为两个人改了同一文件），现在解决
# 打开、编辑冲突文件...
git add <冲突文件>
git rebase --continue

# 推送更新后的分支（-f 是因为 rebase 改了历史）
git push -f origin feat/B

# 创建 PR → review → merge
# 现在 autohyseeker = A 改动 + B 改动（冲突已解决）
```

### 结果

```
autohyseeker 最终包含：
✅ A 部分的所有改动
✅ B 部分的所有改动
✅ 冲突已手动解决
✅ 历史清晰（每个分支一个 squash commit）
```

---

**总结：用 feat/A + feat/B + PR 流程 = 企业级标准！**
**关键：最后 merge 的人记得 rebase + 解决冲突**
