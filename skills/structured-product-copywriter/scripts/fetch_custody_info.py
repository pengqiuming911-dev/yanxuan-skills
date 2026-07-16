#!/usr/bin/env python3
"""从飞书托管FAQ文档提取指定托管人的募集户核对地址（链接+图片）。

用飞书 Open API 读文档 blocks（不用浏览器，不需要登录）。
文档结构：H4(heading4→托管人名) → text("募集户核对地址："+URL) → image(type=27)

用法: python3 fetch_custody_info.py --manager "华泰证券" --output assets/custody-华泰证券.png
输出: CUSTODY_RESULT: found=true link=<URL> image=<path>
"""
import argparse
import json
import os
import urllib.request
import urllib.error

CUSTODY_DOC_URL = "https://kcngap16uccc.feishu.cn/docx/TzWXdKAaeol7kTxs3BNcowqunJh"
DOC_ID = "TzWXdKAaeol7kTxs3BNcowqunJh"


def get_app_token():
    """从 workbench .env 读飞书 app 凭证，获取 app_access_token。"""
    env_path = "/var/www/business-workbench/shared/.env"
    app_id = os.environ.get("FEISHU_APP_ID", "")
    app_secret = os.environ.get("FEISHU_APP_SECRET", "")
    if not app_id and os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("FEISHU_APP_ID="):
                    app_id = line.split("=", 1)[1].strip().strip('"')
                elif line.startswith("FEISHU_APP_SECRET="):
                    app_secret = line.split("=", 1)[1].strip().strip('"')
    if not app_id or not app_secret:
        return None
    data = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode()
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/auth/v3/app_access_token/internal",
        data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
    return result.get("app_access_token", "")


def read_doc_blocks(token):
    """读文档所有 blocks。"""
    url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{DOC_ID}/blocks?page_size=500"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read()).get("data", {}).get("items", [])


def get_block_text(block):
    """提取 block 的文字内容（支持 text + heading1-9）。"""
    bt = block.get("block_type", 0)
    # text block
    if bt == 2:
        els = block.get("text", {}).get("elements", [])
    # heading blocks (3=h1,4=h2,5=h3,6=h4,7=h5,8=h6,9=h7)
    elif bt in (3, 4, 5, 6, 7, 8, 9):
        key = f"heading{bt - 2}"  # 3→heading1, 4→heading2, ..., 6→heading4
        els = block.get(key, {}).get("elements", [])
    else:
        return ""
    return "".join(e.get("text_run", {}).get("content", "") for e in els)


def extract_links(block):
    """提取 block 里的链接 URL。"""
    els = block.get("text", {}).get("elements", [])
    links = []
    for e in els:
        style = e.get("text_run", {}).get("text_element_style", {})
        link = style.get("link", {}).get("url", "")
        if link:
            links.append(link)
    return links


def download_image(token, block, output):
    """下载 type=27(image) block 的图片。"""
    bt = block.get("block_type", 0)
    if bt != 27:
        return False
    # image block 结构: { "image": { "token": "xxx", "width": ..., "height": ... } }
    img_token = block.get("image", {}).get("token", "")
    if not img_token:
        # 有些 image 块结构不同
        img_token = block.get("block_id", "")
    if not img_token:
        return False
    # 飞书 media 下载 API
    url = f"https://open.feishu.cn/open-apis/drive/v1/medias/{img_token}/download"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
            if len(data) > 100:  # 有效图片
                with open(output, "wb") as f:
                    f.write(data)
                return True
    except Exception:
        pass
    # 尝试 block_id 作为 token
    bid = block.get("block_id", "")
    url2 = f"https://open.feishu.cn/open-apis/drive/v1/medias/{bid}/download"
    req2 = urllib.request.Request(url2, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req2, timeout=30) as resp:
            data = resp.read()
            if len(data) > 100:
                with open(output, "wb") as f:
                    f.write(data)
                return True
    except Exception:
        pass
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manager", required=True, help="托管人名称(如 华泰证券)")
    ap.add_argument("--output", default="assets/custody-info.png")
    args = ap.parse_args()

    token = get_app_token()
    if not token:
        print("CUSTODY_RESULT: found=false error=no_app_token")
        return

    blocks = read_doc_blocks(token)
    if not blocks:
        print("CUSTODY_RESULT: found=false error=no_blocks")
        return

    # 找 H4(block_type=6) 文字含托管人名(支持模糊匹配)
    manager = args.manager.strip()
    # 去掉常见后缀，提取核心名(如"海通证券"→"海通"，"华泰证券股份有限公司"→"华泰")
    import re as _re
    manager_core = _re.sub(r'(证券|股份有限公司|股份公司|有限公司|公司)$', '', manager)
    h_idx = -1
    for i, b in enumerate(blocks):
        if b.get("block_type") == 6:
            txt = get_block_text(b).strip()
            # 精确匹配 或 核心名匹配(如"海通"匹配"国泰海通")
            if manager in txt or manager_core in txt or txt in manager:
                h_idx = i
                break

    if h_idx < 0:
        # 也搜其他 heading 类型
        for i, b in enumerate(blocks):
            if b.get("block_type") in (3, 4, 5, 6, 7, 8, 9):
                txt = get_block_text(b).strip()
                if (manager in txt or manager_core in txt or txt in manager) and len(txt) < 30:
                    h_idx = i
                    break

    if h_idx < 0:
        print(f"CUSTODY_RESULT: found=false error=heading_not_found manager={manager}")
        return

    # 从 H4 往后找"募集户核对"文字 + 链接 + 图片(到下一个 heading 为止)
    link_url = ""
    image_block_idx = -1
    for i in range(h_idx + 1, min(h_idx + 20, len(blocks))):
        bt = blocks[i].get("block_type", 0)
        # 到下一个 heading 就停
        if bt in (3, 4, 5, 6, 7, 8, 9) and i > h_idx + 1:
            break
        txt = get_block_text(blocks[i])
        # 链接(从 text_run style 或纯文本 URL 提取)
        if not link_url:
            links = extract_links(blocks[i])
            if links:
                link_url = links[0]
        # 纯文本里的 URL
        if not link_url and "http" in txt:
            import re
            m = re.search(r'(https?://[^\s<>"\']{10,})', txt)
            if m:
                link_url = m.group(1)
        # 图片块(type=27)
        if bt == 27 and image_block_idx < 0:
            image_block_idx = i

    # 下载图片
    image_saved = False
    if image_block_idx >= 0:
        image_saved = download_image(token, blocks[image_block_idx], args.output)

    print(f"CUSTODY_RESULT: found=true manager={manager} link={link_url} image={'saved' if image_saved else 'none'}")
    if image_saved:
        print(f"CUSTODY_IMAGE: saved={args.output}")


if __name__ == "__main__":
    main()
