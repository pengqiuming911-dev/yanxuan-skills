# 飞书原生云文档推介材料模板

默认交付是飞书原生云文档 `/docx/`，不是 Word 附件。最终链接必须形如：

`https://kcngap16uccc.feishu.cn/docx/...`

如果输出 `https://kcngap16uccc.feishu.cn/file/...`，说明误走 Word 附件上传，本次任务不算完成，必须重跑：

```bash
python3 scripts/create_feishu_doc.py --manifest manifest.json --title "产品简称-结构名称"
```

## 归档与命名

1. 文档放入当月文件夹。文件夹命名规则：`某年某月产品`，例如 `2026年7月产品`。若没有当月文件夹，workbench 自动创建。
2. 文档标题命名规则：`销售物料：产品名称简写-结构名称`（`销售物料：` 前缀由 `create_feishu_doc.py` 的 `default_doc_title` 自动加，已带则不重复加；命令人显式传 `--title` 时不叠前缀）。
3. 产品名称简写：去掉尾部 `私募证券投资基金`、`证券投资基金`、`私募基金`、`基金` 等通用后缀。
4. 示例：`泰创纶哲CTA一期私募证券投资基金` -> `泰创纶哲CTA一期`，标题为 `销售物料：泰创纶哲CTA一期-2倍DCN`。

## 12 个标准章节

每个章节标题都是 H2。manifest 里统一使用 `subheading`，不要用一级 `heading`。

1. 产品结构文字版（长版）
2. 产品结构文字版（短版）
3. 产品公告群通知
4. 稳定版接龙通知
5. 产品派息与敲出观察点位表图片
6. 产品胜率数据
7. 一页通
8. 注意事项
9. 管理人-基金业协会公示图
10. 产品-基金业协会公示图
11. 托管募集账户核对
12. 销售常见问题

## 章节内容规则

- 第 1 节：正文为推介文案 + 文末结构要素。标题（🚀 那行）必须放在文案最前面；文末结构要素首行为 `结构：<结构名称>`，随后才是标的/期限/…/费后派息，空一行接打款日截至/入场时间。
- 第 2 节：只贴与第 1 节文末完全相同的结构要素（含首行 `结构：<结构名称>`、打款日截至、入场时间），不写正文分析。
- 第 3 节、第 4 节：正文暂时为空，不要自行生成话术。
- 第 5 节：图片必须来自通毓产品点位页“复制为图片”的原始 PNG。
- 第 6 节：先写一句“回测时间从YYYY年MM月DD日到YYYY年MM月DD，本产品胜率：XX.XX%”，再插入通毓结构化产品回测结果截图。**回测区间=硬性 10 年（开始日=今天−10 年、结束日=今天），用 `tongyu_winrate.py` 实际输出的 `date_range`**（如 2016-07-14至2026-07-14），不要套旧默认 2016-06-26~2026-06-25。短历史标的终端自动 clamp、照实写（可能 < 10 年）。截图先定位结果容器 bounding box；定位不到按整页裁图兜底（去顶导航+底1/3+右1/4）。
- 第 7 节：留 `[图片待补: 一页通]`。
- 第 8 节：固定写三行占位：`申购费：（待补充）`、`赎回费：（待补充）`、`基金合同：（待补充）`。不得省略该节，不得自行编费用数字。
- 第 9 节：先写管理人名称和 AMAC 最终详情页链接，再插入详情页内容容器截图。
- 第 10 节：先写产品名称和 AMAC 最终详情页链接，再插入详情页内容容器截图；从详情页抽取托管人名称供第 11 节使用。
- 第 11 节：只展示 `账户:`、`账号:`、`银行:` 三个字段；补充官方托管核验方式，找不到就写 `[托管户核验方式待补]`。
- 第 12 节：7 个分类每条必须是**真实可点超链接**（飞书 `/docx/` URL，点进去能跳转）。没有 URL 不得用纯标签冒充——拿不到就标 `[链接待补:xxx]` 并提示用户补（见硬规则 15）。

## AMAC 链接硬规则

第 9、10 节必须使用 AMAC 最终详情页，不要使用搜索结果页截图。

- 管理人详情页：`https://www.amac.org.cn/index/qzss/details/?type=1&name=...&code=...`
- 产品详情页：`https://www.amac.org.cn/index/qzss/details/?type=2&code=...&ctype=P`

截图必须先定位详情内容容器，只截元素 bounding box，再 trim/crop 白边；不要截浏览器视口，不要 full page。

## 图片两边对齐（硬规则）

最终云文档里所有图片（第 5、6、9、10 节）必须像手工截图粘贴那样**按正文两边对齐**（满正文内容宽度），不得是缩小居中图。图片显示宽度由 workbench 图片块的 `width` 字段控制：

- 根因：`business-workbench/backend-go` 里 `DocxImageDisplaySize` 早期把宽度 cap 在 600/686，飞书就按 686 显示（小于正文宽度 → 缩小居中）。
- 修法（已实施）：`DocxImageDisplaySize` 返回图片**自然像素宽高**（`cfg.Width/cfg.Height`，不 cap），飞书按正文内容宽度等比 clamp 显示——和手工粘贴一致。已用以前手贴图的销售文档核实：image block 存的是自然宽（2382/3174），clamp 后撑满两边。
- 目检：打开任一已生成文档，图片应与左右正文边平齐、没有两侧留白、不在中间缩小。窄图保持原宽不放大。

## manifest 骨架

