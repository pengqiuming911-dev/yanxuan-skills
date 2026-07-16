---
name: structured-product-copywriter
description: 为场外结构化产品(经典雪球/经典锁盈/早利锁盈/早利雪球/DCN/FCN/复合结构(月增)等)生成面向客户的推介文案。当用户给出标的、期限、保证金、敲出线、降敲、降落伞、派息线、费后派息、打款日、入场时间等参数,或提到"雪球""DCN""FCN""锁盈""经典""早利""复合""月增""结构化产品""场外期权""敲出/敲入/降落伞/降敲/派息/票息""末次观察敲出价/期末敲出价/期末障碍价"(均=降落伞)",或要求写"产品文案/推介材料/产品介绍/结构文字版"时,务必使用本技能。即使用户只是甩过来一串参数没说要写文案,也应主动用本技能补全缺失参数并产出长版+短版文案。
---

# 结构化产品推介文案生成

## ⚠️ 复合结构（月增产品）必读——检测到复合必须分DCN+锁盈分别测算

**如果用户参数包含以下任一关键词**：「复合」「月增」「DCN+锁盈」「DCN不观察敲入」「复合DCN」→ **这是复合结构，必须按下方硬规则#11分别测算DCN和锁盈两组，不得合并成一张图/一次胜率。** 跳转到硬规则#11执行。

本技能帮你把一组结构化产品参数,转换成既能讲清结构、又有销售打动力的客户推介文案。核心价值:参数一个不漏、点位换算不出错、卖点组织得有逻辑,而不是平铺直叙地罗列数字。

## 近期踩坑硬规则（必须优先遵守）

