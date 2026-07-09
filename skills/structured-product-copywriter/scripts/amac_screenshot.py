#!/usr/bin/env python3
"""Capture AMAC final detail screenshots following the sales-material templates."""
import argparse
import os
from pathlib import Path
from urllib.parse import quote

DETAIL_ROOT = "https://www.amac.org.cn/index/qzss/details/"
SEARCH_ROOT = "https://www.amac.org.cn/index/qzss/?key="

KNOWN_MANAGER_CODES = {
    "\u5317\u4eac\u6cf0\u521b\u6295\u8d44\u7ba1\u7406\u6709\u9650\u516c\u53f8": "101000008864",
}
KNOWN_PRODUCT_CODES = {
    "\u6cf0\u521b\u7eb6\u54f2CTA\u4e00\u671f\u79c1\u52df\u8bc1\u5238\u6295\u8d44\u57fa\u91d1": "2105110905109934",
}


def detail_url(kind, name="", code="", ctype="P"):
    if kind == "manager":
        return f"{DETAIL_ROOT}?type=1&name={quote(name.strip())}&code={quote(code.strip())}&"
    return f"{DETAIL_ROOT}?type=2&code={quote(code.strip())}&ctype={quote(ctype.strip() or 'P')}"


def resolve_detail_url(page, name, kind, explicit_code="", ctype="P"):
    if explicit_code:
        return detail_url(kind, name=name, code=explicit_code, ctype=ctype)
    code = KNOWN_MANAGER_CODES.get(name) if kind == "manager" else KNOWN_PRODUCT_CODES.get(name)
    if code:
        return detail_url(kind, name=name, code=code, ctype=ctype)

    page.goto(SEARCH_ROOT + quote(name.strip()), wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(5000)
    want_type = "type=1" if kind == "manager" else "type=2"
    href = page.evaluate(
        """({wantType}) => {
          const links = Array.from(document.querySelectorAll('a[href]'));
          const hit = links.find(a => {
            const h = a.href || a.getAttribute('href') || '';
            return h.includes('/index/qzss/details/') && h.includes(wantType);
          });
          return hit ? hit.href : '';
        }""",
        {"wantType": want_type},
    )
    if not href:
        raise RuntimeError(f"AMAC detail link not found for {name}")
    return href


def trim_near_white(path, pad=20, threshold=246):
    from PIL import Image, ImageChops

    im = Image.open(path).convert("RGB")
    bg = Image.new("RGB", im.size, (255, 255, 255))
    diff = ImageChops.difference(im, bg).convert("L")
    mask = diff.point(lambda p: 255 if p > (255 - threshold) else 0)
    bbox = mask.getbbox()
    if not bbox:
        im.save(path)
        return
    left = max(0, bbox[0] - pad)
    top = max(0, bbox[1] - pad)
    right = min(im.width, bbox[2] + pad)
    bottom = min(im.height, bbox[3] + pad)
    im.crop((left, top, right, bottom)).save(path)


def content_box(page, kind):
    return page.evaluate(
        """({kind}) => {
          const vw = Math.min(1280, document.documentElement.scrollWidth || window.innerWidth);
          const nodes = Array.from(document.querySelectorAll('body *')).map(el => {
            const r = el.getBoundingClientRect();
            const text = (el.innerText || el.textContent || '').trim();
            return {el, r, text};
          });

          if (kind === 'manager') {
            const card = document.querySelector('.qiyeBox');
            const statsText = '\\u6b63\\u5728\\u8fd0\\u4f5c';
            const stats = nodes
              .filter(x => x.text.includes(statsText) && x.r.width > 800)
              .sort((a, b) => (a.r.width * a.r.height) - (b.r.width * b.r.height))[0];
            if (card) {
              const cr = card.getBoundingClientRect();
              const bottom = (stats ? stats.r.bottom : cr.bottom) + 65;
              const y = Math.max(0, cr.top - 35);
              return {
                x: 0,
                y,
                width: vw,
                height: Math.max(1, bottom - y + 8)
              };
            }
          }

          if (kind === 'product') {
            const back = nodes
              .filter(x => x.text.includes('\\u8fd4\\u56de\\u4e0a\\u4e00\\u9875'))
              .sort((a, b) => (a.r.width * a.r.height) - (b.r.width * b.r.height))[0];
            const bottom = back ? back.r.bottom + 8 : Math.min(document.documentElement.scrollHeight, 700);
            return {
              x: 0,
              y: 0,
              width: vw,
              height: Math.max(1, bottom)
            };
          }

          const badTexts = [
            '\\u8fd4\\u56de\\u4e0a\\u4e00\\u9875',
            '\\u6cd5\\u5f8b\\u58f0\\u660e',
            '\\u8054\\u7cfb\\u6211\\u4eec',
            '\\u5ec9\\u653f\\u4e3e\\u62a5',
            'IPV6'
          ];
          const backTop = nodes
            .filter(x => x.text.includes('\\u8fd4\\u56de\\u4e0a\\u4e00\\u9875'))
            .map(x => x.r.top)
            .sort((a, b) => a - b)[0] || Number.POSITIVE_INFINITY;
          const useful = nodes.filter(x => {
            if (!x.text || x.r.width <= 0 || x.r.height <= 0) return false;
            if (x.r.top < 200 || x.r.top >= backTop) return false;
            if (badTexts.some(k => x.text.includes(k))) return false;
            if (x.r.height > 140 || x.r.width > 1350) return false;
            if (x.r.left < 40 && x.r.width > 1450) return false;
            return x.el.children.length === 0 || x.r.height <= 90;
          });
          if (!useful.length) {
            const r = document.body.getBoundingClientRect();
            return {x:0, y:200, width:Math.min(window.innerWidth, r.width), height:600};
          }
          let left = Math.min(...useful.map(x => x.r.left));
          let top = Math.min(...useful.map(x => x.r.top));
          let right = Math.max(...useful.map(x => x.r.right));
          let bottom = Math.max(...useful.map(x => x.r.bottom));
          left = Math.max(0, left - 20);
          top = Math.max(0, top - 20);
          right = Math.min(document.documentElement.scrollWidth, right + 20);
          bottom = Math.min(document.documentElement.scrollHeight, bottom + 20);
          return {
            x: left,
            y: top,
            width: Math.max(1, right - left),
            height: Math.max(1, bottom - top)
          };
        }""",
        {"kind": kind},
    )


def capture_detail(page, name, kind, out_png, explicit_code="", ctype="P"):
    url = resolve_detail_url(page, name, kind, explicit_code=explicit_code, ctype=ctype)
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(5000)
    page.evaluate("() => window.scrollTo(0, 0)")
    page.wait_for_timeout(500)

    box = content_box(page, kind)
    page.screenshot(
        path=out_png,
        full_page=True,
        clip={
            "x": float(box["x"]),
            "y": float(box["y"]),
            "width": float(box["width"]),
            "height": float(box["height"]),
        },
    )
    # The AMAC templates intentionally keep the page/content margins visible.

    label = "manager" if kind == "manager" else "product"
    print(f"[{label}] {name}")
    print(f"source_url={url}")
    print(f"screenshot={out_png}")
    print(f"box={box}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manager", required=True)
    ap.add_argument("--product", required=True)
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--manager-code", default="")
    ap.add_argument("--product-code", default="")
    ap.add_argument("--product-ctype", default="P")
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu"])
        page = browser.new_page(viewport={"width": 1280, "height": 1200}, device_scale_factor=1)
        capture_detail(page, args.manager, "manager", os.path.join(args.outdir, "amac-manager.png"), args.manager_code)
        capture_detail(
            page,
            args.product,
            "product",
            os.path.join(args.outdir, "amac-product.png"),
            args.product_code,
            args.product_ctype,
        )
        browser.close()


if __name__ == "__main__":
    main()
