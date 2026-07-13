#!/usr/bin/env python3
"""Generate product card PNG for 锁盈 (lock-in profit) structure via Tongyu."""
import base64
import argparse
from datetime import date
from pathlib import Path
from PIL import Image, ImageChops

TOOL_URL = "https://terminal.tongyu-quant.com/smallTool/index.html#/product-position"

def trim_near_white(path, pad=20, threshold=246):
    im = Image.open(path).convert("RGB")
    bg = Image.new("RGB", im.size, (255, 255, 255))
    diff = ImageChops.difference(im, bg).convert("L")
    mask = diff.point(lambda p: 255 if p > (255 - threshold) else 0)
    bbox = mask.getbbox()
    if bbox:
        left = max(0, bbox[0] - pad)
        top = max(0, bbox[1] - pad)
        right = min(im.width, bbox[2] + pad)
        bottom = min(im.height, bbox[3] + pad)
        im.crop((left, top, right, bottom)).save(path)
    else:
        im.save(path)

def fill_input(page, index, value):
    loc = page.locator("input").nth(index)
    loc.click()
    loc.press("Control+A")
    loc.fill(str(value))
    loc.dispatch_event("input")
    loc.dispatch_event("change")
    loc.blur()
    page.wait_for_timeout(80)

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
    ap.add_argument("--title", default="")
    ap.add_argument("--term", type=int, required=True)
    ap.add_argument("--lock", type=int, default=0)
    ap.add_argument("--margin", type=float, default=100)
    ap.add_argument("--ko", type=float, required=True)
    ap.add_argument("--step-down", type=float, default=0)
    ap.add_argument("--parachute", type=float, default=0)
    ap.add_argument("--parachute-months", type=int, default=1)
    ap.add_argument("--rate1-start", type=int, default=1)
    ap.add_argument("--rate1-end", type=int, default=12)
    ap.add_argument("--rate1", type=float, default=35)
    ap.add_argument("--rate2-start", type=int, default=13)
    ap.add_argument("--rate2-end", type=int, default=24)
    ap.add_argument("--rate2", type=float, default=1.3)
    ap.add_argument("--entry-date", default="")
    ap.add_argument("--entry-point", type=float, required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    # 入场日期默认取今天（产品卡「入场日期」按当前日期，见 product-position-card.md）。
    entry_date = args.entry_date or date.today().isoformat()

    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu"])
        context = browser.new_context(
            viewport={"width": 1600, "height": 2000},
            permissions=["clipboard-read", "clipboard-write"],
            bypass_csp=True,
        )
        page = context.new_page()
        page.goto(TOOL_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)

        # Select 锁盈
        page.locator("select").select_option(label="锁盈")
        page.wait_for_timeout(500)

        # Check input count
        ic = page.locator("input").count()
        print(f"Input count: {ic}")

        # For 锁盈, inputs are:
        # 0: 产品名称, 1: 期限, 2: 锁定期, 3: 保证金, 4: 敲出线
        # 5: 降敲, 6: 降落伞, 7: 降落伞月份
        # 8: 起始月-区间1, 9: 结束月-区间1, 10: 区间年化票息%
        # 11: 起始月-区间2, 12: 结束月-区间2, 13: 区间年化票息%
        # 14: 入场时间, 15: 入场点位
        values = {
            0: args.title,
            1: args.term,
            2: args.lock,
            3: args.margin,
            4: args.ko,
            5: args.step_down,
            6: args.parachute,
            7: args.parachute_months,
            8: args.rate1_start,
            9: args.rate1_end,
            10: args.rate1,
            11: args.rate2_start,
            12: args.rate2_end,
            13: args.rate2,
            14: entry_date.replace("/", "-"),
            15: args.entry_point,
        }

        for index, value in values.items():
            fill_input(page, index, value)

        # Submit
        page.on("dialog", lambda d: d.accept())
        click_button_by_text(page, "提交")
        page.wait_for_timeout(2000)

        # Verify
        body_text = page.locator("body").inner_text()
        required_checks = [str(args.entry_point), f"{args.margin:g}%", f"{args.ko:g}%"]
        missing = [item for item in required_checks if item not in body_text]
        if missing:
            # Let's debug - dump full body
            print(f"Body text (first 1000): {body_text[:1000]}")
            # Try clicking submit again
            click_button_by_text(page, "提交")
            page.wait_for_timeout(2000)

        # Copy as image
        click_button_by_text(page, "复制为图片")
        page.wait_for_timeout(1500)
        copied = clipboard_png(page)
        browser.close()

    if not copied.get("ok"):
        raise RuntimeError(f"Tongyu copy-as-image failed: {copied}")
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(base64.b64decode(copied["b64"]))
    trim_near_white(out, pad=20)
    print(f"Product card saved: {out} ({copied.get('size')} bytes)")

if __name__ == "__main__":
    main()
