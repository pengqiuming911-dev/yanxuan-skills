# 创建飞书原生云文档

本技能默认把推介材料创建为飞书原生云文档 `/docx/`。Word `.docx` 只作为用户明确要求时的附件，不是默认主交付。

硬性验收：

- 成功链接必须是 `https://kcngap16uccc.feishu.cn/docx/...`
- `https://kcngap16uccc.feishu.cn/file/...` 是 Word 附件链接，默认场景必须判为失败
- 出现 `/file/` 时，重新运行 `scripts/create_feishu_doc.py --manifest manifest.json`

## 默认命令

```bash
WORKBENCH_BASE_URL=http://127.0.0.1:3001 \
python3 scripts/create_feishu_doc.py --manifest manifest.json --title "泰创纶哲CTA一期-2倍DCN"
```

脚本应调用 workbench：

- `/api/drive/create-rich-docx`：manifest + 图片，默认主路径
- `/api/drive/create-docx`：纯文本兜底

不要默认调用：

- `/api/drive/build-docx`
- `/api/drive/upload-docx`
- `scripts/build_docx.py`
- `scripts/upload_to_feishu.py`

这些只在用户明确要求 Word 文件、`.docx` 附件或下载 Word 时使用。

## 图片上传坑

飞书 docx 图片块不能只塞临时图片 token。正确流程：

1. 按 document_id 先上传图片并创建 image block。
2. 拿到真实 block_id。
3. 按 block_id 二次上传同一图片。
4. 用 documentBlock batchUpdate 的 replace_image 绑定真实 token。
5. 写入 `width` 和按原图比例计算的 `height`。

否则飞书前端会显示“图片上传失败”，或正文中图片底部出现大片空白。

如果图片点开正常但正文显示底部空白，不要回退 Word，应检查 image block 的 width/height。

## 鉴权

- OpenClaw/生产节点默认使用 `WORKBENCH_BASE_URL=http://127.0.0.1:3001`，命中同机免 internal token 规则。
- 外网调用才需要 `INTERNAL_DOCX_TOKEN`，兼容 `INTERNAL_DOCS_TOKEN`。
- 不要因为 `INTERNAL_DOCX_TOKEN` 未配置就生成 Word。
- 飞书 user token 持久化在生产服务器 `shared/.feishu-user-token`，refresh token 失效时重新 OAuth 授权。

## 故障排查

- 返回 `/file/`：误用了 Word 附件路径。重跑 `create_feishu_doc.py --manifest`。
- 提示 `INTERNAL_DOCX_TOKEN` 未配置：生产节点应走 `http://127.0.0.1:3001`，不要回退 Word。
- 401 飞书未授权：走 `https://operation.iyanxuan.cn/api/auth/login` 重新授权。
- 图片上传失败：检查是否使用 `/api/drive/create-rich-docx`，并确认图片路径存在。
- 图片底部空白：检查 workbench 图片块 `height` 是否按原图比例写入。
