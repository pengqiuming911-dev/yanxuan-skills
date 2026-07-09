# yanxuan-skills 同步与统一管理 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把服务器 openclaw 的 `structured-product-copywriter` skill 剥成干净源文件入 `yanxuan-skills` 公开仓库,并建一个 `sync.sh` 支持 仓库↔本地↔服务器 的分发与抓回。

**Architecture:** 仓库为唯一源;`sync.sh` 用 rsync + 共用 `.sync-excludes` 做分发(to-local/to-server/out)与抓回(capture,带密钥扫描)。初始入库用 capture 从服务器 B 版剥垃圾。

**Tech Stack:** bash、rsync(本地 Git Bash 自带 / 服务器自带)、ssh(jiuyueming-ecs 免密已配)、git。

## Global Constraints

- 仓库公开(`https://github.com/pengqiuming911-dev/yanxuan-skills.git`),**绝不**入库:凭证、`.bak*`、`__pycache__`/`*.pyc`、`workdir/`、`*.docx` 产出物、scratch 截图、`.openclaw/`。
- 本地工作目录:`/d/projects/yanxuan-skills`(已 git clone,空仓库,git 身份 pengqiuming/pengqiuming911@gmail.com)。
- SSH 别名 `jiuyueming-ecs` 已配免密。
- skill 名固定 `structured-product-copywriter`,仓库内路径 `skills/structured-product-copywriter/`(下文简称 `skills/spc/`)。
- 服务器 skill 路径:`/root/.openclaw/workspace/skills/structured-product-copywriter/`(B,live)与 `/root/.claude/skills/structured-product-copywriter/`(A,clean 安装快照,仅参考其 asset 集)。
- 本地 skill 目标:`~/.claude/skills/structured-product-copywriter/`(即 `C:/Users/WIKO/.claude/skills/structured-product-copywriter/`)。

---

### Task 1: 从服务器 capture 干净 skill 源文件到仓库

**Files:**
- Create: `skills/structured-product-copywriter/` 下 `SKILL.md`、`references/*.md`、`scripts/*.py`、`evals/evals.json`、`assets/*.png`

**Interfaces:**
- Consumes: 服务器 `/root/.openclaw/workspace/skills/structured-product-copywriter/`(B 版内容)
- Produces: 仓库 `skills/spc/` 下的干净源文件(供 Task 2-6 使用)

- [ ] **Step 1: 建临时排除规则文件(供 capture 用,后续固化为 `.sync-excludes`)**

写到 `/d/projects/yanxuan-skills/.sync-excludes`:

```
*.bak*
*.pyc
__pycache__/
workdir/
.openclaw/
copy_announce.txt
copy_long.txt
copy_short.txt
推介材料.docx
*.docx
```

- [ ] **Step 2: rsync 服务器 skill → 临时目录(套排除规则)**

```bash
cd /d/projects/yanxuan-skills
rm -rf /tmp/spc-capture
mkdir -p /tmp/spc-capture
rsync -a --exclude-from=.sync-excludes \
  jiuyueming-ecs:/root/.openclaw/workspace/skills/structured-product-copywriter/ \
  /tmp/spc-capture/
```
Expected: `/tmp/spc-capture/` 含 `SKILL.md`、`references/`(仅 .md)、`scripts/`(仅 .py)、`evals/`、`assets/`(png,含 scratch)、`manifest.json`(顶层)、`copy_*.txt` 已被排除。

- [ ] **Step 3: 删顶层 `manifest.json` 等非源文件**

capture 后顶层可能残留 `manifest.json`(运行态产物,非 skill 源):

```bash
rm -f /tmp/spc-capture/manifest.json /tmp/spc-capture/*.docx /tmp/spc-capture/copy_*.txt
ls -la /tmp/spc-capture/
```
Expected: 顶层仅 `SKILL.md` + 目录 `assets/ evals/ references/ scripts/`(及可能的 `manifest.json` 已删)。

- [ ] **Step 4: 复制到仓库 skill 目录**

```bash
mkdir -p skills/structured-product-copywriter
rsync -a /tmp/spc-capture/ skills/structured-product-copywriter/
```

- [ ] **Step 5: 验证源文件就位**

