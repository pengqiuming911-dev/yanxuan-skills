#!/usr/bin/env python3
"""创建飞书原生云文档(/docx/)并写入推介材料内容。

默认用于 OpenClaw/生产节点：调用 business-workbench 的 /api/drive/create-docx。
- 生产节点默认 WORKBENCH_BASE_URL=http://127.0.0.1:3001，命中同机免 internal token。
- 本地/外部运行默认 https://47.103.54.197，需 INTERNAL_DOCX_TOKEN（兼容 INTERNAL_DOCS_TOKEN）。

注意：当前 workbench create-docx 接口写入的是 Markdown/文本内容；本脚本会把 manifest
里的图片 section 会随 multipart 一起上传,由 workbench 插入为飞书原生 image block。
Word 上传仅作为附件/兜底。
"""
import argparse
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.request
import uuid
from io import BytesIO
from pathlib import Path


STRUCTURE_SUFFIXES = (
    "私募证券投资基金",
    "私募投资基金",
    "证券投资基金",
    "私募基金",
    "投资基金",
    "基金",
)


# 第 12 节「销售常见问题」的 7 条飞书 /docx/ 链接。label=标题、url=飞书云文档，
# 作为本技能单一事实源：manifest 里 link_list 的 items 留空时自动补全，
# 保证写入飞书云文档的是 `- [标题](url)` 可点清单，而不是裸 URL 长链接。
# （来源 references/docx-template.md「销售常见问题固定链接」，2026-07-11 确认可点跳转。）
DEFAULT_FAQ_LINKS = [
    {"label": "管理人相关常见问题", "url": "https://kcngap16uccc.feishu.cn/docx/QsiEdsgkSohqCPx4OpccoIwAnGf"},
    {"label": "交易台相关问题", "url": "https://kcngap16uccc.feishu.cn/docx/JVsCdkwtFoNhLNxW7Mbc4wQynrg"},
    {"label": "托管相关常见问题", "url": "https://kcngap16uccc.feishu.cn/docx/TzWXdKAaeol7kTxs3BNcowqunJh"},
    {"label": "申购、赎回流程以及常见问题", "url": "https://kcngap16uccc.feishu.cn/docx/TiJ3daOWvocmofx9FgZcNI2lnce"},
    {"label": "衍生品设计相关问题", "url": "https://kcngap16uccc.feishu.cn/docx/FTmcddqyqobg2UxW2PRcuslFnje"},
    {"label": "衍选公司相关常见问题", "url": "https://kcngap16uccc.feishu.cn/docx/SWU3dgmHgoi8Pvx4TitccYisnbd"},
    {"label": "销售沟通常见问题", "url": "https://kcngap16uccc.feishu.cn/docx/GMDodL9xSo2ejExMeOfc7H4unSh"},
]


def faq_link_items(sec):
    """归一 link_list 的 items：留空则补 DEFAULT_FAQ_LINKS；手填的逐条校验 label/url 形状。

    手填 items 时常见错形是把 URL 当 label（`{label:url, url:url}` → 渲染成可见文字是长链接）。
    这里强制：缺 label 用「链接」兜底、label 恰好等于 url 时改回「链接」，保证可见文字是标题而非裸 URL。
    """
    raw_items = sec.get("items") or []
    if not raw_items:
        return [dict(x) for x in DEFAULT_FAQ_LINKS]
    out = []
    for it in raw_items:
        if not isinstance(it, dict):
            continue
        label = (it.get("label") or "").strip()
        url = (it.get("url") or "").strip()
        if not url:
            # 没 url 的条目不算超链接，跳过（不静默塞无链接标签，见硬规则 15）。
            continue
        if not label or label == url:
            label = "链接"
        out.append({"label": label, "url": url})
    return out or [dict(x) for x in DEFAULT_FAQ_LINKS]


def default_base_url():
    if os.environ.get("WORKBENCH_BASE_URL"):
        return os.environ["WORKBENCH_BASE_URL"]
    return "http://127.0.0.1:3001" if os.path.exists("/var/www/business-workbench/current") else "https://47.103.54.197"