1. **默认交付必须是飞书原生云文档 `/docx/`**。返回链接形如 `https://kcngap16uccc.feishu.cn/docx/...` 才算成功。若最终链接是 `https://kcngap16uccc.feishu.cn/file/...`，说明误走了 Word 附件上传，必须判为失败并改跑 `scripts/create_feishu_doc.py --manifest ...`。
2. **不要把 Word 当兜底主交付**。`build_docx.py` 和 `upload_to_feishu.py` 只在用户明确说“要 Word 文件 / .docx 附件 / 下载 Word”时才运行。用户说“推介材料、销售物料、飞书文档、云文档”时，一律走 `create_feishu_doc.py`。
3. **图片必须作为飞书云文档正文图片块插入**，不是把 Word 上传到飞书 Drive。使用 `create_feishu_doc.py --manifest`，它会调用 workbench `/api/drive/create-rich-docx` 并处理图片块。
4. **飞书图片显示空白坑**：飞书 image block 需要按原图比例传 `width` 和 `height`。如果文档里点开图片正常、正文显示底部大片空白，多半是图片块高度没按比例写入；应修 workbench 图片块尺寸，不要改成 Word 附件规避。
5. **INTERNAL_DOCX_TOKEN/INTERNAL_DOCS_TOKEN 坑**：OpenClaw 在生产节点上默认使用 `WORKBENCH_BASE_URL=http://127.0.0.1:3001`，同机调用不需要 internal token。不要因为 token 未配置就回退生成本地 Word。
6. **章节顺序和标题类型不可变**：最终云文档固定 **12 个 H2 章节**，顺序见 `references/docx-template.md`：产品结构文字版（长版）→ 产品结构文字版（短版）→ 产品公告群通知（空）→ 稳定版接龙通知（空）→ 产品派息与敲出观察点位表图片 → 产品胜率数据 → 一页通 → **注意事项** → 管理人-基金业协会公示图 → 产品-基金业协会公示图 → 托管募集账户核对 → 销售常见问题。不要穿插内容，不要漏掉空白的第 3、4 节，不要漏掉第 8 节注意事项。
7. **长版标题必须放在文案最前面**，例如 `【 月月派息·安全垫双重加厚｜中证1000 2倍降敲DCN】`，不要把标题放到段落后面。
8. **AMAC 截图必须进入最终详情页**，不能停在搜索结果页；只截详情内容容器 bounding box，再 trim 白边。
9. **产品点位图必须来自通毓”复制为图片”原始 PNG**。复制失败时显式报错或占位，不要用本地 HTML 重画表格，也不要截浏览器视口。
10. **所有截图都不要按浏览器视口截图**。先定位目标内容容器，只截元素 bounding box，完成后 trim/crop，最终底部距离最后一行内容不超过 20px。
11. **复合结构（月增产品）必须分别测算，不得混合**：当用户参数包含”复合”、”月增”、或一个产品有多个子结构（如”复合DCN｜DCN+锁盈”）时，**必须拆成DCN和锁盈两组参数，分别跑点位图、分别跑胜率、分别生成图片**，不得合并成一张图/一次胜率。

    **检测**：用户参数出现”复合”、”月增”、”DCN+锁盈”、”DCN不观察敲入”、或同时出现DCN的派息线和锁盈的敲出票息→判定为复合结构。

    **拆分规则**（以”复合DCN不观察敲入｜中证1000｜36M锁3｜DCN全保，锁盈2.85倍杠杆不追保｜DCN: 4M起降敲0.5%, 36月降落伞65%, 派息线78%, 月派息0.699%｜锁盈: 4M起降敲0.5%, 36月降落伞65%｜锁盈敲出: 3-18M 3.27%, 19-36M 0.04%”为例）：

    | 参数 | DCN子结构 | 锁盈子结构 |
    |---|---|---|
    | structure | DCN | 早利 |
    | term/lock/ko/step-down/parachute | 36/3/101/0.5/65 | 36/3/101/0.5/65 |
    | margin | 100（全保） | 35（2.85倍杠杆→100/2.85≈35） |
    | dividend-coupon | 0.699（月派息） | 0 |
    | coupon-line/coupon | 78/0.699（DCN用） | 不用 |
    | rate1/rate2/rate1-start/rate2-start | 不用（DCN无分段敲出票息） | 3.27/0.04/3/19（锁盈用） |
    | option-structure | SNOWBALL_FIXED | SNOWBALL_FLOATING |

    **DCN胜率命令**：
    ```bash
    xvfb-run -a python3 scripts/tongyu_winrate.py --structure DCN --term 36 --lock 3 --margin 100 --ko 101 --step-down 0.5 --parachute 65 --coupon-line 78 --coupon 0.699 --dividend-coupon 0.699 --option-structure SNOWBALL_FIXED --rate1 0 --rate2 0 --output assets/tongyu-winrate-DCN.png --headed
    ```

    **锁盈胜率命令**：
    ```bash
    xvfb-run -a python3 scripts/tongyu_winrate.py --structure 早利 --term 36 --lock 3 --margin 35 --ko 101 --step-down 0.5 --parachute 65 --rate1 3.27 --rate2 0.04 --rate1-start 3 --rate2-start 19 --dividend-coupon 0 --option-structure SNOWBALL_FLOATING --output assets/tongyu-winrate-锁盈.png --headed
    ```

    **DCN点位图**：`product_card.py`（DCN用，选DCN类型）
    **锁盈点位图**：`product_card_locky.py`（锁盈用，选锁盈类型）

    **执行顺序（严格按此顺序，不得跳步/合并）**：
    1. 先跑 DCN 点位图：`python3 scripts/product_card.py --underlying <标的> --term 36 --lock 3 --margin 100 --ko 101 --step-down 0.5 --parachute 65 --coupon-line 78 --coupon 0.699 --entry-point <点位> --output assets/product-card-DCN.png`
    2. 再跑 锁盈点位图：`python3 scripts/product_card_locky.py --title “<简称>-锁盈” --term 36 --lock 3 --margin 35 --ko 101 --step-down 0.5 --parachute 68 --parachute-months 36 --rate1-start 3 --rate1-end 18 --rate1 3.27 --rate2-start 19 --rate2-end 36 --rate2 0.04 --entry-point <点位> --output assets/product-card-锁盈.png`
    3. 跑 DCN 胜率：`xvfb-run -a python3 scripts/tongyu_winrate.py --structure DCN --term 36 --lock 3 --margin 100 --ko 101 --step-down 0.5 --parachute 65 --coupon-line 78 --coupon 0.699 --dividend-coupon 0.699 --option-structure SNOWBALL_FIXED --rate1 0 --rate2 0 --output assets/tongyu-winrate-DCN.png --headed` → 从 `WINRATE_RESULT` 取 DCN 胜率
    4. 跑 锁盈胜率：`xvfb-run -a python3 scripts/tongyu_winrate.py --structure 早利 --term 36 --lock 3 --margin 35 --ko 101 --step-down 0.5 --parachute 65 --rate1 3.27 --rate2 0.04 --rate1-start 3 --rate2-start 19 --dividend-coupon 0 --option-structure SNOWBALL_FLOATING --output assets/tongyu-winrate-锁盈.png --headed` → 从 `WINRATE_RESULT` 取 锁盈胜率

    **manifest 第5节**（两张点位图，DCN在前锁盈在后）：
    ```json
    {“type”:”image”,”path”:”assets/product-card-DCN.png”,”caption”:”DCN结构点位表”},
    {“type”:”image”,”path”:”assets/product-card-锁盈.png”,”caption”:”锁盈结构点位表”}
    ```

    **manifest 第6节**（DCN胜率一句话+截图在前，锁盈在后）：
    ```json
    {“type”:”body”,”text”:”DCN结构：回测时间从{start}到{end}，胜率：{DCN胜率}%”},
    {“type”:”image”,”path”:”assets/tongyu-winrate-DCN.png”,”caption”:”DCN胜率数据”},
    {“type”:”body”,”text”:”锁盈结构：回测时间从{start}到{end}，胜率：{锁盈胜率}%”},
    {“type”:”image”,”path”:”assets/tongyu-winrate-锁盈.png”,”caption”:”锁盈胜率数据”}
    ```

    **文案要点**：标题突出”双收益叠加”（如`【 月月派息·敲出高票息双收益｜中证1000 复合DCN+锁盈】`）；正文分别描述DCN的月月派息和锁盈的敲出票息，再加一段”综合收益”=两者相加（如”敲出收益3-18M约11.66%（DCN月派息0.699%×12≈8.39%+锁盈3.27%），19-36M约8.43%”）。
