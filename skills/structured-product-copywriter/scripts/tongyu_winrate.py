#!/usr/bin/env python3
"""Tongyu structured-product backtest automation."""
import argparse
import json
from pathlib import Path

CREDENTIALS = Path.home() / ".claude" / "tongyu-creds.json"
PROFILE_DIR = str(Path.home() / ".claude" / "tongyu-profile")
BASE = "https://terminal.tongyu-quant.com"


def zh(s):
    return s.encode("ascii").decode("unicode_escape")


TEXT = {
    "username": zh(r"\u7528\u6237\u540d"),
    "password": zh(r"\u5bc6\u7801"),
    "login": zh(r"\u767b\u5f55\u8d26\u53f7"),
    "investment": zh(r"\u6295\u8d44\u5206\u6790"),
    "step_down": zh(r"\u964d\u6572\u7ed3\u6784"),
    "parachute": zh(r"\u964d\u843d\u4f1e\u7ed3\u6784"),
    "locked": zh(r"\u6709\u9501\u5b9a\u671f"),
    "no_margin_call": zh(r"\u4e0d\u8ffd\u4fdd"),
    "term": zh(r"\u671f\u9650"),
    "first_ko": zh(r"\u9996\u6b21\u89c2\u5bdf\u6572\u51fa\u4ef7"),
    "terminal_barrier": zh(r"\u671f\u672b\u969c\u788d\u4ef7"),
    "coupon_barrier": zh(r"\u6d3e\u606f\u969c\u788d\u4ef7"),
    "ko_step": zh(r"\u6572\u51fa\u4ef7\u9012\u51cf\u6b65\u957f"),
    "coupon": zh(r"\u6bcf\u6708\u6216\u6709\u6d3e\u606f"),
    "lock": zh(r"\u9501\u5b9a\u671f"),
    "analyze": zh(r"\u7acb\u5373\u5206\u6790"),
    "date_range": zh(r"\u56de\u6d4b\u533a\u95f4"),
    "winrate": zh(r"\u80dc\u7387"),
}


def load_creds():
    if CREDENTIALS.exists():
        data = json.loads(CREDENTIALS.read_text(encoding="utf-8"))
        return data.get("username", ""), data.get("password", "")
    return "", ""


def set_by_label(page, label, value):
    result = page.evaluate(
        """({lbl, val}) => {
          let el = null;
          for (const e of Array.from(document.querySelectorAll('div,span,label'))) {
            if (e.textContent.trim() === lbl) { el = e; break; }
          }
          if (!el) return 'NOTFOUND';
          let c = el;
          let inp = null;
          for (let i = 0; i < 6; i++) {
            c = c.parentElement;
            if (!c) break;
            inp = c.querySelector('input');
            if (inp) break;
          }
          if (!inp) return 'NOINPUT';
          const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
          setter.call(inp, String(val));
          inp.dispatchEvent(new Event('input', {bubbles:true}));
          inp.dispatchEvent(new Event('change', {bubbles:true}));
          inp.dispatchEvent(new Event('blur', {bubbles:true}));
          return inp.value;
        }""",
        {"lbl": label, "val": value},
    )
    return f"{label}: {result}"


def click_exact_text(page, text):
    page.evaluate(
        """(t) => {
          const all = Array.from(document.querySelectorAll('*'))
            .filter(e => (e.textContent || '').trim() === t);
          all.sort((a, b) => a.querySelectorAll('*').length - b.querySelectorAll('*').length);
          if (all[0]) all[0].click();
        }""",
        text,
    )


def result_screenshot_box(page):
    return page.evaluate(
        """() => {
          const nodes = Array.from(document.querySelectorAll('body *')).map(el => {
            const r = el.getBoundingClientRect();
            const text = (el.innerText || el.textContent || '').trim();
            return {el, r, text};
          }).filter(x => x.r.width > 0 && x.r.height > 0);
          const result = nodes.find(x =>
            x.text.includes('\\u80dc\\u7387') &&
            x.text.includes('\\u5df2\\u5b8c\\u7ed3\\u5408\\u7ea6') &&
            x.text.includes('\\u5e73\\u5747\\u6572\\u51fa\\u65f6\\u95f4') &&
            x.r.left > window.innerWidth * 0.42
          );
          const leftInputs = nodes.filter(x =>
            x.r.left < window.innerWidth * 0.45 &&
            x.r.top > 0 &&
            x.r.bottom < Math.max(result ? result.r.bottom + 160 : 700, 650) &&
            (x.text.includes('\\u671f\\u672b\\u969c\\u788d\\u4ef7') ||
             x.text.includes('\\u56de\\u6d4b\\u533a\\u95f4') ||
             x.text.includes('\\u7acb\\u5373\\u5206\\u6790') ||
             x.text.includes('\\u5f00\\u4ed3\\u6761\\u4ef6') ||
             x.text.includes('\\u6bcf\\u6708\\u6216\\u6709\\u6d3e\\u606f'))
          );
          if (!result || !leftInputs.length) return null;
          const all = [result, ...leftInputs];
          const left = Math.min(...all.map(x => x.r.left));
          const top = Math.min(...all.map(x => x.r.top));
          const right = Math.max(...all.map(x => x.r.right));
          const bottom = Math.max(...all.map(x => x.r.bottom));
          const x = Math.max(0, left - 20);
          const y = Math.max(0, top - 20);
          return {
            x,
            y,
            width: Math.min(document.documentElement.scrollWidth, right + 20) - x,
            height: Math.min(document.documentElement.scrollHeight, bottom + 20) - y
          };
        }"""
    )


