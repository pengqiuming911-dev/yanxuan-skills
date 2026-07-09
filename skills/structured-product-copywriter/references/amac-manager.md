# AMAC 管理人/产品公示图

管理人、产品公示图必须来自 AMAC 最终详情页，不能停留在全站搜索结果页。

## URL 规则

- 管理人详情页：`https://www.amac.org.cn/index/qzss/details/?type=1&name=<管理人名称>&code=<机构code>`
- 产品详情页：`https://www.amac.org.cn/index/qzss/details/?type=2&code=<产品code>&ctype=P`

泰创示例：

- 管理人：`https://www.amac.org.cn/index/qzss/details/?type=1&name=%E5%8C%97%E4%BA%AC%E6%B3%B0%E5%88%9B%E6%8A%95%E8%B5%84%E7%AE%A1%E7%90%86%E6%9C%89%E9%99%90%E5%85%AC%E5%8F%B8&code=101000008864&`
- 产品：`https://www.amac.org.cn/index/qzss/details/?type=2&code=2105110905109934&ctype=P`

## 截图硬规则

1. 打开最终详情页。
2. 等待 JS 异步数据加载完成。纯 HTTP 抓不到字段值，必须用浏览器渲染。
3. 先定位实际内容容器：
   - 管理人优先截 `.qiyeBox`
   - 产品优先截 `.chanpinBox`
   - 若类名变化，选择包含标题、基础字段、统计/公示信息的最小可见内容容器。
4. 只截该元素的 bounding box。
5. 不要截浏览器视口，不要 full page，不要包含页脚或整页空白。
6. 截图后再做近白色 trim/crop，删除四周和底部空白边缘。
7. 最终图片底部距离最后一行内容不超过 20px。

如果原 PNG 无空白，但飞书正文显示底部空白，这是飞书 image block 宽高比例问题，应修 workbench 图片块尺寸，不要重新按视口截图或回退 Word。

## 执行

```bash
python3 scripts/amac_screenshot.py --manager "北京泰创投资管理有限公司" --product "泰创纶哲CTA一期私募证券投资基金" --outdir assets --manager-code 101000008864 --product-code 2105110905109934 --product-ctype P
```

## 验收

图片只包含 AMAC 详情页实际公示内容，无搜索列表页，无浏览器顶部/底部空白，无详情容器下方大块白区。