```bash
cd /d/projects/yanxuan-skills
echo "--- SKILL.md ---" && ls -la skills/spc/SKILL.md
echo "--- references ---" && ls skills/spc/references/
echo "--- scripts ---" && ls skills/spc/scripts/
echo "--- evals ---" && ls skills/spc/evals/
echo "--- assets count ---" && ls skills/spc/assets/ | wc -l
```
Expected: `SKILL.md` 22545 字节左右;references 仅 .md(amac-manager.md/docx-template.md/feishu-upload.md/product-position-card.md/tongyu-winrate.md);scripts 仅 .py(无 .bak/__pycache__);evals/evals.json;assets 仍含 scratch(下一步 prune)。

- [ ] **Step 6: 提交"已 capture 但未 prune"快照(便于回看)**

```bash
git add skills/ && git commit -m "feat(skill): capture structured-product-copywriter from server (pre-prune)"
```

---

### Task 2: prune assets 到 SKILL.md/references 实际引用集 + 密钥扫描

**Files:**
- Modify: `skills/structured-product-copywriter/assets/`(删非引用 png)

**Interfaces:**
- Consumes: `skills/spc/SKILL.md`、`skills/spc/references/*.md`(提取 `assets/xxx.png` 引用)
- Produces: `skills/spc/assets/` 仅含被引用 png(~7 张)

- [ ] **Step 1: 提取被引用的 assets 集合**

```bash
cd /d/projects/yanxuan-skills/skills/spc
grep -rhoE 'assets/[^"'"'"' )]+\.(png|jpg|jpeg|gif|svg)' SKILL.md references/ 2>/dev/null | sed 's#assets/##' | sort -u > /tmp/assets-keep.txt
cat /tmp/assets-keep.txt
wc -l < /tmp/assets-keep.txt
```
Expected: ~7 行,含 `amac-manager.png`、`amac-product.png`、`product-card-中证1000-DCN.png`、`tongyu-winrate-中证1000-降敲DCN.png`、`winrate-full-raw.png` 等。

- [ ] **Step 2: 删除 assets/ 中不在保留集的文件**

```bash
cd /d/projects/yanxuan-skills/skills/spc/assets
# 保留集里有的留下,其余删
while IFS= read -r f; do keep["$f"]=1; done < /tmp/assets-keep.txt
for f in *; do [ -n "${keep[$f]:-}" ] || rm -f -- "$f"; done
ls -la
```
Expected: assets/ 仅剩 ~7 个被引用 png,体积从 ~12MB 降到 ~3MB 内。

- [ ] **Step 3: 整仓密钥扫描(安全闸)**

```bash
cd /d/projects/yanxuan-skills
grep -rnE 'sk-[A-Za-z0-9]{20,}|cli_a[a-z0-9]{10,}|appSecret.*[:=].*["'\''][A-Za-z0-9]{8,}|password.*[:=].*["'\''][A-Za-z0-9]{4,}' skills/ 2>/dev/null
```
Expected: **无输出**(命中即中断,人工核查后改外部化再继续)。脚本中已有的 `tongyu-creds.json`/`workbench-token.json` 文件**读取路径**不算命中(那不是密钥本体)。

- [ ] **Step 4: 验证无垃圾残留**

```bash
cd /d/projects/yanxuan-skills
find skills/ -name '*.bak*' -o -name '*.pyc' -o -name '__pycache__' -o -name 'workdir' -o -name '*.docx' -o -name '.openclaw' 2>/dev/null
ls skills/spc/   # 顶层不应有 copy_*.txt / 推介材料.docx / manifest.json
```
Expected: `find` 无输出;顶层仅 `SKILL.md assets/ evals/ references/ scripts/`。

- [ ] **Step 5: 提交 pruned 干净版**

```bash
cd /d/projects/yanxuan-skills
git add -A skills/ && git commit -m "chore(skill): prune assets to referenced set, strip junk"
```

---

### Task 3: 写 .gitignore(与 .sync-excludes 对齐)

**Files:**
- Create: `.gitignore`(`.sync-excludes` Task1 已建)

- [ ] **Step 1: 写 .gitignore**