11. **图片必须按正文两边对齐（满正文宽度）展示，不得是缩小居中图**。最终云文档里所有图片（产品卡、胜率、AMAC 管理人/产品）都要像手工截图粘贴那样撑满正文内容宽度、与左右正文边对齐，而不是缩小居中图。图片显示宽度由 workbench 图片块 `width` 控制：**用图片的自然像素宽高**（`DocxImageDisplaySize` 返回 `cfg.Width/cfg.Height`，不 cap），飞书会按正文内容宽度等比 clamp 显示——已用以前手贴图的销售文档核实：那些 image block 存的就是自然宽（2382/3174），飞书 clamp 后撑满两边。早期 cap 600/686 是「缩小居中图」根因，已改。窄于正文宽度的图保持原宽不放大。详见 `references/docx-template.md`「图片两边对齐」。
12. **第 8 节注意事项必须存在且填占位**：正文固定写 `申购费：（待补充）`、`赎回费：（待补充）`、`基金合同：（待补充）` 三行，不要省略该节，也不要自行编费用数字。
13. **第 1 节长版必须严格按 4 段顺序**，不得调换/合并/漏段：① 第一行 `🚀【 <卖点>｜<标的> <倍数> <结构>】` 标题；② 第二行**亮点摘取短句**——用客观数据写一句简短推介，数据密集、末尾带口语收尾（例：`62%深度安全垫，十年回测胜率97.88%，1.4%高票息，稳稳地幸福。`），不要写成五点特征罗列；③ 第三行**推介文案段**——根据结构特点写一段简短文案，简明扼要突出结构优势（当前点位→安全垫对比→降敲→杠杆→定位）；④ 最后**结构要素明细**——参数块（首行 `结构：<结构名称>`，逐行同用户原始参数）。短版只复用第 4 段参数块。
14. **第 6 节胜率：直调 `new-back-test-analysis` API 取真实胜率（不走表单立即分析）**。跑 `tongyu_winrate.py --structure <结构> --term <N> --lock <L> --margin <M> --ko <K> --step-down <S> --parachute <P> --rate1 <R1> --rate2 <R2> --rate1-start <3> --rate2-start <19> --output assets/tongyu-winrate-<标的>.png --headed`——脚本会：①填表单（结构/票息/敲入价=降落伞/期末障碍价=降落伞/日期双选）；②**直调 `new-back-test-analysis` API**（表单立即分析有 umi URL bug：terminal-data-service base undefined→TypeError→回测不触发；直调绕过它）→ 打印 `DIRECT WINRATE response: {"status":200,"resp":{"payLoad":{"winRate":0.9529...}}}`；③从 `winRate` 取胜率（0.9529→95.29%）+ 回测区间（startDate~endDate，硬性10年=今天−10年到今天）；④**生成胜率卡片图**（胜率+已完结合约+未敲入敲出/敲入未敲出/盈利/亏损分布表）到 `--output`。正文第6节写成「回测时间从YYYY年MM月DD日到YYYY年MM月DD日，本产品胜率：XX.XX%」+ 嵌入 `--output` 的胜率卡片图。**必须从 DIRECT WINRATE response 的 winRate 取真实值，不得留 [胜率待补] 占位**。**不得用表单立即分析的截图**（缓存旧值，非本产品参数）。
15. **第 12 节销售常见问题必须用 `link_list` section + `[标题](url)` 清单格式，不得输出裸 URL 长链接**。manifest 里写 `{"type":"link_list","items":[]}`，`items` 可留空——`scripts/create_feishu_doc.py` 内置 7 条默认飞书 `/docx/` 链接（见 `references/docx-template.md`「销售常见问题固定链接」），留空时自动补全成 `- [标题](url)` 清单写入飞书云文档，可见文字是中文标题、不是裸 URL。手填 items 时每条必须是 `{label:中文标题, url:飞书/docx/ URL}`，**label 不要写成 URL**（label==url 时可见文字就是长链接，正是要消灭的坑；脚本会兜底改回「链接」，但 manifest 层面就该写对）。**禁止把 7 条链接塞进 `body` 当裸 URL 文本**——飞书会把裸 URL 当纯文本渲染成长链接；脚本对「FAQ body 含 feishu.cn/docx/ 裸链接」有兜底转 link_list，但 manifest 应直接用 `link_list`。7 个分类：管理人相关/交易台/托管/申购赎回流程/衍生品设计/衍选公司/销售沟通。拿不到某条真实 url 不要塞无 url 纯标签——留空让脚本补默认全 7 条。
16. **飞书 markdown convert 对多段文本会乱序**：实测把多段落文本一次性丢给 `/docx/v1/documents/blocks/convert`，首段（🚀 标题行）会被挪到末尾、段落顺序被打乱。`create_feishu_doc.py` 的 `copy_file` 已按空行拆成多段、每段单独 convert 成单 block 按 section 顺序插入来锁定顺序——所以第 1 节长版 `copy_long.txt` 的 🚀 标题行能稳在首行。**勿把 copy_file 改回整段单 body**，写 copy_long.txt 时保持段落间空行分隔即可。

17. **基础结构类型按结构名映射（5 选 1）+ 单一结构类型恒点 FCN**。胜率回测页基础结构共 5 类：经典结构 / 凤凰结构 / 早利结构 / 蝶变结构 / DCN。结构名含 `DCN`→DCN；含 `经典`（经典雪球/经典锁盈）→经典结构；含 `早利`（早利锁盈/早利雪球）→早利结构；含 `凤凰`→凤凰结构；含 `蝶变`→蝶变结构（凤凰/蝶变罕见，保留规则备用）。**歧义词**（`多倍锁盈`/`全保锁盈` 等无经典/早利关键词）按分段票息推断：前段票息 ≥ 后段 × 2（且后段 > 0）→早利结构；前后一致 / 单一票息无分段 →经典结构；混合段不明显前高后低 →默认经典结构。**"单一结构类型"恒定勾选 FCN**（所有结构都显式点，不靠系统默认）。FCN 不进基础结构检测列表（你从不会只甩"FCN"）。详见 `references/tongyu-winrate.md`「基础结构选择规则」。**产品点位卡页**只有「锁盈/DCN」两选项：含 DCN→DCN，其余→锁盈（早利/经典只影响票息分段填法，不改变类型下拉）。

## 第一步:核对 10 项参数,缺了就问

无论用户给的是哪种结构(经典雪球/经典锁盈/早利锁盈/早利雪球/DCN/FCN等),先逐项核对。**8 项必填**(标的/期限/保证金/期初敲出线/降敲/降落伞/派息线或敲出票息/费后派息或敲出票息),**2 项可选**(打款日截至、入场时间——给了就写进参数块,没给就省略,不要写 `[待补充]` 占位)。把缺的必填项一次性问用户,不要挤牙膏式地问一个等回复再问下一个——客户体验很差。

