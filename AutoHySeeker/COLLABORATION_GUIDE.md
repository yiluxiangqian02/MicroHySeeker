# AutoHySeeker A/B 分工开发指南

## 当前状态

已从 `autohyseeker` 主分支创建了两个独立分支：

```
autohyseeker (主分支)
├── feat/A  (你的分支 - 改 A 部分)
└── feat/B  (同事的分支 - 改 B 部分)
```

**base commit**: `bfaefcb1` - 融合版本1（加了故障部分）

---

## 开发工作流

### 第一步：切换到各自分支

**你** (负责 A 部分):
```powershell
git checkout feat/A
```

**同事** (负责 B 部分):
```powershell
git checkout feat/B
```

### 第二步：各自开发

在 `feat/A` 分支上：
```powershell
# 改 A 部分的代码
# ... 编辑文件 ...

# 频繁提交（每个小功能一个 commit）
git add .
git commit -m "feat: A部分 - XXX功能"

# 推送到远端（方便同事查看进度）
git push origin feat/A
```

在 `feat/B` 分支上同理。

### 第三步：合并回主分支（分别合并）

**A 部分完成后** (你操作):
```powershell
git checkout autohyseeker
git pull origin autohyseeker
git merge feat/A
git push origin autohyseeker
```

**B 部分完成后** (同事操作):
```powershell
git checkout autohyseeker
git pull origin autohyseeker  # 拉 A 部分的改动
git merge feat/B
git push origin autohyseeker
```

---

## 常见场景

### 场景 1：A/B 都改了同一个文件

**出现冲突时**，git 会标记冲突部分。寻找标记并手动解决：

```
<<<<<<< feat/A
你的改动
=======
同事的改动
>>>>>>> feat/B
```

保留需要的内容，删除冲突标记后 `git add` 并 `commit`。

### 场景 2：需要 A 完成后 B 才能推进

B 分支获取 A 的最新改动：
```powershell
git fetch origin
git rebase origin/autohyseeker  # 同步最新的 autohyseeker
```

这样 B 分支就建立在最新的 A 部分基础上。

### 场景 3：临时需要切换分支

```powershell
# 保存当前改动（如果还未 commit）
git stash

# 切换分支
git checkout feat/B

# 完成后回到 A
git checkout feat/A

# 恢复之前的改动
git stash pop
```

---

## 推荐做法

✅ **尽量减少冲突**
- 沟通好 A/B 各自改哪些文件，避免重叠
- 如果必须改同一个文件，频繁沟通，及时 pull

✅ **频繁 commit**
- 每个逻辑单元一个 commit（如"added error handler"）
- 方便 review，也方便日后回滚

✅ **定期同步**
- 每建议的是 A/B 每完成一个小功能块就推送一次
- 这样对方可以及时看到进展，提早发现冲突

✅ **最后合并时保持分支顺序**
- A 完成 merge 回 autohyseeker
- B 再 rebase + merge
- 这样历史线性清晰

---

## 快速参考

| 操作 | 命令 |
|------|-------|
| 查看所有分支 | `git branch -a` |
| 切换到 A 分支 | `git checkout feat/A` |
| 查看分支差异 | `git diff autohyseeker feat/A` |
| 看 A 新增了哪些文件 | `git diff --name-status autohyseeker feat/A` |
| A 分支推送 | `git push origin feat/A` |
| 取消最后一个 commit | `git reset --soft HEAD~1` |
| 查看 commit 历史 | `git log --oneline --graph --all` |

---

**问题或困惑？** 
- 查看 git 状态：`git status`
- 查看某文件的冲突：`git diff <filename>`
