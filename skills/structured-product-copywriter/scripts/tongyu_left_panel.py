#!/usr/bin/env python3
"""Screenshot left panel of Tongyu backtest page, including observation price table."""
import argparse
import json
import time
from pathlib import Path

CREDENTIALS = Path.home() / ".claude" / "tongyu-creds.json"
BASE = "https://terminal.tongyu-quant.com"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--term", type=int, required=True)
    ap.add_argument("--lock", type=int, default=0)
    ap.add_argument("--ko", type=float, required=True)
    ap.add_argument("--step-down", type=float, default=0)
    ap.add_argument("--parachute", type=float, default=0)
    ap.add_argument("--coupon-line", type=float, default=0)
    ap.add_argument("--coupon", type=float, default=0)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    creds = json.loads(CREDENTIALS.read_text(encoding="utf-8"))
    user = creds["username"]
    pwd = creds["password"]

    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            str(Path.home() / ".claude" / "tongyu-profile"),
            headless=False,
            args=["--no-sandbox", "--disable-gpu", "--disable-blink-features=AutomationControlled"],
            viewport={"width": 1400, "height": 1200},
        )
        ctx.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        try:
            page = ctx.new_page()
            page.goto(f"{BASE}/#/login", wait_until="domcontentloaded", timeout=60000)
            time.sleep(3)

            if "/#/login" in page.url:
                username_input = page.locator('input[placeholder*="用户"]')
                if username_input.count() > 0:
                    username_input.click()
                    username_input.press_sequentially(user, delay=40)
                    pwd_input = page.locator('input[placeholder*="密码"]')
                    pwd_input.click()
                    pwd_input.press_sequentially(pwd, delay=40)
                    page.get_by_role("button", name="登录账号").click()
                    time.sleep(5)
                if "/#/login" in page.url:
                    try:
                        page.wait_for_function("() => !location.href.includes('/#/login')", timeout=60000)
                    except:
                        print("Login blocked, aborting")
                        ctx.close()
                        return

            page.goto(f"{BASE}/#/investmentAnalysis/InvestmentAnalysis", wait_until="domcontentloaded", timeout=60000)
            time.sleep(4)
            page.evaluate("""
                () => {
                    document.querySelectorAll('.fast-refer-to-quotation-modal, .ant-modal-mask, .ant-modal-wrap')
                        .forEach(e => e.remove());
                }
            """)
            time.sleep(0.5)

            def click_text(text):
                page.evaluate(
                    """(t) => {
                        const all = Array.from(document.querySelectorAll('*'))
                            .filter(e => (e.textContent || '').trim() === t);
                        all.sort((a, b) => a.querySelectorAll('*').length - b.querySelectorAll('*').length);
                        if (all[0]) all[0].click();
                    }""",
                    text,
                )

            click_text("DCN")
            time.sleep(1)
            click_text("降敲结构")
            time.sleep(0.8)
            click_text("降落伞结构")
            time.sleep(1)
            click_text("有锁定期")
            time.sleep(0.5)
            click_text("不追保")
            time.sleep(0.5)

            def fill_field(label, value):
                result = page.evaluate(
                    """({lbl, val}) => {
                        let el = null;
                        for (const e of Array.from(document.querySelectorAll('div,span,label'))) {
                            if (e.textContent.trim() === lbl) { el = e; break; }
                        }
                        if (!el) return 'NOTFOUND';
                        let c = el, inp = null;
                        for (let i = 0; i < 6; i++) {
                            c = c.parentElement;
                            if (!c) break;
                            inp = c.querySelector('input');
                            if (inp) break;
                        }
                        if (!inp) return 'NOINPUT';
                        Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set.call(inp, String(val));
                        inp.dispatchEvent(new Event('input', {bubbles: true}));
                        inp.dispatchEvent(new Event('change', {bubbles: true}));
                        inp.dispatchEvent(new Event('blur', {bubbles: true}));
                        return 'OK:' + inp.value;
                    }""",
                    {"lbl": label, "val": value},
                )
                print(f"  {label}={value} -> {result}")

            fill_field("期限", args.term)
            fill_field("首次观察敲出价", args.ko)
            fill_field("期末障碍价", args.parachute)
            fill_field("末次观察敲出价", args.parachute)
            fill_field("派息障碍价", args.coupon_line)
            fill_field("敲出价递减步长", args.step_down)
            fill_field("每月或有派息", args.coupon)
            if args.lock != 3 and args.lock > 0:
                fill_field("锁定期", args.lock)
            time.sleep(0.5)

            click_text("立即分析")
            time.sleep(8)

            # Use evaluate to get precise left panel bounding box
            box = page.evaluate("""() => {
                const all = Array.from(document.querySelectorAll('body *')).map(el => {
                    const r = el.getBoundingClientRect();
                    return {el, r, text: (el.innerText || el.textContent || '').trim()};
                }).filter(x => x.r.width > 0 && x.r.height > 0 && x.r.top < 5000);

                // Title bar
                const title = all.find(x =>
                    x.text.startsWith('假设在今天T日') && x.r.left < 300 && x.r.top < 100
                );

                // Observation table (the big one in left panel)
                const table = all.find(x =>
                    x.text.includes('观察次数') &&
                    x.text.includes('敲出') &&
                    x.text.includes('敲入') &&
                    x.r.left < window.innerWidth * 0.45
                );

                // Table rows - find the deepest table element in left panel
                const tables = all.filter(x =>
                    x.el.tagName === 'TABLE' && x.r.left < window.innerWidth * 0.45
                );
                const leftTable = tables.length > 0
                    ? tables.reduce((a, b) => a.r.width > b.r.width ? a : b)
                    : null;

                // Backtest param section title
                const leftTitle = all.find(x =>
                    x.el.tagName === 'HEADER' && x.r.left < 200
                );

                const top = title ? Math.max(0, title.r.top - 15) : 0;
                const bottom = leftTable
                    ? leftTable.r.bottom + 15
                    : (table ? table.r.bottom + 15 : 900);
                const right = leftTable
                    ? Math.min(window.innerWidth * 0.48, leftTable.r.right + 15)
                    : (table ? table.r.right + 15 : 600);

                // Scroll to show the area
                window.scrollTo(0, top);

                return {
                    x: Math.max(0, 0),
                    y: Math.max(0, top),
                    width: Math.min(document.documentElement.scrollWidth, right),
                    height: Math.min(5000, bottom - top)
                };
            }""")

            print(f"Computed box: {box}")

            if box and box.get("width") and box.get("height") and box["width"] > 100 and box["height"] > 100:
                page.screenshot(
                    path=args.output,
                    clip={
                        "x": float(box["x"]),
                        "y": float(box["y"]),
                        "width": float(box["width"]),
                        "height": float(box["height"]),
                    },
                )
                print(f"Left panel screenshot saved: {args.output}")
            else:
                # Fallback crop
                page.screenshot(path=args.output, clip={"x": 0, "y": 0, "width": 600, "height": 900})
                print(f"Fallback screenshot saved: {args.output}")

        finally:
            ctx.close()


if __name__ == "__main__":
    main()