| # | 字段 | 必填 | 示例 |
|---|------|------|------|
| 1 | 标的 | ✓ | 中证1000 / 沪深300 / 中证500 / 创业板指 / 个股名 |
| 2 | 期限 | ✓ | 36M锁3M(36个月,前3个月锁仓) |
| 3 | 保证金 | ✓ | 50%(不追保) |
| 4 | 期初敲出线 | ✓ | 101% |
| 5 | 降敲 | ✓ | 0.5%(每月) |
| 6 | 降落伞(敲入线) = 末次观察敲出价 = 期末敲出价 = 期末障碍价 | ✓ | 60% |
| 7 | 派息线(DCN) / 敲出票息(雪球/锁盈) | ✓(按结构) | DCN:78% / 早利锁盈:第3-18M 33%；第19-36M 0.75% |
| 8 | 费后派息(DCN) / 敲出票息同#7(雪球) | ✓(按结构) | DCN:1.39%(月票息) / 雪球:#7已含 |
| 9 | 打款日截至 | **可选** | 6月30日(没给就省略) |
| 10 | 入场时间 | **可选** | 7月3号或6号(没给就省略) |

**默认不追保**：所有产品保证金默认按「不追保」处理,参数块写 `保证金：50%（不追保）`。用户明确说追保才改。

**术语同义词(降落伞)**：`末次观察敲出价 = 期末敲出价 = 期末障碍价 = 降落伞(敲入线)`，四者同义，都指敲入障碍线(如 60%)。用户/要素表里出现任何一个，都按降落伞处理、换算绝对点位 = 当前点位 × 该%。长/短版参数块里仍用销售口径 `降落伞：<…>` 一行展示，不重复列同义词。

> ⚠️ 通毓回测表单的「末次观察敲出价」字段：选降敲后出现，表单默认按"首次观察敲出价 − 步长 × 观察间隔数"自动联动成 85，但本产品里末次观察敲出价 = 期末障碍价 = 降落伞(如 60)，三者一致。填表时「期末障碍价」和「末次观察敲出价」都填降落伞值(60)，覆盖默认 85——`scripts/tongyu_winrate.py` 已在期末障碍价后紧接着填末次观察敲出价 = `parachute`。详见 `references/tongyu-winrate.md`。

**字段不适用的处理**:不同结构字段集会略有不同(例如 FCN 没有敲出线、经典/早利(雪球/锁盈)没有 DCN 的派息线/每月票息而用敲出票息)。如果某字段对该结构确实不适用,让用户明确说"不适用",打印参数块时省略该行即可——但核对这一步不能省,要确认是"不适用"而不是"漏写了"。

**为什么要一次问全**:这些参数之间有联动(降敲节奏影响安全垫厚度、降落伞位置决定抗跌能力),零碎提问会让你失去对整体结构的判断,也让客户来回被打断。一次性收齐,你才能写出有整体感的文案。

## 第二步:收齐行情软数据

文案里的分析需要几项时效性数据,这些不能凭记忆编。

- **当前标的点位**(如"中证1000当前8601点左右")——用于换算降落伞、敲出线的绝对点位。**先跑脚本自动取**:
  ```bash
  python scripts/fetch_quote.py <标的>     # 如 中证1000 / 沪深300 / sh000852
  ```
  脚本只依赖标准库,会从腾讯/新浪/东方财富三个源依次兜底取最新价,最后一行打印 `最新点位: <数字>`。脚本要和 SKILL.md 在同一技能目录下运行(即 `cd` 到技能目录或用相对路径 `scripts/fetch_quote.py`)。**取到了就用真实值,不要再用记忆里的旧点位**;脚本失败(网络不通等)才回头问用户要点位——绝不能因为脚本失败就编一个数字。
- **历史参考底部**——用于和降落伞点位做安全垫对比。若标的是中证1000且用户未另给口径,默认采用 `2025年4月关税战底部中证1000收盘5437.45点`;用户给了其他底部/区间则以用户口径为准。其他标的没有默认底部时再一次性询问,不要临时编数字。
- **回测胜率**(如"历史回测胜率95.29%")——这是文案最有冲击力的卖点,必须真实。**自动获取**:跑 `tongyu_winrate.py`(见硬规则14),脚本**直调 `new-back-test-analysis` API**(不走表单立即分析——那个有 umi URL bug:terminal-data-service base undefined→TypeError→回测不触发),打印 `DIRECT WINRATE response: {"status":200,"resp":{"payLoad":{"winRate":0.9529...}}}`——从 `winRate` 取胜率(0.9529→95.29%)+回测区间(startDate~endDate,硬性10年)。脚本同时**生成胜率卡片图**到 `--output`。凭证从 `~/.claude/tongyu-creds.json` 读(持久化 profile 复用登录态)。**不得留 [胜率待补] 占位**——必须从 DIRECT WINRATE response 的 winRate 取真实值填入 manifest 第6节 body + 文案亮点短句。

为什么当前点位和胜率可以自动取、历史底部通常可默认:当前点位是"现价",有公开实时行情,`fetch_quote.py` 能可靠拿到;胜率是回测算出来的,通毓终端能跑(见 `references/tongyu-winrate.md`),但依赖登录态和表单交互,遇滑块验证码时人工拖一下可救回。中证1000的关税战底部 5437.45 是本技能默认口径;其他标的没有默认底部时才询问。

## 第三步:做点位换算与分析

收到当前点位后,做以下机械换算(算术,不要凭感觉):

- **降落伞绝对点位** = 当前点位 × 降落伞%(= 末次观察敲出价/期末敲出价/期末障碍价，同义)。例:8800 × 60% = 5280点 ≈ "5200点左右"。
- **期初敲出绝对点位** = 当前点位 × 期初敲出线%。例:8800 × 101% = 8888点。
- **派息触发绝对点位** = 当前点位 × 派息线%(如适用)。

