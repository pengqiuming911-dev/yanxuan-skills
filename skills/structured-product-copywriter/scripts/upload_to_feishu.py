#!/usr/bin/env python3
"""把推介材料 .docx 上传到飞书云空间「当年当月产品」子文件夹，返回飞书 /file/ 链接。

流程：复用 build_docx.build() 在本地装配 .docx（图片本地可读，已嵌入）→
读二进制 → POST multipart 到 workbench 的 /api/drive/upload-docx 接口 →
服务端 UploadDocx 到当年当月子文件夹（find-or-create，模糊匹配含"某年某月"的既有文件夹）→
返回飞书链接。

为什么走二进制接口而非 build-docx(sections)：build-docx 在服务端装配 .docx，
image path 要服务端可读；而推介材料截图（通毓回测、AMAC 公示、产品卡）在本地由
Playwright 生成，生产服务器读不到。本脚本在本地装配好 .docx（图已嵌入），只把
二进制传给服务端上传，规避"服务端读不到本地图"的约束。

环境变量：
  WORKBENCH_BASE_URL   workbench 后端地址；服务器/OpenClaw 默认 http://127.0.0.1:3001，本地默认 https://47.103.54.197
  INTERNAL_DOCX_TOKEN  接口鉴权 token（外网调用需要；兼容 INTERNAL_DOCS_TOKEN）

用法：
  python scripts/upload_to_feishu.py --manifest manifest.json --title "泰创纶哲CTA一期-2倍DCN"
  python scripts/upload_to_feishu.py --docx 推介材料.docx --title "泰创纶哲CTA一期-2倍DCN"
"""
import argparse
import json
import os
import ssl
import sys
import tempfile
import urllib.error
import urllib.request
import uuid

# 复用同目录 build_docx.py 的装配逻辑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_docx  # noqa: E402


def upload(base_url, token, docx_path, title):
    url = base_url.rstrip("/") + "/api/drive/upload-docx"
    with open(docx_path, "rb") as f:
        data = f.read()

    boundary = "----upload" + uuid.uuid4().hex
    fname = title or os.path.basename(docx_path)
    if not fname.endswith(".docx"):
        fname += ".docx"

    parts = []
    parts.append(b"--" + boundary.encode())
    parts.append(b'Content-Disposition: form-data; name="file"; filename="' + fname.encode() + b'"')
    parts.append(b"Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    parts.append(b"")
    parts.append(data)
    if title:
        parts.append(b"--" + boundary.encode())
        parts.append(b'Content-Disposition: form-data; name="title"')
        parts.append(b"")
        parts.append(title.encode())
    parts.append(b"--" + boundary.encode() + b"--")
    parts.append(b"")
    body = b"\r\n".join(parts)

    headers = {"Content-Type": "multipart/form-data; boundary=" + boundary}
    if token:
        headers["X-Internal-Token"] = token

    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    # 生产用 IP https 访问（域名 jiuyueming.online 解析到别处），证书 CN 是域名、不匹配 IP，故禁用验证
    ctx = ssl._create_unverified_context()
    try:
        with urllib.request.urlopen(req, timeout=120, context=ctx) as resp:
            out = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        print(f"上传失败 HTTP {e.code}: {e.read().decode('utf-8', 'replace')}", file=sys.stderr)
        if e.code == 401:
            print("鉴权失败：外网调用需设置 INTERNAL_DOCX_TOKEN（兼容 INTERNAL_DOCS_TOKEN）；"
                  "服务器/OpenClaw 上应默认走 127.0.0.1 免 internal token。若仍失败，检查飞书 user token 是否需重新 OAuth 授权。", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"上传失败: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        res = json.loads(out)
    except json.JSONDecodeError:
        print(out)
        return
    if "error" in res:
        print(f"上传失败: {res['error']}", file=sys.stderr)
        sys.exit(1)
    print(f"飞书链接: {res.get('url')}")
    print(f"file_token: {res.get('file_token')}")
    print(f"归档文件夹: {res.get('folder')}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", help="manifest JSON 路径（用 build_docx 装配 .docx 后上传）")
    ap.add_argument("--docx", help="已有 .docx 路径；与 --manifest 二选一")
    ap.add_argument("--title", help='飞书文件名（建议格式：标的+结构+日期，如 "泰创纶哲CTA一期-2倍DCN"）')
    args = ap.parse_args()

    if not args.manifest and not args.docx:
        ap.error("需指定 --manifest 或 --docx")

    base_url = os.environ.get("WORKBENCH_BASE_URL")
    if not base_url:
        # OpenClaw 跑在生产节点时走 loopback，命中 workbench 的同机免 internal token 规则。
        base_url = "http://127.0.0.1:3001" if os.path.exists("/var/www/business-workbench/current") else "https://47.103.54.197"

    token = os.environ.get("INTERNAL_DOCX_TOKEN") or os.environ.get("INTERNAL_DOCS_TOKEN")
    if not token:
        # 从本地 creds 文件读（skill 目录外、不打包）。兼容历史 key。
        creds_path = os.path.expanduser("~/.claude/workbench-token.json")
        if os.path.exists(creds_path):
            try:
                d = json.load(open(creds_path, encoding="utf-8"))
                token = d.get("internal_docx_token", "") or d.get("internal_docs_token", "")
            except Exception:
                token = ""
    if not token and base_url.startswith("https://"):
        print("警告: 外网调用未取到 INTERNAL_DOCX_TOKEN/INTERNAL_DOCS_TOKEN，可能 401；"
              "服务器/OpenClaw 默认走 127.0.0.1 时不需要 internal token。", file=sys.stderr)
    if args.docx:
        docx_path = args.docx
    else:
        fd, docx_path = tempfile.mkstemp(suffix=".docx")
        os.close(fd)
        build_docx.build(args.manifest, docx_path)
        print(f"已装配: {docx_path}", file=sys.stderr)

    upload(base_url, token, docx_path, args.title)


if __name__ == "__main__":
    main()