def load_token(base_url):
    token = os.environ.get("INTERNAL_DOCX_TOKEN") or os.environ.get("INTERNAL_DOCS_TOKEN")
    if token:
        return token
    creds_path = os.path.expanduser("~/.claude/workbench-token.json")
    if os.path.exists(creds_path):
        try:
            d = json.load(open(creds_path, encoding="utf-8"))
            return d.get("internal_docx_token", "") or d.get("internal_docs_token", "")
        except Exception:
            return ""
    if base_url.startswith("https://"):
        print("警告: 外网调用未取到 INTERNAL_DOCX_TOKEN/INTERNAL_DOCS_TOKEN，可能 401；服务器/OpenClaw 默认走 127.0.0.1 时不需要 internal token。", file=sys.stderr)
    return ""


def read_text_relative(base_dir, rel_path):
    p = Path(rel_path)
    if not p.is_absolute():
        p = base_dir / p
    try:
        return p.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return f"[内容待补: {rel_path}]"


def product_short_name(product_name):
    name = (product_name or "").strip()
    for suffix in STRUCTURE_SUFFIXES:
        if name.endswith(suffix):
            return name[: -len(suffix)].strip()
    return name


DOC_TITLE_PREFIX = "销售物料："


def default_doc_title(manifest):
    explicit_short = (manifest.get("product_short_name") or "").strip()
    product_name = (manifest.get("product_name") or "").strip()
    structure_name = (manifest.get("structure_name") or "").strip()
    short = explicit_short or product_short_name(product_name)
    if short and structure_name:
        base = f"{short}-{structure_name}"
    else:
        base = (manifest.get("title") or "").strip()
    if not base:
        return base
    # 飞书云文档标题统一加「销售物料：」前缀，已带则不重复加。
    if base.startswith(DOC_TITLE_PREFIX):
        return base
    return f"{DOC_TITLE_PREFIX}{base}"


def normalize_section_type(typ):
    typ = (typ or "").strip().lower()
    # Material section titles must be H2 in Feishu. In the workbench rich-docx
    # endpoint, "subheading" maps to Markdown ## while "heading" maps to #.
    if typ == "heading":
        return "subheading"
    return typ


def manifest_to_rich_manifest(manifest_path):
    manifest_file = Path(manifest_path)
    base_dir = manifest_file.parent
    m = json.loads(manifest_file.read_text(encoding="utf-8"))
    sections = []
    image_paths = []
    last_subheading = ""
    for sec in m.get("sections", []):
        typ = normalize_section_type(sec.get("type"))
        if typ == "subheading":
            last_subheading = (sec.get("text") or "").strip()
        if typ == "copy_file":
            # 按空行拆成多段，每段一个 body section。飞书 markdown convert 对一段
            # 多段落文本会乱序（实测首段会被挪到末尾），拆成每段单独 convert 成单 block，
            # 按 section 顺序插入即可锁定段落顺序。copy_long.txt 的 🚀 标题行才能稳在首行。
            content = read_text_relative(base_dir, sec.get("path", ""))
            for para in re.split(r"\n\s*\n", content):
                para = para.strip()
                if para:
                    sections.append({"type": "body", "text": para})
        elif typ == "image":
            path = sec.get("path", "")
            sections.append({"type": "image", "path": path, "caption": sec.get("caption", "")})
            if path:
                image_paths.append(path)
        elif typ == "link_list":
            # items 留空自动补 7 条默认 FAQ 链接；手填的逐条归一成 {label:标题, url}。
            sections.append({"type": "link_list", "items": faq_link_items(sec)})
        elif typ in {"heading", "subheading", "body", "params", "separator"}:
            # 兜底：FAQ 误写成 body 且含裸飞书 /docx/ 长链接时，归一成 link_list 默认清单，
            # 避免飞书把裸 URL 当纯文本渲染成长链接（用户反馈的坑）。
            if typ == "body" and "销售常见问题" in last_subheading and "feishu.cn/docx/" in (sec.get("text") or ""):
                sections.append({"type": "link_list", "items": [dict(x) for x in DEFAULT_FAQ_LINKS]})
                continue
            out = {"type": typ}
            for key in ("text", "caption", "path", "items"):
                if key in sec:
                    out[key] = sec[key]
            sections.append(out)
    rich = {
        "title": default_doc_title(m) or manifest_file.stem,
        "sections": sections,
    }
    if m.get("folder_name"):
        rich["folder_name"] = m.get("folder_name")
    if m.get("folder_token"):
        rich["folder_token"] = m.get("folder_token")
    return rich, image_paths, base_dir


