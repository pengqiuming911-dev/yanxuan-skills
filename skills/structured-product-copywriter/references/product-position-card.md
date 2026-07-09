# 产品点位卡生成流程

“产品派息与敲出观察点位表图片”必须来自通毓终端产品点位页的“复制为图片”功能。

页面：
`https://terminal.tongyu-quant.com/smallTool/index.html#/product-position`

## 硬规则

1. 打开产品点位页。
2. 选择产品类型并填入产品基础要素。
3. 点击提交，等待结果卡生成。
4. 点击页面自带的“复制为图片”按钮。
5. 从浏览器剪贴板读取 `image/png`，保存为产品点位图。
6. 保存后只做近白色 trim/crop，删除边缘空白；不得改变原图表格样式、背景色、红色重点字体。

不能用本地 HTML 重画表格，不能用浏览器视口截图代替，不能静默兜底成自制表格。

若剪贴板里没有 `image/png`，应显式报错或在 manifest 中写 `[图片待补: 产品派息与敲出观察点位表图片]`。

## 填表口径

- DCN 的费后派息填“每月或有派息”，直接填月票息，如 `1.39`。
- 锁盈/经典结构若表单要求“区间年化票息”，填月票息 x 12，如 `16.68`。
- 入场点位用 `fetch_quote.py` 或用户明确给出的真实点位。

## 装进飞书云文档

最终装配用：

```bash
python3 scripts/create_feishu_doc.py --manifest manifest.json --title "产品简称-结构名称"
```

manifest 第 5 节写：

```json
{"type":"subheading","text":"产品派息与敲出观察点位表图片"},
{"type":"image","path":"assets/product-card.png","caption":"产品派息与敲出观察点位表图片"}
```

不要默认使用 `scripts/build_docx.py`，不要返回 `/file/` 链接。

## 验收

最终图片应与通毓复制出的原始 PNG 风格一致，保留清晰背景色和红色重点字体，底部没有表格外大块空白。
