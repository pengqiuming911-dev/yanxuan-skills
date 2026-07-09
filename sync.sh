#!/usr/bin/env bash
# yanxuan-skills 同步工具
# 用法: ./sync.sh {to-local|to-server|out|capture}
# 仓库 skills/<name>/ 为唯一源;本地 ~/.claude/skills 与服务器 openclaw 都从这里取。
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

# 分发:仓库 -> 目标。按源子目录 tar 覆盖,保留目标 workdir/ 与顶层产出物。
#   $1=目标类型 local|server
distribute() {
  local kind="$1"
  case "$kind" in
    local)  dest="$LOCAL_SKILL" ;;
    server) dest="$SERVER_SKILL" ;;
    *) echo "bad kind"; exit 1 ;;
  esac
  echo "→ to-$kind: $REPO_SKILL -> $dest"
  if [ "$kind" = "local" ]; then
    mkdir -p "$dest"
    cp -a "$REPO_SKILL/SKILL.md" "$dest/"
    for d in references scripts evals assets; do
      rm -rf "$dest/$d" && mkdir -p "$dest/$d" && cp -a "$REPO_SKILL/$d/." "$dest/$d/"
    done
  else
    # 服务器:tar 打包子目录,远端按目录解包(覆盖式)
    local tmp; tmp="$(mktemp -d)"
    tar czf "$tmp/bundle.tgz" -C "$REPO_SKILL" SKILL.md references scripts evals assets
    ssh "$SSH" "mkdir -p '$SERVER_SKILL' && cd '$SERVER_SKILL' && rm -rf references scripts evals assets && tar xzf -" < "$tmp/bundle.tgz"
    rm -rf "$tmp"
  fi
  echo "✓ done"
}

cmd_to_local()   { distribute local; }
cmd_to_server()  { distribute server; echo "  (openclaw 文件级读取,下次 agent 调用即生效)"; }
cmd_out()        { cmd_to_local; cmd_to_server; }

cmd_capture() {
  echo "→ capture: $SSH:$SERVER_SKILL -> $REPO_SKILL (strip junk)"
  local tmp; tmp="$(mktemp -d)"/spc
  # 服务器 tar 排除垃圾,流式下到临时目录
  local exc; exc="$(tar_excludes)"
  eval "ssh \"\$SSH\" \"cd \\\"$SERVER_SKILL\\\" && tar czf - $exc .\"" | tar xzf - -C "$tmp/"
  # 兜底清顶层非源文件
  rm -f "$tmp/manifest.json" "$tmp"/*.docx "$tmp"/copy_*.txt 2>/dev/null || true
  # prune assets:保留 A 策展集(以仓库现有 assets 文件名 = 策展集为准)
  if [ -d "$tmp/assets" ]; then
    ( cd "$tmp/assets" && \
      for f in *; do [ -f "$REPO_SKILL/assets/$f" ] || rm -f -- "$f"; done ) 2>/dev/null || true
  fi
  # 密钥扫描闸
  if grep -rnE 'sk-[A-Za-z0-9]{20,}|cli_a[a-z0-9]{10,}|appSecret.*[:=].*["'"'"'][A-Za-z0-9]{8,}' "$tmp" 2>/dev/null; then
    echo "✗ 检测到疑似密钥,已中断 capture。请人工核查后重试。" >&2
    rm -rf "$tmp"; exit 1
  fi
  # 覆盖仓库 skill 目录(保留 .git 等)
  mkdir -p "$REPO_SKILL"
  ( cd "$tmp" && tar czf - . ) | tar xzf - -C "$REPO_SKILL/"
  rm -rf "$tmp"
  echo "✓ captured,请 git status / diff 复核后 commit"
  cd "$HERE" && git status --short
}

case "${1:-}" in
  to-local)  cmd_to_local ;;
  to-server) cmd_to_server ;;
  out)       cmd_out ;;
  capture)   cmd_capture ;;
  *) echo "usage: $0 {to-local|to-server|out|capture}"; exit 1 ;;
esac