然后组织卖点判断(这是文案的"分析骨架",不是直接抄进文案的数字):

1. **安全垫厚度**:比较降落伞绝对点位 与 历史参考底部。降落伞点位低于历史底部 → 安全垫厚,这是最强卖点(例:5280 < 5437.45,说明要跌破关税战底才会触发敲入)。降落伞点位高于历史底部 → 卖点弱化,文案要诚实弱化,不要硬吹。
2. **降敲节奏**:每月降敲 0.5% 意味着敲出线逐月下移,敲出概率随时间推移而提高。讲清"越往后越容易敲出"。
3. **杠杆放大**:保证金 50%(不追保)= 2 倍杠杆,且不追保意味着极端行情下不会被强制平仓追加,风险可控。讲清"放大收益空间 + 不追保的安心"。
4. **票息吸引力**:费后月票息 × 权益/期限,换算成"每月稳到手多少"。客户对"每月到手的钱"比"年化"更有感。
5. **市场语境**:结合用户给的市场判断(上涨/震荡/下跌行情),点出该结构在当前行情下的适配性。若用户未给判断,默认使用中性表述"近期反复震荡/震荡行情",不要卡住追问。上涨行情强调"既守住收益又兼顾安全";震荡强调"安全垫保驾护航、兼顾票息"。

**诚实底线**:卖点判断必须基于真实参数和真实行情数据。降落伞点位没低于历史底部就别写"安全垫厚";市场是下跌行情就别写"上涨行情下兼顾安全"。客户买的是结构,不是文案——夸大一次,信任就没了。

## 第四步:产出文案(长版 + 短版)

### 长版结构

```
🚀【 <安全垫/票息卖点>｜<标的> <倍数> <结构类型>】

<亮点摘取短句:用客观数据写一句简短推介,数据密集、末尾口语收尾,如"62%深度安全垫,十年回测胜率97.88%,1.4%高票息,稳稳地幸福。",不要写成五点特征罗列>

<一段正文:当前点位与波动 → 降落伞绝对点位与历史底部对比(安全垫) → 降敲好处 → 杠杆放大与不追保 → 一句定位总结>

结构：<结构名称，如 2倍DCN / 平层DCN / 多倍锁盈 / 经典锁盈 / 早利锁盈>
标的：<标的>
期限：<期限>
保证金：<保证金>
期初敲出线：<期初敲出线>
降敲：<降敲>
降落伞：<降落伞>
派息线：<派息线>
费后派息：<费后派息>

打款日截至：<打款日截至，可选，没给就省略整段>
入场时间：<入场时间，可选，没给就省略整段>
```

> 长版"文末结构要素"必须和用户给的原始参数块逐行一致：`结构` 行在最前（来自 `structure_name`），随后是标的/期限/保证金/期初敲出线/降敲/降落伞/派息线（或敲出票息）/费后派息。打款日截至/入场时间**可选**——用户给了就空一行接在后面，没给就整段省略（不写 `[待补充]` 占位）。不适用的字段整行省略。

### 短版结构

短版只保留参数块 + 打款日/入场时间（与长版文末那段完全相同），不要正文分析，用于客户快速浏览或转发:

```
结构：<结构名称>
标的：<标的>
期限：<期限>
保证金：<保证金>
期初敲出线：<期初敲出线>
降敲：<降敲>
降落伞：<降落伞>
派息线：<派息线>
费后派息：<费后派息>

打款日截至：<打款日截至，可选，没给就省略整段>
入场时间：<入场时间，可选，没给就省略整段>
```

(短版里"不适用"的字段同样省略;打款日/入场时间没给就整段省略。)

### 写作风格要点

- **标题用 emoji + 正向卖点提炼**,不要只写产品名,也不要用"…才有风险/才会…"这种条件句当标题(听着像在劝退)。客户先看卖点再看结构,标题要给客户一个"我能得到什么"的正向钩子。好标题如"收益安全垫双重加厚""降敲加速敲出·月月派息";坏标题如"关税战底之下才有风险"。若安全垫薄(降落伞高于历史底),标题就走票息/降敲路线,别硬蹭安全垫。
- **副标题浓缩 5 个点**:降敲节奏、安全垫、胜率、费后月票息、行情适配。一句话讲完为什么值得看。
- **正文用"先现状、后对比、再结论"**:先给当前点位和波动,再用降落伞 vs 历史底部做对比(最有说服力),最后落一句定位。不要堆术语,客户要听懂。
- **数字配人话**:每个数字后面跟一句"意味着什么"。8800×60%=5280 后面要接"低于关税战底5437.45点,要跌破2025年最恐慌时刻才会敲入"。
- **倍数/杠杆写进标题**,放大收益是客户最直接的兴趣点。但保证金 100%(1 倍)时不要写"2 倍/双倍",如实写无杠杆即可。
- **不追保单独点一句**,这是风险可控的关键信号。

## 参考示例(供对齐风格,不要照抄)

> 🚀【 收益安全垫双重加厚｜中证 1000 2 倍 DCN】
>
> 每月降敲 0.5%,60% 安全垫,历史回测胜率达98.17%,费后月票息 1.39%,当前上涨行情下既兼顾安全性又守住收益
>
> 中证1000当前点位在8800左右,近期波动较大。目前布局2倍DCN,60%的降落伞(5200点左右,低于2025年4月关税战底部收盘价:5437.45点)以及每月0.5%的降敲让您入场更加安心,同时2倍杠杆能放大收益空间,是当下既能抗波动,又能增强收益的非常理想的配置。