def run(args):
    from playwright.sync_api import sync_playwright

    user, pwd = load_creds()
    if not user:
        print("[winrate_pending] ~/.claude/tongyu-creds.json not found")
        return

    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            PROFILE_DIR,
            headless=not args.headed,
            args=["--no-sandbox", "--disable-gpu", "--disable-blink-features=AutomationControlled"],
            viewport={"width": 1232, "height": 900},
        )
        ctx.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        try:
            page = ctx.new_page()
            page.goto(f"{BASE}/#/login", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(5000)
            if "/#/login" in page.url and page.locator(f'input[placeholder*="{TEXT["username"]}"]').count() > 0:
                page.locator(f'input[placeholder*="{TEXT["username"]}"]').click()
                page.locator(f'input[placeholder*="{TEXT["username"]}"]').press_sequentially(user, delay=40)
                page.locator(f'input[placeholder*="{TEXT["password"]}"]').click()
                page.locator(f'input[placeholder*="{TEXT["password"]}"]').press_sequentially(pwd, delay=40)
                page.get_by_role("button", name=TEXT["login"]).click()
                page.wait_for_timeout(6000)
            if "/#/login" in page.url:
                if args.headed:
                    page.wait_for_function("() => !location.href.includes('/#/login')", timeout=120000)
                else:
                    print("[winrate_pending] login slider in headless mode")
                    return
            page.evaluate("() => { document.querySelectorAll('.fast-refer-to-quotation-modal, .ant-modal-mask').forEach(e => e.remove()); }")
            page.goto(f"{BASE}/#/investmentAnalysis/InvestmentAnalysis", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000)
            for _ in range(3):
                page.evaluate("() => { document.querySelectorAll('.fast-refer-to-quotation-modal, .ant-modal-mask').forEach(e => e.remove()); }")
                page.wait_for_timeout(300)
            click_exact_text(page, "DCN")
            page.wait_for_timeout(1000)
            click_exact_text(page, TEXT["step_down"])
            page.wait_for_timeout(800)
            click_exact_text(page, TEXT["parachute"])
            page.wait_for_timeout(1000)
            click_exact_text(page, TEXT["locked"])
            page.wait_for_timeout(400)
            click_exact_text(page, TEXT["no_margin_call"])
            page.wait_for_timeout(400)
            for label, value in [
                (TEXT["term"], args.term),
                (TEXT["first_ko"], args.ko),
                (TEXT["terminal_barrier"], args.parachute),
                (TEXT["coupon_barrier"], args.coupon_line),
                (TEXT["ko_step"], args.step_down),
                (TEXT["coupon"], args.coupon),
            ]:
                print(set_by_label(page, label, value))
                page.wait_for_timeout(150)
            if args.lock != 3:
                print(set_by_label(page, TEXT["lock"], args.lock))
            click_exact_text(page, TEXT["analyze"])
            page.wait_for_timeout(6000)
            winrate = page.evaluate(
                """(label) => {
                  const el = Array.from(document.querySelectorAll('*')).find(e => e.children.length === 0 && e.textContent.trim() === label);
                  return el ? el.parentElement.textContent.replace(label, '').trim() : null;
                }""",
                TEXT["winrate"],
            )
            box = result_screenshot_box(page)
            if box:
                page.screenshot(path=args.output, full_page=True, clip={
                    "x": float(box["x"]),
                    "y": float(box["y"]),
                    "width": float(box["width"]),
                    "height": float(box["height"]),
                })
            else:
                page.screenshot(path=args.output, full_page=True)
            print(f"winrate: {winrate}")
            print(f"screenshot: {args.output}")
        finally:
            ctx.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--term", type=int, required=True)
    parser.add_argument("--lock", type=int, default=3)
    parser.add_argument("--ko", type=float, required=True)
    parser.add_argument("--step-down", type=float, required=True)
    parser.add_argument("--parachute", type=float, required=True)
    parser.add_argument("--coupon-line", type=float, required=True)
    parser.add_argument("--coupon", type=float, required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--headed", action="store_true")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