```
# Python
__pycache__/
*.pyc

# Backups
*.bak*

# Runtime outputs / 产出物
workdir/
*.docx
~$*

# Install metadata
.openclaw/

# 凭证(本就在 skill 目录外,兜底)
tongyu-creds.json
workbench-token.json

# 临时
/tmp/
```

- [ ] **Step 2: 验证 git 不跟踪垃圾**

```bash
cd /d/projects/yanxuan-skills
git add -A && git status --short
```
Expected: 仅 `.gitignore`、`.sync-excludes` 待提交,无 `.docx/.bak/__pycache__`。

- [ ] **Step 3: 提交**

```bash
git commit -m "chore: add .gitignore and .sync-excludes"
```

---

### Task 4: 写 sync.sh(to-local / to-server / out / capture + 密钥扫描)

**Files:**
- Create: `sync.sh`

**Interfaces:**
- Consumes: `.sync-excludes`、仓库 `skills/spc/`、SSH `jiuyueming-ecs`、本地 `~/.claude/skills/`
- Produces: 四个子命令的副作用(分发/抓回)

- [ ] **Step 1: 写 sync.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SKILL="structured-product-copywriter"
REPO_SKILL="$HERE/skills/$SKILL"
LOCAL_SKILL="$HOME/.claude/skills/$SKILL"
SERVER_SKILL="/root/.openclaw/workspace/skills/$SKILL"
SSH="jiuyueming-ecs"

# 分发:仓库 -> 目标。按源子目录 rsync --delete,保留目标 workdir/ 与顶层产出物。
distribute_to() {
  local dest="$1"; shift
  local rsync_dest_args=()
  [ -n "${SSH_HOST:-}" ] && rsync_dest_args=(--rsh="ssh")
  rsync -a "${rsync_dest_args[@]}" \
    "$REPO_SKILL/SKILL.md" "$dest/" 2>/dev/null || true
  for d in references scripts evals assets; do
    rsync -a --delete "${rsync_dest_args[@]}" \
      "$REPO_SKILL/$d/" "$dest/$d/"
  done
}

cmd_to_local() {
  echo "→ to-local: $REPO_SKILL -> $LOCAL_SKILL"
  distribute_to "$LOCAL_SKILL"
  echo "✓ done"
}

cmd_to_server() {
  echo "→ to-server: $REPO_SKILL -> $SERVER_SKILL (via $SSH)"
  SSH_HOST=1 distribute_to "$SSH:$SERVER_SKILL"
  echo "✓ done (openclaw 文件级读取,下次调用即生效)"
}

cmd_out() { cmd_to_local; cmd_to_server; }