> **第 6 节胜率句的日期/胜率是占位符**（`<date_range ...>`、`<winrate ...>`），必须用 `tongyu_winrate.py` 实际输出的 `date_range` 和 `winrate` 替换，**不要照抄骨架、不要套旧默认 `2016-06-26~2026-06-25`（已过期）**。终端默认回测区间随当天滚动——今天是哪天，区间结尾就滚到哪天（2026-07-13 跑出的区间结尾 ≈ 2026-07-12）；脚本会打印 `date_range`，照填即可。胜率截图本身从通毓实时结果页截取，天然是当前时间，无需额外处理。

```json
{
  "product_name": "泰创纶哲CTA一期私募证券投资基金",
  "product_short_name": "泰创纶哲CTA一期",
  "structure_name": "2倍DCN",
  "sections": [
    {"type":"subheading","text":"产品结构文字版（长版）"},
    {"type":"copy_file","path":"copy_long.txt"},
    {"type":"subheading","text":"产品结构文字版（短版）"},
    {"type":"copy_file","path":"copy_short.txt"},
    {"type":"subheading","text":"产品公告群通知"},
    {"type":"body","text":""},
    {"type":"subheading","text":"稳定版接龙通知"},
    {"type":"body","text":""},
    {"type":"subheading","text":"产品派息与敲出观察点位表图片"},
    {"type":"image","path":"assets/product-card.png","caption":"产品派息与敲出观察点位表图片"},
    {"type":"subheading","text":"产品胜率数据"},
    {"type":"body","text":"回测时间从<date_range 起 YYYY年MM月DD日>到<date_range 止 YYYY年MM月DD日>，本产品胜率：<winrate XX.XX>%"},
    {"type":"image","path":"assets/tongyu-winrate.png","caption":"产品胜率数据截图"},
    {"type":"subheading","text":"一页通"},
    {"type":"body","text":"[图片待补: 一页通]"},
    {"type":"subheading","text":"注意事项"},
    {"type":"body","text":"申购费：（待补充）\n赎回费：（待补充）\n基金合同：（待补充）"},
    {"type":"subheading","text":"管理人-基金业协会公示图"},
    {"type":"body","text":"北京泰创投资管理有限公司\nAMAC详情页链接"},
    {"type":"image","path":"assets/amac-manager.png","caption":"管理人基金业协会公示图"},
    {"type":"subheading","text":"产品-基金业协会公示图"},
    {"type":"body","text":"泰创纶哲CTA一期私募证券投资基金\nAMAC详情页链接"},
    {"type":"image","path":"assets/amac-product.png","caption":"产品基金业协会公示图"},
    {"type":"subheading","text":"托管募集账户核对"},
    {"type":"body","text":"账户：\n账号：\n银行：\n\n[托管户核验方式待补]"},
    {"type":"subheading","text":"销售常见问题"},
    {"type":"link_list","items":[]}
  ]
}
```

## 销售常见问题固定链接（第 12 节）

第 12 节用 `link_list` section，items 每条 `{label, url}`：`label` 是中文标题（如「管理人相关常见问题」），`url` 是飞书 `/docx/` 链接。workbench `create-rich-docx` 会逐条转成 `- [label](url)` markdown 再 convert 成独立 block，飞书云文档里展示成 **可点超链接清单**，可见文字是标题、不是裸 URL。

**items 可留空**（manifest 骨架就是 `"items":[]`）：`scripts/create_feishu_doc.py` 内置下列 7 条默认链接作为单一事实源，留空时自动补全。手填 items 时每条必须有真实 `url`，且 `label` 不要写成 URL（label==url 时脚本会改回「链接」兜底，避免可见文字是长链接）。拿不到某条 url 时**不要**塞无 url 的纯标签——直接留空让脚本补默认全 7 条。

7 条默认链接（2026-07-11 确认可点跳转）：

1. 管理人相关常见问题 → https://kcngap16uccc.feishu.cn/docx/QsiEdsgkSohqCPx4OpccoIwAnGf
2. 交易台相关问题 → https://kcngap16uccc.feishu.cn/docx/JVsCdkwtFoNhLNxW7Mbc4wQynrg
3. 托管相关常见问题 → https://kcngap16uccc.feishu.cn/docx/TzWXdKAaeol7kTxs3BNcowqunJh
4. 申购、赎回流程以及常见问题 → https://kcngap16uccc.feishu.cn/docx/TiJ3daOWvocmofx9FgZcNI2lnce
5. 衍生品设计相关问题 → https://kcngap16uccc.feishu.cn/docx/FTmcddqyqobg2UxW2PRcuslFnje
6. 衍选公司相关常见问题 → https://kcngap16uccc.feishu.cn/docx/SWU3dgmHgoi8Pvx4TitccYisnbd
7. 销售沟通常见问题 → https://kcngap16uccc.feishu.cn/docx/GMDodL9xSo2ejExMeOfc7H4unSh

## 验收

- 交付链接是 `/docx/`，不是 `/file/`。
- 章节数量为 **12 个**，顺序完全一致；第 8 节注意事项存在且写了三行占位。
- 第 3、4 节正文为空。
- 第 5、6、9、10 节图片来源和本产品一致，且图片无大块空白。
- 第 9、10 节 AMAC 截图来自最终详情页。
- 第 11 节只展示账户、账号、银行三个字段，并补官方核验方式或待补占位。
- 所有图片在云文档里两边对齐（满正文宽度），不是缩小居中图。