注意这个示例里"5200点左右"是 8800×60%=5280 的口语化近似——你在换算时也用这种"约点"表达,精确到十位即可,客户不需要小数。

### 可选:详版/合规版(仅在用户明确要"详版/合规版/尽调版/含风险揭示"时才出)

上面的长版+短版是默认的简短推介体,用于客户快速浏览和销售转发。如果用户要的是面向合规、尽调或机构客户的完整材料,在长版基础上追加以下三块(短版仍保留):

- **情景分析表**:列出敲出/未敲出未敲入/跌破派息线未敲入/击穿降落伞 等情景下的结果,每行注明对应绝对点位(用第三步的换算)。这是让客户看清"什么行情下拿什么钱"。
- **风险揭示**:逐条列出敲入风险、未敲出风险、流动性风险、市场风险,以及"历史回测胜率不代表未来"。结构化产品非保本,这一段不能省,否则推介材料不合规。
- **适合客群**:2-4 条,写清适合什么样的投资者(看好标的中长期、能承受敲入尾部风险、资金可闲置到期等)。

为什么默认不出:简短版是销售日常用的体例,信息密度够、客户看得完;详版信息全但长,只在合规场景才需要。不要每次都强行铺开。

## 第五步:生成材料资源与 manifest(默认自动)

文案产出后默认自动生成材料资源,不需用户再开口要。最终主交付是 **飞书原生云文档 `/docx/`**,不是 Word 文件。Word(.docx) 只作为图片原样保真的备份/附件兜底。

1. **产品结构卡图**:进通毓"产品点位"小工具(`smallTool/index.html#/product-position`),按产品参数填表(DCN 票息用"每月或有派息"填月票息,锁盈才用年化区间),提交→点"📋 复制为图片"→从浏览器剪贴板读原始 `image/png`(分块 base64,别 spread 爆栈),再做近白边缘 trim。不得用本地 HTML 重画表格,也不得用浏览器视口截图替代原图。见 `references/product-position-card.md`。
2. **胜率卡片图**:由 `tongyu_winrate.py` 的 `generate_winrate_png` 自动生成——直调 API 拿到胜率后,注入 HTML 卡片(胜率+已完结合约+敲出/敲入分布表)到页面 DOM,screenshot 保存到 `--output`。**不要用表单立即分析的截图**(缓存旧值,非本产品参数;立即分析有 umi URL bug 触发不了回测)。manifest 第6节 image 直接用 `--output` 路径。
3. **管理人 + 产品公示截图**:进 AMAC(`amac.org.cn`)管理人最终详情页(type=1)和产品最终详情页(type=2),先定位详情内容容器(`.qiyeBox`/`.chanpinBox` 或等价有效内容容器),只截该元素 bounding box,再 trim/crop 白边;不要截搜索结果页,也不要按浏览器视口或整页截图。见 `references/amac-manager.md`。注意 AMAC 字段值是 JS 异步加载,纯 urllib 抓不到,必须用浏览器渲染后取。
4. **写 manifest JSON**:章节结构仍参考 `references/docx-template.md`,用于同时生成飞书云文档正文与可选 Word 备份。manifest 里的 image section 会随 multipart 一起上传到 workbench,上传前会统一转成标准 JPEG,再由后端按 document_id 创建 image block、按 block_id 二次上传并 replace_image 绑定真实 token 后插入云文档正文;缺图时才写 `[图片待补:xxx]` 占位。

标准材料章节顺序必须严格遵守用户物料生成规则,共 **12 个** H2 章节:产品结构文字版（长版）→ 产品结构文字版（短版）→ 产品公告群通知（空）→ 稳定版接龙通知（空）→ 产品派息与敲出观察点位表图片 → 产品胜率数据 → 一页通 → **注意事项** → 管理人-基金业协会公示图 → 产品-基金业协会公示图 → 托管募集账户核对 → 销售常见问题。详见 `references/docx-template.md`。manifest 中章节标题一律用 `subheading`，不要用 `heading`。


## 用户物料生成规则(硬性)