cmd_capture() {
  echo "→ capture: $SSH:$SERVER_SKILL -> $REPO_SKILL (strip junk)"
  local tmp; tmp="$(mktemp -d)"/spc
  rsync -a --exclude-from="$HERE/.sync-excludes" \
    "$SSH:$SERVER_SKILL/" "$tmp/"
  rm -f "$tmp/manifest.json" "$tmp"/*.docx "$tmp"/copy_*.txt 2>/dev/null || true
  # prune assets 到被引用集
  local keep; keep="$(grep -rhoE 'assets/[^"'"'"' )]+\.(png|jpg|jpeg|gif|svg)' \
      "$tmp/SKILL.md" "$tmp/references/" 2>/dev/null \
      | sed 's#assets/##' | sort -u)"
  if [ -d "$tmp/assets" ]; then
    ( cd "$tmp/assets" && \
      while IFS= read -r f; do touch "/tmp/.keep-$$-$f" 2>/dev/null; done <<<"$keep"; \
      for f in *; do echo "$keep" | grep -qxF "$f" || rm -f -- "$f"; done ) 2>/dev/null || true
  fi
  # 密钥扫描闸
  if grep -rnE 'sk-[A-Za-z0-9]{20,}|cli_a[a-z0-9]{10,}|appSecret.*[:=].*["'"'"'][A-Za-z0-9]{8,}' "$tmp" 2>/dev/null; then
    echo "✗ 检测到疑似密钥,已中断 capture。请人工核查后重试。" >&2
    exit 1
  fi
  mkdir -p "$REPO_SKILL"
  rsync -a --delete "$tmp/" "$REPO_SKILL/"
  rm -rf "$tmp"
  echo "✓ captured,请 git status / diff 复核后 commit"
  cd "$HERE" && git status --short
}

case "${1:-}" in
  to-local) cmd_to_local ;;
  to-server) cmd_to_server ;;
  out) cmd_out ;;
  capture) cmd_capture ;;
  *) echo "usage: $0 {to-local|to-server|out|capture}"; exit 1 ;;
esac
```

- [ ] **Step 2: 加可执行权限并 syntax check**

```bash
cd /d/projects/yanxuan-skills
chmod +x sync.sh
bash -n sync.sh && echo "syntax ok"
```
Expected: 输出 `syntax ok`。

- [ ] **Step 3: 冒烟测 `sync.sh`(无参应打印 usage)**

```bash
./sync.sh; echo "exit=$?"
```
Expected: 打印 `usage: ... {to-local|to-server|out|capture}` 且 `exit=1`。

- [ ] **Step 4: 提交**

```bash
git add sync.sh && git commit -m "feat: add sync.sh (to-local/to-server/out/capture + secret scan)"
```

---

### Task 5: 写 README.md

**Files:**
- Create: `README.md`

- [ ] **Step 1: 写 README.md**

内容包含:仓库用途、目录结构、当前 skill 列表、如何用 `sync.sh` 安装到本地/服务器、如何 capture 回抓、安全说明(凭证外部化)、干净边界(什么不入仓)。

- [ ] **Step 2: 提交**

```bash
git add README.md && git commit -m "docs: add README"
```

---

### Task 6: push 到 GitHub 并验证仓库干净

**Files:**
- 无新建,仅 git push + 远端核对

- [ ] **Step 1: 设上游并 push**

```bash
cd /d/projects/yanxuan-skills
git push -u origin main 2>&1 | tail -10
```
Expected: 推送成功(`To https://github.com/pengqiuming911-dev/yanxuan-skills.git * [new branch]`)。

- [ ] **Step 2: 远端验证结构干净**

```bash
git ls-tree -r --name-only HEAD | sed 's/^/  /'
echo "--- 垃圾扫描(应为空)---"
git ls-tree -r --name-only HEAD | grep -E '\.(bak|pyc|docx)$|__pycache__|workdir/|\.openclaw/' || echo "clean"
```
Expected: 树含 `README.md`、`.gitignore`、`.sync-excludes`、`sync.sh`、`docs/specs/...`、`docs/superpowers/plans/...`、`skills/structured-product-copywriter/{SKILL.md,references/*.md,scripts/*.py,evals/evals.json,assets/*.png}`;垃圾扫描输出 `clean`。

---

### Task 7: 部署到本地并验证(可选:到服务器)

**Files:**
- 无新建,运行 `sync.sh to-local` + 验证

- [ ] **Step 1: 部署到本地**

```bash
cd /d/projects/yanxuan-skills
./sync.sh to-local
```
Expected: `→ to-local ...` → `✓ done`,本地 `~/.claude/skills/structured-product-copywriter/SKILL.md` 为仓库版。

- [ ] **Step 2: 核对本地 skill 与仓库一致**

```bash
diff <(cat skills/spc/SKILL.md) <(cat ~/.claude/skills/structured-product-copywriter/SKILL.md) && echo "SKILL.md identical"
ls ~/.claude/skills/structured-product-copywriter/
```
Expected: `SKILL.md identical`;目录含 SKILL.md/assets/evals/references/scripts,且**未带入** workdir(本地原有 workdir 保留,不受影响)。

- [ ] **Step 3: (可选,服务器已是源)到服务器回写验证一致**

服务器本就是 capture 源,正常无需 `to-server`。若要校验分发链路通,可:

```bash
./sync.sh to-server
ssh jiuyueming-ecs "diff <(cat /root/.openclaw/workspace/skills/structured-product-copywriter/SKILL.md) <(cat -)" <<<"$(cat skills/spc/SKILL.md)" >/dev/null 2>&1 && echo "server SKILL.md identical" || echo "differs"
```
Expected: `server SKILL.md identical`(或跳过本步)。

- [ ] **Step 4: 收尾 commit(若 README/sync 有小修)**

```bash
git status --short   # 若有改动则 add+commit,否则跳过
```
