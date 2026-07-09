# yanxuan-skills 统一管理设计(单 skill 起步)

- 日期: 2026-07-09
- 仓库: https://github.com/pengqiuming911-dev/yanxuan-skills.git(公开)
- 状态: 已批准

## 1. 目标

把 `structured-product-copywriter` skill 做成干净、版本化的公开仓库作为**唯一源**;本地 Claude Code 与服务器 openclaw 都从这里取;需要时能把服务器 live 版本抓回仓库。遵循 YAGNI:只做这一个 skill + 一个 sync 脚本,不建多 skill 框架。

## 2. 仓库布局

```
yanxuan-skills/
├── README.md            # 仓库说明 + 使用方法
├── .gitignore
├── .sync-excludes       # 共用的 rsync 排除规则(capture 与分发共用)
├── sync.sh              # to-local / to-server / out / capture
└── skills/
    └── structured-product-copywriter/
        ├── SKILL.md
        ├── references/   # 仅 *.md
        ├── scripts/      # 仅 *.py
        ├── evals/evals.json
        └── assets/       # 仅 SKILL.md 实际引用的 png(~7 张)
```

`skills/<name>/` 这层为零成本未来扩展,不增加当前复杂度。

## 3. "干净"边界

### 入仓白名单
- `SKILL.md`
- `references/*.md`(剔除所有 `.bak*`、`*.docx` 销售圣经)
- `scripts/*.py`(剔除所有 `.bak*`、`__pycache__/`、`*.pyc`)
- `evals/evals.json`

> **assets 不入仓**(用户最终决策:纯文本 skill,只保证 SKILL.md/references/scripts 为最新;png 运行时在 workdir 现生成)。SKILL.md/references 中对 `assets/*.png` 的引用在仓库内为悬空引用,不影响运行(图在运行期生成)。

### 永不入仓(排除规则,`.sync-excludes` + `.gitignore`)
- `*.bak*`、`*.pyc`、`__pycache__/`
- `workdir/`(运行输出:docx/html/manifest/copy txt/浏览器 profile 缓存)
- 顶层 `copy_*.txt`、`推介材料.docx`、`copy_announce.txt`(运行产出)
- `assets/` 中非引用的 scratch 截图(backtest-*/home-*/after-analyze 等 50+ 张)
- `.openclaw/`(安装元数据)
- 凭证 `tongyu-creds.json`、`workbench-token.json`(本就在 skill 目录外,自然不打包)

### Canonical 源(初始入库基准)
- 内容以服务器 **B 版**(`/root/.openclaw/workspace/skills/structured-product-copywriter`)为准:SKILL.md 22KB、references/scripts 更新更全。
- assets 不入仓(见上)。
- 入库即"基准快照"。之后仓库为准。

## 4. sync.sh 行为

排除规则统一用一份 `.sync-excludes`,capture 与分发共用,保证两边"干净"定义一致。

- `./sync.sh to-local` — 仓库 `skills/structured-product-copywriter/` → 本地 `~/.claude/skills/structured-product-copywriter/`(rsync 源文件层覆盖,不动本地 workdir)。
- `./sync.sh to-server` — 仓库 → 服务器 `/root/.openclaw/workspace/skills/structured-product-copywriter/`(rsync over ssh,保留服务器 workdir/产出物)。
- `./sync.sh out` — to-local + to-server 一起执行。
- `./sync.sh capture` — 反向:服务器 live 版 → 临时目录,套 `.sync-excludes` 剥成干净版,覆盖仓库 `skills/structured-product-copywriter/`,然后 `git status` 给用户看 diff,用户决定是否 commit。

## 5. 安全

- 已确认脚本/文档无硬编码密钥;通毓凭证走 `~/.claude/tongyu-creds.json`、飞书 token 走 `~/.claude/workbench-token.json` 或环境变量,均在 skill 目录外。SKILL.md 明确要求"不要写进技能文件"。公开仓库安全。
- `capture` 前自动 grep 扫 `sk-`、`cli_a`、`appSecret`、`password` 等模式,命中则中断并提示,作为额外防线。

## 6. 验证

- `to-local` 后:本地 Claude Code 重启能看到 skill,功能可用。
- `to-server` 后:openclaw 文件级读取,下次 agent 调用即用新版(无需重启 pm2)。
- push 后:GitHub 上结构干净,无 `.docx/.bak/__pycache__/workdir`。

## 7. 不做(YAGNI)

- 多 skill 注册表/安装框架
- CI 校验流水线
- 版本号/变更日志体系
- 自动双向同步(同步仍由人触发 `sync.sh`)
