#!/usr/bin/env bash
# yanxuan-skills 同步工具
# 用法: ./sync.sh {to-local|to-server|out|capture}
# 仓库 skills/<name>/ 为唯一源;本地 ~/.claude/skills 与服务器 openclaw 都从这里取。
# 当前策略:skill 只保留 SKILL.md + references + scripts(+ evals),不带 assets/png。
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SKILL="structured-product-copywriter"
REPO_SKILL="$HERE/skills/$SKILL"
LOCAL_SKILL="$HOME/.claude/skills/$SKILL"
SERVER_SKILL="/root/.openclaw/workspace/skills/$SKILL"
SSH="jiuyueming-ecs"
EXCLUDES="$HERE/.sync-excludes"

# tar 排除参数(从 .sync-excludes 生成),供 capture 用
tar_excludes() {
  while IFS= read -r pat; do
    [ -z "$pat" ] && continue
    printf ' --exclude=%s' "$pat"
  done < "$EXCLUDES"
}

# 仓库里要分发的条目:SKILL.md + 现有子目录(不含 assets)
repo_items() {
  echo SKILL.md
  for d in "$REPO_SKILL"/*/; do
    [ -d "$d" ] || continue
    basename "$d"
  done
}

# 分发:仓库 -> 目标。按源条目覆盖,保留目标 workdir/ 与顶层产出物。
#   $1=local|server
distribute() {
  local kind="$1" dest
  case "$kind" in
    local)  dest="$LOCAL_SKILL" ;;
    server) dest="$SERVER_SKILL" ;;
    *) echo "bad kind"; exit 1 ;;
  esac
  echo "→ to-$kind: $REPO_SKILL -> $dest"
  local items; items="$(repo_items)"
  if [ "$kind" = "local" ]; then
    mkdir -p "$dest"
    cp -a "$REPO_SKILL/SKILL.md" "$dest/" 2>/dev/null || true
    for d in $items; do
      [ "$d" = "SKILL.md" ] && continue
      rm -rf "$dest/$d" && mkdir -p "$dest/$d" && cp -a "$REPO_SKILL/$d/." "$dest/$d/"
    done
    # 策略:本地不带 assets,清掉旧 assets
    rm -rf "$dest/assets" 2>/dev/null || true
  else
    local tmp; tmp="$(mktemp -d)"
    ( cd "$REPO_SKILL" && tar czf "$tmp/bundle.tgz" $items )
    ssh "$SSH" "mkdir -p '$SERVER_SKILL' && cd '$SERVER_SKILL' && $(for d in $items; do [ "$d" = "SKILL.md" ] || printf 'rm -rf %s && ' "$d"; done | sed 's/ && $//') && tar xzf -" < "$tmp/bundle.tgz"
    rm -rf "$tmp"
    # 服务器 assets/ 不动(它是 live 运行态,保留)
  fi
  echo "✓ done"
}

cmd_to_local()   { distribute local; }
cmd_to_server()  { distribute server; echo "  (openclaw 文件级读取,下次 agent 调用即生效)"; }
cmd_out()        { cmd_to_local; cmd_to_server; }

cmd_capture() {
  echo "→ capture: $SSH:$SERVER_SKILL -> $REPO_SKILL (strip junk + no assets)"
  local tmp; tmp="$(mktemp -d)"/spc
  local exc; exc="$(tar_excludes)"
  eval "ssh \"\$SSH\" \"cd \\\"$SERVER_SKILL\\\" && tar czf - $exc .\"" | tar xzf - -C "$tmp/"
  # 兜底清顶层非源文件 + 彻底去 assets/png(策略:仓库不带图)
  rm -f "$tmp/manifest.json" "$tmp"/*.docx "$tmp"/copy_*.txt 2>/dev/null || true
  rm -rf "$tmp/assets" 2>/dev/null || true
  # 密钥扫描闸
  if grep -rnE 'sk-[A-Za-z0-9]{20,}|cli_a[a-z0-9]{10,}|appSecret.*[:=].*["'"'"'][A-Za-z0-9]{8,}' "$tmp" 2>/dev/null; then
    echo "✗ 检测到疑似密钥,已中断 capture。请人工核查后重试。" >&2
    rm -rf "$tmp"; exit 1
  fi
  # 覆盖仓库 skill 目录(仅保留 SKILL.md/references/scripts/evals)
  mkdir -p "$REPO_SKILL"
  rm -rf "$REPO_SKILL/assets"
  ( cd "$tmp" && tar czf - SKILL.md references scripts evals 2>/dev/null ) | tar xzf - -C "$REPO_SKILL/" 2>/dev/null || true
  rm -rf "$tmp"
  echo "✓ captured (仅 SKILL.md/references/scripts/evals),请 git status / diff 复核后 commit"
  cd "$HERE" && git status --short
}

case "${1:-}" in
  to-local)  cmd_to_local ;;
  to-server) cmd_to_server ;;
  out)       cmd_out ;;
  capture)   cmd_capture ;;
  *) echo "usage: $0 {to-local|to-server|out|capture}"; exit 1 ;;
esac
