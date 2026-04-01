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

### 第4步：Code Review 和冲突处理

**情况1：没有冲突 ✅**
```bash
# GitHub 会自动提示"This branch has no conflicts with the base branch"
# 直接点 "Squash and merge" 或 "Merge pull request" 即可
```

**情况2：有冲突 ⚠️**
```bash
# GitHub 会显示冲突文件

# 方法1：在网页上解决（只适合简单冲突）
# - 点击 "Resolve conflicts"
# - 手动编辑冲突标记
# - 点 "Mark as resolved"

# 方法2：本地解决（推荐，更安全）
git fetch origin
git checkout feat/A
git merge origin/autohyseeker

# Git 会标记冲突，你手动修改，然后
git add <冲突文件>
git commit -m "merge: 解决与 autohyseeker 的冲突"
git push origin feat/A

# GitHub 会自动检测冲突已解决，PR 可以继续 merge
```

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

---

**总结：用 feat/A + feat/B + PR 流程就是企业级标准了！**
