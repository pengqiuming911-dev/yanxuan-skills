# yanxuan-skills

公司共享的 Claude / openclaw agent 技能(skill)物料库。仓库是**唯一源**,本地 Claude Code 和服务器 openclaw 都从这里取。

## 目录结构

```
yanxuan-skills/
├── README.md
├── .gitignore
├── .sync-excludes      # capture 与分发共用的排除规则,保证两边"干净"定义一致
├── sync.sh             # 同步工具:to-local / to-server / out / capture
└── skills/
    └── structured-product-copywriter/   # 场外结构化产品推介文案
        ├── SKILL.md
        ├── references/   # 仅 *.md
        ├── scripts/      # 仅 *.py
        ├── evals/        # evals.json
        └── assets/       # 仅 SKILL.md 引用的 png
```

## 当前 skill

| skill | 说明 |
|------|------|
| `structured-product-copywriter` | 为雪球/降敲雪球/DCN/FCN/限亏雪球等场外结构化产品生成面向客户的推介文案(长版+短版),含取点位、跑胜率、生成产品卡、出 docx、传飞书。 |

## 使用方法

### 装到本地 Claude Code

```bash
./sync.sh to-local     # 仓库 skills/<name>/ -> ~/.claude/skills/<name>/
```

部署后重启 Claude Code 即可在该会话使用对应 skill。

### 部署到服务器 openclaw

```bash
./sync.sh to-server    # 仓库 -> /root/.openclaw/workspace/skills/<name>/
```

openclaw 文件级读取,下次 agent 调用即用新版,无需重启 pm2。

### 一次分发两边

```bash
./sync.sh out          # = to-local + to-server
```

### 从服务器抓回最新改动

openclaw 在服务器上会持续迭代。需要时把 live 版本抓回仓库:

```bash
./sync.sh capture      # 服务器 live -> 仓库(自动剥 bak/pycache/workdir/产出物/scratch 截图)
# 然后 git status / diff 复核,确认后 git commit
```

capture 会自动套 `.sync-excludes` 剥垃圾,并跑一道密钥扫描,命中则中断。

## 安全与"干净"边界

**仓库公开,以下绝不入库**:

- 凭证:`tongyu-creds.json`、`workbench-token.json`(本就在 skill 目录外,通毓凭证走 `~/.claude/tongyu-creds.json`、飞书 token 走 `~/.claude/workbench-token.json` 或环境变量)
- 备份:`*.bak*`
- Python 缓存:`__pycache__/`、`*.pyc`
- 运行产出:`workdir/`、`*.docx`、顶层 `copy_*.txt`
- 安装元数据:`.openclaw/`
- scratch 截图:assets/ 中非 SKILL.md 引用的 png

scripts 与文档里**不硬编码密钥**,SKILL.md 明确要求"不要写进技能文件"。`capture` 前自动 grep 扫 `sk-`/`cli_a`/`appSecret` 等模式作为额外防线。

## 设计文档

- 设计:[docs/specs/2026-07-09-yanxuan-skills-unified-management-design.md](docs/specs/2026-07-09-yanxuan-skills-unified-management-design.md)
- 实现计划:[docs/superpowers/plans/2026-07-09-yanxuan-skills-sync.md](docs/superpowers/plans/2026-07-09-yanxuan-skills-sync.md)
