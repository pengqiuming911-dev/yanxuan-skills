# 飞书原生云文档推介材料模板

默认交付是飞书原生云文档 `/docx/`，不是 Word 附件。最终链接必须形如：

`https://kcngap16uccc.feishu.cn/docx/...`

如果输出 `https://kcngap16uccc.feishu.cn/file/...`，说明误走 Word 附件上传，本次任务不算完成，必须重跑：

```bash
python3 scripts/create_feishu_doc.py --manifest manifest.json --title "产品简称-结构名称"
```

## 归档与命名

1. 文档放入当月文件夹。文件夹命名规则：`某年某月产品`，例如 `2026年7月产品`。若没有当月文件夹，workbench 自动创建。
2. 文档标题命名规则：`产品名称简写-结构名称`。
3. 产品名称简写：去掉尾部 `私募证券投资基金`、`证券投资基金`、`私募基金`、`基金` 等通用后缀。
4. 示例：`泰创纶哲CTA一期私募证券投资基金` -> `泰创纶哲CTA一期`，标题为 `泰创纶哲CTA一期-2倍DCN`。

## 11 个标准章节

每个章节标题都是 H2。manifest 里统一使用 `subheading`，不要用一级 `heading`。

1. 产品结构文字版（长版）
2. 产品结构文字版（短版）
3. 产品公告群通知
4. 稳定版接龙通知
5. 产品派息与敲出观察点位表图片
6. 产品胜率数据
7. 一页通
8. 管理人-基金业协会公示图
9. 产品-基金业协会公示图
10. 托管募集账户核对
11. 销售常见问题

## 章节内容规则

- 第 1 节：正文为推介文案 + 基础结构。标题必须放在文案最前面。
- 第 2 节：只写基础结构、打款日截至、入场时间，不写正文分析。
- 第 3 节、第 4 节：正文暂时为空，不要自行生成话术。
- 第 5 节：图片必须来自通毓产品点位页“复制为图片”的原始 PNG。
- 第 6 节：先写一句“回测时间从YYYY年MM月DD日到YYYY年MM月DD，本产品胜率：XX.XX%”，再插入通毓结构化产品回测结果截图。
- 第 7 节：留 `[图片待补: 一页通]`。
- 第 8 节：先写管理人名称和 AMAC 最终详情页链接，再插入详情页内容容器截图。
- 第 9 节：先写产品名称和 AMAC 最终详情页链接，再插入详情页内容容器截图；从详情页抽取托管人名称供第 10 节使用。
- 第 10 节：只展示 `账户:`、`账号:`、`银行:` 三个字段；补充官方托管核验方式，找不到就写 `[托管户核验方式待补]`。
- 第 11 节：直接填固定销售常见问题飞书链接，不要写 placeholder。

## AMAC 链接硬规则

第 8、9 节必须使用 AMAC 最终详情页，不要使用搜索结果页截图。

- 管理人详情页：`https://www.amac.org.cn/index/qzss/details/?type=1&name=...&code=...`
- 产品详情页：`https://www.amac.org.cn/index/qzss/details/?type=2&code=...&ctype=P`

截图必须先定位详情内容容器，只截元素 bounding box，再 trim/crop 白边；不要截浏览器视口，不要 full page。

## manifest 骨架

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
    {"type":"body","text":"回测时间从2016年06月26日到2026年06月25，本产品胜率：98.14%"},
    {"type":"image","path":"assets/tongyu-winrate.png","caption":"产品胜率数据截图"},
    {"type":"subheading","text":"一页通"},
    {"type":"body","text":"[图片待补: 一页通]"},
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

## 验收

- 交付链接是 `/docx/`，不是 `/file/`。
- 章节数量为 11 个，顺序完全一致。
- 第 3、4 节正文为空。
- 第 5、6、8、9 节图片来源和本产品一致，且图片无大块空白。
- 第 8、9 节 AMAC 截图来自最终详情页。
- 第 10 节只展示账户、账号、银行三个字段，并补官方核验方式或待补占位。