- 飞书归档文件夹命名为 `某年某月产品`；workbench 默认按当前年月查找,找不到自动创建。
- 飞书文档命名为 `销售物料：产品名称简写-结构名称`，不是“标的+结构+日期”。示例: `销售物料：泰创纶哲CTA一期-2倍DCN`（`销售物料：` 前缀由脚本自动加，命令人传 `--title` 时不带前缀也可，脚本推导时统一补前缀）。
- 文档结构固定 **12 节**,每个标题都是 H2；manifest 里统一使用 `subheading`。
- 第 3 节“产品公告群通知”和第 4 节“稳定版接龙通知”正文暂时留空,不要自行生成话术。
- 第 5 节图片必须来自通毓产品点位页“复制为图片”的原始剪贴板 PNG;复制失败要显式报错/占位,不要用自制表格或视口截图兜底。
- 第 6 节先写一句“回测时间从YYYY年MM月DD日到YYYY年MM月DD，本产品胜率：XX.XX%”,再插入 `tongyu_winrate.py --output` 生成的**胜率卡片图**。胜率+回测区间从 `DIRECT WINRATE response` 的 `winRate`+body 的 `startDate`/`endDate` 取（硬性10年=今天−10年到今天）。**不要用表单立即分析的截图**（缓存旧值，非本产品参数）。**不要留 [胜率待补] 占位**。
- 第 12 节销售常见问题：用 `link_list` section（`{"type":"link_list","items":[]}`），items 留空即可——`create_feishu_doc.py` 内置 7 条默认飞书 `/docx/` 链接自动补全成 `- [标题](url)` 清单。**不得把 7 条链接塞进 `body` 当裸 URL 文本**，可见文字必须是中文标题、不是裸 URL（见硬规则 15）。
- 第 7 节一页通留 `[图片待补: 一页通]` 占位,待手工补入。
- 第 8 节注意事项固定写三行占位: `申购费：（待补充）`、`赎回费：（待补充）`、`基金合同：（待补充）`,不得省略该节,不得自行编费用数字。
- 第 9、10 节 AMAC 来源统一用最终详情页:管理人 `details/?type=1...`、产品 `details/?type=2...`。正文先写名称,再写详情页链接/卡片,截图只截 `.qiyeBox`/`.chanpinBox` 等实际内容容器的 bounding box,并 trim 删除底部和四周白边;不要停留在搜索结果页,不要保留整页空白。
- 第 11 节展示 `账户:`、`账号:`、`银行:` 三个字段，**在打款备注下一行直接附上核验链接和截图**（不是写"见飞书FAQ"——必须把链接和图片提取出来放到物料文档里）。核验方式查找流程：
  1. 从第 10 节产品公示里拿到**托管人名称**（如"海通证券""华泰证券"——**必须用实际产品的托管人名称，不要用此处的示例名"华泰证券"**）。
  2. 跑脚本：`python3 scripts/fetch_custody_info.py --manager "<托管人名称>" --output assets/custody-<托管人>.png`（脚本用飞书 Open API 读飞书文档 `TzWXdKAaeol7kTxs3BNcowqunJh` 的 blocks，找到 H4 标题匹配托管人名称，提取其下方"募集户核对地址："的链接 URL + 图片）。
  3. 脚本输出 `CUSTODY_RESULT: found=true manager=华泰证券 link=<URL> image=saved`——从 `link` 取 URL、从 `CUSTODY_IMAGE: saved=<path>` 取图片路径。
  4. **直接把链接 URL + 图片放到 manifest 第11节** body（`账户:... 账号:... 银行:... 募集户核对地址：<链接URL>`）+ image（`CUSTODY_IMAGE` 的路径）。有的托管人只有图片没链接（如华泰证券），就只放图片。
  5. 找不到该托管人（`found=false`）→写 `[托管户核验方式待补]`。
- 第 12 节用 `link_list` section，items 留空即可——`create_feishu_doc.py` 内置 `references/docx-template.md` 里的 7 个销售常见问题飞书链接自动补全成 `- [标题](url)` 清单；不得写裸 URL body、不得写 placeholder。
- **所有图片两边对齐**:第 5、6、9、10 节图片必须按正文两边对齐(满正文宽度)展示,像手工截图粘贴那样,不得是缩小居中图;图片显示宽度由 workbench 图片块 `width` 控制(见硬规则 11)。

## 第六步:创建飞书原生云文档(默认自动,不再询问)

材料资源和 manifest 就绪后,默认创建飞书原生云文档——**这是硬性规则:不再单独问用户"要不要传飞书"**。全流程(文案→截图/manifest→飞书云文档)一条龙跑完,结尾必须优先交付飞书 `/docx/` 链接。**如果输出的是 `/file/` 链接,本次任务未完成,必须重新跑 `create_feishu_doc.py --manifest manifest.json`。**

流程:
1. 推介材料 manifest 已就绪,文本、参数、账户、胜率数据都写入正文;图片 section 对应的本地 PNG 会自动嵌入云文档正文。
2. 跑飞书云文档脚本:
   ```bash
   python scripts/create_feishu_doc.py --manifest manifest.json --title "泰创纶哲CTA一期-2倍DCN"
   # 或直接从文本创建:
   # python scripts/create_feishu_doc.py --content-file copy_long.txt --title "..."
   ```
3. 脚本打印飞书云文档链接 `https://kcngap16uccc.feishu.cn/docx/{token}`。这才是默认交付链接。
4. **可选兜底**:如用户明确需要图片原样嵌入/离线版/附件版,再跑 `python scripts/build_docx.py --manifest manifest.json --output 推介材料.docx` 生成 Word,并用 `python scripts/upload_to_feishu.py --docx 推介材料.docx --title "..."` 上传为 `/file/` 附件。不要把 `/file/` 当默认主交付。

**标题格式**：`销售物料：产品名称简写-结构名称`，如 `销售物料：泰创纶哲CTA一期-2倍DCN`。标题统一带 `销售物料：` 前缀（由 `create_feishu_doc.py` 的 `default_doc_title` 自动加，已带则不重复加；用户显式传 `--title` 时尊重用户输入、不再叠前缀）。产品名称简写通常去掉 `私募证券投资基金/证券投资基金/基金` 等尾部通用后缀；结构名称用销售口径（如 `2倍DCN`、`平层DCN`、`多倍锁盈`、`经典锁盈`、`早利锁盈`）。manifest 顶层应写 `product_name`、`product_short_name`、`structure_name`，脚本会据此推导标题。

**鉴权**：OpenClaw/服务器上默认用 `WORKBENCH_BASE_URL=http://127.0.0.1:3001` 调 workbench,命中同机免 internal token 规则,不应因为未配置 `INTERNAL_DOCX_TOKEN` 而失败。外网调用才需要 `INTERNAL_DOCX_TOKEN`（兼容 `INTERNAL_DOCS_TOKEN`）并以 `X-Internal-Token` 头带；`https://47.103.54.197` 仅作本地/外部兜底。401 故障见 `references/feishu-upload.md`。
## 服务器/openclaw 执行模式(不用 MCP,用 python 脚本)

服务器(无 GUI)或 openclaw 跑本技能时,浏览器操作(胜率/AMAC/产品卡)不用 Playwright MCP,改用 scripts/ 下 python 脚本(exec 调用),稳定且不依赖 LLM 浏览器 agent。openclaw agent(DeepSeek)调 exec 跑脚本,文案 LLM 写,manifest LLM 组装。

