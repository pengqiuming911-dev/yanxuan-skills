#!/usr/bin/env python3
"""Save Tongyu product-position PNG from the page's "copy as image" action.

No browser viewport screenshot is used. The script submits the form, clicks the
page's copy-image button, reads image/png from the clipboard, then trims
near-white borders so the final PNG contains only effective content.
"""
import argparse
import base64
from pathlib import Path

TOOL_URL = "https://terminal.tongyu-quant.com/smallTool/index.html#/product-position"


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


def fill_input(page, index, value):
    loc = page.locator("input").nth(index)
    loc.click()
    loc.press("Control+A")
    loc.fill(str(value))
    loc.dispatch_event("input")
    loc.dispatch_event("change")
    loc.blur()
    page.wait_for_timeout(50)


def clipboard_png(page):
    return page.evaluate(
        """async () => {
          if (!navigator.clipboard || !navigator.clipboard.read) {
            return {ok:false, err:"clipboard read unavailable"};
          }
          const items = await navigator.clipboard.read();
          for (const item of items) {
            for (const type of item.types) {
              if (type === "image/png") {
                const blob = await item.getType(type);
                const ab = await blob.arrayBuffer();
                const bytes = new Uint8Array(ab);
                let binary = "";
                for (let i = 0; i < bytes.length; i += 0x8000) {
                  binary += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
                }
                return {ok:true, b64:btoa(binary), size:bytes.length};
              }
            }
          }
          return {ok:false, err:"image/png not found", types: items.map(x => x.types)};
        }"""
    )


def click_button_by_text(page, text):
    ok = page.evaluate(
        """({text}) => {
          const btn = Array.from(document.querySelectorAll('button')).find(b => (b.innerText || b.textContent || '').includes(text));
          if (!btn) return false;
          btn.click();
          return true;
        }""",
        {"text": text},
    )
    if not ok:
        raise RuntimeError(f"Button not found: {text}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--underlying", required=True)
    ap.add_argument("--term", type=int, required=True)
    ap.add_argument("--lock", type=int, default=0)
    ap.add_argument("--margin", type=float, default=100)
    ap.add_argument("--ko", type=float, required=True)
    ap.add_argument("--step-down", type=float, default=0)
    ap.add_argument("--parachute", type=float, default=0)
    ap.add_argument("--coupon-line", type=float, default=0)
    ap.add_argument("--coupon", type=float, default=0)
    ap.add_argument("--entry-date", default="")
    ap.add_argument("--entry-point", type=float, required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--title", default="")
    args = ap.parse_args()

    leverage = round(100 / args.margin, 1) if args.margin else ""
    product_title = args.title or f"{args.underlying} {leverage}x DCN"
    values = {
        0: product_title,
        1: args.term,
        2: args.lock,
        3: args.margin,
        4: args.ko,
        5: args.step_down,
        6: args.parachute,
        7: args.coupon,
        8: args.coupon_line,
        9: 1,
        10: args.entry_date.replace("/", "-"),
        11: args.entry_point,
    }

    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu"])
        context = browser.new_context(
            viewport={"width": 1600, "height": 1800},
            permissions=["clipboard-read", "clipboard-write"],
            bypass_csp=True,
        )
        page = context.new_page()
        page.goto(TOOL_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)
        page.locator("select").select_option(label="DCN")
        page.wait_for_timeout(500)
        if page.locator("input").count() < 12:
            raise RuntimeError("Unexpected Tongyu product-position form shape")
        for index, value in values.items():
            fill_input(page, index, value)
        page.on("dialog", lambda d: d.accept())
        click_button_by_text(page, "\u63d0\u4ea4")
        page.wait_for_timeout(2000)

        body_text = page.locator("body").inner_text()
        required = [str(args.entry_point), f"{args.margin:g}%", f"{args.ko:g}%", str(args.coupon)]
        missing = [item for item in required if item not in body_text]
        if missing:
            raise RuntimeError(f"Tongyu form submit did not render target values: {missing}")

        click_button_by_text(page, "\u590d\u5236\u4e3a\u56fe\u7247")
        page.wait_for_timeout(1500)
        copied = clipboard_png(page)
        browser.close()

    if not copied.get("ok"):
        raise RuntimeError(f"Tongyu copy-as-image failed: {copied}")
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(base64.b64decode(copied["b64"]))
    trim_near_white(out, pad=20)
    print(f"Tongyu product-position PNG saved: {out} ({copied.get('size')} bytes)")


if __name__ == "__main__":
    main()