def manifest_to_markdown(manifest_path):
    rich, image_paths, base_dir = manifest_to_rich_manifest(manifest_path)
    parts = []
    image_items = []
    for sec in rich.get("sections", []):
        typ = normalize_section_type(sec.get("type"))
        if typ == "heading":
            parts.append(f"## {sec.get('text', '').strip()}")
        elif typ == "subheading":
            parts.append(f"## {sec.get('text', '').strip()}")
        elif typ in {"body", "params"}:
            parts.append(sec.get("text", "").strip())
        elif typ == "link_list":
            lines = []
            for item in sec.get("items", []):
                label = item.get("label", "链接")
                url = item.get("url", "")
                lines.append(f"- [{label}]({url})" if url else f"- {label}")
            parts.append("\n".join(lines))
        elif typ == "image":
            caption = sec.get("caption") or sec.get("path") or "图片"
            image_items.append(f"- {caption}：`{sec.get('path', '')}`")
        elif typ == "separator":
            parts.append("---")
    if image_items:
        parts.append("## 图片材料\n" + "\n".join(image_items))
    return rich.get("title") or Path(manifest_path).stem, "\n\n".join(p for p in parts if p)

def create_rich_doc(base_url, token, title, rich_manifest, image_paths, base_dir, folder_name=None, folder_token=None):
    url = base_url.rstrip("/") + "/api/drive/create-rich-docx"
    if title:
        rich_manifest["title"] = title
    if folder_name:
        rich_manifest["folder_name"] = folder_name
    if folder_token:
        rich_manifest["folder_token"] = folder_token

    boundary = "----richdoc" + uuid.uuid4().hex
    parts = []

    def add_field(name, value):
        parts.append(b"--" + boundary.encode())
        parts.append(f'Content-Disposition: form-data; name="{name}"'.encode())
        parts.append(b"")
        parts.append(str(value).encode("utf-8"))

    def normalize_image(file_path):
        p = Path(file_path)
        if not p.is_absolute():
            p = base_dir / p
        if not p.exists() or not p.is_file():
            return None, ""
        try:
            from PIL import Image
            im = Image.open(p)
            if im.mode not in ("RGB", "L"):
                im = im.convert("RGB")
            elif im.mode == "L":
                im = im.convert("RGB")
            max_w = 1200
            max_h = 1800
            scale = min(max_w / im.width, max_h / im.height, 1.0)
            if scale < 1.0:
                im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))))
            buf = BytesIO()
            im.save(buf, format="JPEG", quality=90, optimize=True)
            return buf.getvalue(), p.with_suffix(".jpg").name
        except Exception:
            return p.read_bytes(), p.name

    def add_file(field_name, file_path):
        data, filename = normalize_image(file_path)
        if not data:
            return False
        content_type = "image/jpeg" if filename.lower().endswith((".jpg", ".jpeg")) else "image/png"
        parts.append(b"--" + boundary.encode())
        disp = f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"'
        parts.append(disp.encode("utf-8"))
        parts.append(f"Content-Type: {content_type}".encode("utf-8"))
        parts.append(b"")
        parts.append(data)
        return True

    add_field("manifest", json.dumps(rich_manifest, ensure_ascii=False))
    if title:
        add_field("title", title)
    if folder_name:
        add_field("folder_name", folder_name)
    if folder_token:
        add_field("folder_token", folder_token)
    uploaded = 0
    for image_path in image_paths:
        if add_file(image_path, image_path):
            uploaded += 1
    parts.append(b"--" + boundary.encode() + b"--")
    parts.append(b"")
    body = b"\r\n".join(parts)
    headers = {"Content-Type": "multipart/form-data; boundary=" + boundary}
    if token:
        headers["X-Internal-Token"] = token
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    ctx = ssl._create_unverified_context()
    try:
        with urllib.request.urlopen(req, timeout=180, context=ctx) as resp:
            out = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        print(f"创建飞书富文档失败 HTTP {e.code}: {e.read().decode('utf-8', 'replace')}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"创建飞书富文档失败: {e}", file=sys.stderr)
        sys.exit(1)
    try:
        res = json.loads(out)
    except json.JSONDecodeError:
        print(out)
        return
    if "error" in res:
        print(f"创建飞书富文档失败: {res['error']}", file=sys.stderr)
        sys.exit(1)
    print(f"飞书云文档: {res.get('url')}")
    print(f"images_uploaded: {uploaded}")
    for k in ("doc_token", "folder", "folder_token", "blocks_added", "images_added", "missing_images"):
        if res.get(k) not in (None, "", []):
            print(f"{k}: {res.get(k)}")


def create_doc(base_url, token, title, content, folder_name=None, folder_token=None):
    url = base_url.rstrip("/") + "/api/drive/create-docx"
    payload = {"title": title, "content": content}
    if folder_name:
        payload["folder_name"] = folder_name
    if folder_token:
        payload["folder_token"] = folder_token
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-Internal-Token"] = token
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    ctx = ssl._create_unverified_context()
    try:
        with urllib.request.urlopen(req, timeout=120, context=ctx) as resp:
            out = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        print(f"创建飞书云文档失败 HTTP {e.code}: {e.read().decode('utf-8', 'replace')}", file=sys.stderr)
        if e.code == 401:
            print("鉴权失败：服务器/OpenClaw 应默认走 127.0.0.1 免 internal token；外网调用需设置 INTERNAL_DOCX_TOKEN/INTERNAL_DOCS_TOKEN，或重新飞书 OAuth 授权。", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"创建飞书云文档失败: {e}", file=sys.stderr)
        sys.exit(1)
    try:
        res = json.loads(out)
    except json.JSONDecodeError:
        print(out)
        return
    if "error" in res:
        print(f"创建飞书云文档失败: {res['error']}", file=sys.stderr)
        sys.exit(1)
    print(f"飞书云文档: {res.get('url')}")
    for k in ("doc_token", "folder", "folder_token"):
        if res.get(k):
            print(f"{k}: {res.get(k)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", help="manifest JSON 路径；自动转成飞书云文档正文")
    ap.add_argument("--content", help="直接传入正文 Markdown/文本；与 --manifest 二选一")
    ap.add_argument("--content-file", help="从文件读取正文 Markdown/文本；与 --manifest 二选一")
    ap.add_argument("--title", help="飞书云文档标题")
    ap.add_argument("--folder-name", help="目标文件夹名称；不传则由服务端默认归档")
    ap.add_argument("--folder-token", help="目标文件夹 token")
    args = ap.parse_args()
    chosen = [bool(args.manifest), bool(args.content), bool(args.content_file)]
    if sum(chosen) != 1:
        ap.error("需且只能指定 --manifest / --content / --content-file 之一")
    base_url = default_base_url()
    token = load_token(base_url)
    if args.manifest:
        rich_manifest, image_paths, base_dir = manifest_to_rich_manifest(args.manifest)
        title = args.title or rich_manifest.get("title") or Path(args.manifest).stem
        create_rich_doc(base_url, token, title, rich_manifest, image_paths, base_dir, args.folder_name, args.folder_token)
        return
    elif args.content_file:
        content = Path(args.content_file).read_text(encoding="utf-8")
        title = args.title or Path(args.content_file).stem
    else:
        content = args.content
        title = args.title or "推介材料"
    create_doc(base_url, token, title, content, args.folder_name, args.folder_token)


if __name__ == "__main__":
    main()