- 当前点位:`python3 scripts/fetch_quote.py <标的>`
- 胜率:`xvfb-run -a python3 scripts/tongyu_winrate.py --structure <DCN|经典|早利|凤凰|蝶变> --term <N> --lock <L> --margin <M> --ko <K> --step-down <S> --parachute <P> --rate1 <R1> --rate2 <R2> --rate1-start <3> --rate2-start <19> --output assets/tongyu-winrate-<标的>.png --headed`→ 脚本最后打印 **`WINRATE_RESULT: winrate=95.29% start=2016-07-15 end=2026-07-15 card=assets/tongyu-winrate-中证1000.png`**——**从这行取胜率+日期+卡片图路径**，填入 manifest 第6节 body（`回测时间从{start}到{end}，本产品胜率：{winrate}`）+ image（`card` 路径）。**直调 API 不走表单立即分析**(有 umi URL bug);`--margin`/`--rate1`/`--rate2` 是直调 API body 需要的(保证金%/区间1票息/区间2票息)。**必须跑此脚本并从 WINRATE_RESULT 行取值，不得留 [胜率待补] 占位**
- 产品卡:`python3 scripts/product_card.py --underlying <标的> --term <N> --lock <L> --margin <M> --ko <K> --step-down <S> --parachute <P> --coupon-line <C> --coupon <M> --entry-point <点位> --output assets/product-card-<标的>.png`(入场日期=生成物料当天，不传 `--entry-date` 即默认 `date.today()`；入场点位用 `fetch_quote.py` 当天真实现价)
- AMAC:`python3 scripts/amac_screenshot.py --manager "<管理人>" --product "<产品>" --outdir assets`
- 飞书云文档:`python3 scripts/create_feishu_doc.py --manifest manifest.json --title "<产品简称>-<结构名称>"`(默认主交付,返回 `/docx/`；**脚本自动加"销售物料："前缀**，--title 传不带前缀也行)
- Word附件兜底:`python3 scripts/build_docx.py --manifest manifest.json --output 推介材料.docx && python3 scripts/upload_to_feishu.py --docx 推介材料.docx --title "<产品简称>-<结构名称>"`(仅在用户明确要求 Word/.docx 附件时使用,返回 `/file/`; `/file/` 不能作为默认交付)

详见 references/tongyu-winrate.md「服务器跑通方案:Xvfb 有头」。openclaw 已装本技能(`openclaw skills install`),agent 调 exec 跑上述脚本(实测 fetch_quote 返回 8620.79 ✓)。

## 最后自检

产出前过一遍:
- [ ] 10 项参数齐全(不适用的已确认并省略)
- [ ] 降落伞绝对点位 = 当前点位 × 降落伞%,算对了
- [ ] 期初敲出绝对点位算对了(如果文案用到)
- [ ] 降落伞点位 vs 历史底部的对比方向诚实(低于才吹安全垫)
- [ ] 胜率:跑了 `tongyu_winrate.py` 直调 `new-back-test-analysis` API,从 `DIRECT WINRATE response` 的 `winRate` 取真实值(如0.9529→95.29%);manifest 第6节 body 填真实胜率+回测区间,image 用脚本 `--output` 生成的胜率卡片图;**没留 [胜率待补] 占位**,没编数字
- [ ] 第 5、6 节是当前时间口径:产品卡入场日期=生成物料当天(`--entry-date` 不传即 `date.today()`)、入场点位=`fetch_quote.py` 当天真实现价;第 6 节回测区间=硬性 10 年(`tongyu_winrate.py` 的 `set_backtest_range` 显式设开始日=今天−10 年、结束日=今天,`_warn_if_range_stale` 校验区间≈10 年+结束日=今天,见告警需手动在 picker 改后重跑),正文回测区间用脚本当天实际 `date_range`,没套旧默认 2016-06-26~2026-06-25、没照抄 docx-template 骨架占位;短历史标的终端自动 clamp、照实写
- [ ] 长版 + 短版都给了;长版/短版参数块首行是 `结构：<结构名称>`,文末结构要素与用户原始参数逐行一致
- [ ] 标题是正向卖点、非条件句;保证金 100% 时没误写"2 倍/双倍"
- [ ] 行情判断与用户给的真实行情一致,没自作主张
- [ ] 详版(情景/风险/客群)只在用户要合规版时才追加,没默认铺开
- [ ] 章节数为 **12 节**,顺序正确;第 8 节注意事项写了申购费/赎回费/基金合同三行占位,没漏
- [ ] 第 12 节用 `link_list` section(items 可留空,`create_feishu_doc.py` 自动补 7 条默认链接);飞书云文档里展示成 `- [标题](url)` 可点清单,可见文字是中文标题、不是裸 URL 长链接;没有把 7 条链接塞进 body 当裸 URL 文本
- [ ] 图片资源已默认生成:产品卡图、胜率截图、AMAC 管理人/产品截图都取到了(取不到的留"[图片待补:xxx]"占位,不卡住流程);manifest 写好;默认不把 Word 作为主交付
- [ ] 所有图片在云文档里两边对齐(满正文宽度),不是 600px 居中缩小图;workbench 图片块宽度已按正文内容宽度(默认 686)设定
- [ ] 飞书原生云文档已默认创建:create_feishu_doc.py 跑通返回飞书 `/docx/` 链接(不再询问确认);如果返回 `/file/` 视为失败并重跑;title 用"销售物料：产品名称简写-结构名称"格式(`销售物料：` 前缀由脚本自动加);服务器/OpenClaw 走 127.0.0.1 免 internal token；外网调用才需 INTERNAL_DOCX_TOKEN/INTERNAL_DOCS_TOKEN
