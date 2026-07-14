#!/usr/bin/env python3
"""Tongyu structured-product backtest automation."""
import argparse
import json
import re
from datetime import date
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
    "last_ko": zh(r"\u672b\u6b21\u89c2\u5bdf\u6572\u51fa\u4ef7"),
    "coupon_barrier": zh(r"\u6d3e\u606f\u969c\u788d\u4ef7"),
    "ko_step": zh(r"\u6572\u51fa\u4ef7\u9012\u51cf\u6b65\u957f"),
    "coupon": zh(r"\u6bcf\u6708\u6216\u6709\u6d3e\u606f"),
    "lock": zh(r"\u9501\u5b9a\u671f"),
    "analyze": zh(r"\u7acb\u5373\u5206\u6790"),
    "date_range": zh(r"\u56de\u6d4b\u533a\u95f4"),
    "winrate": "\u80dc\u7387",
    "early": "\u65e9\u5229\u7ed3\u6784",
    "classic": "\u7ecf\u5178\u7ed3\u6784",
    "phoenix": "\u51e4\u51f0\u7ed3\u6784",
    "butterfly": "\u8776\u53d8\u7ed3\u6784",
    "single_struct": "\u5355\u4e00\u7ed3\u6784",
    "fcn": "FCN",
}


def load_creds():
    if CREDENTIALS.exists():
        data = json.loads(CREDENTIALS.read_text(encoding="utf-8"))
        return data.get("username", ""), data.get("password", "")
    return "", ""


def set_backtest_range(page):
    """显式把「回测区间」设成硬性 10 年：开始日=今天−10 年、结束日=今天。

    旧版只设结束日、开始日吃终端默认≈10 年；结束日 native setter 在 antd DatePicker 上
    flaky（实测落后几天）。本版同时显式设两个日期，并 best-effort 点 picker「今天」加固结束日；
    设不上不阻断，由读取 date_range 后的 `_warn_if_range_stale` 校验「结束日=今天 + 区间≈10 年」
    告警兜底——agent 看告警可在 picker 手动改后重跑。短历史标的终端会自动 clamp 到最大可得区间。"""
    today = date.today()
    try:
        start = today.replace(year=today.year - 10)  # 今天−10 年（Feb29 等边界由终端 clamp）
    except ValueError:
        start = today.replace(year=today.year - 10, day=28)
    start_s, end_s = start.isoformat(), today.isoformat()
    res = page.evaluate(
        """({start, end}) => {
          const all = Array.from(document.querySelectorAll('input'));
          let rs = all.find(i => /开始|Start/i.test(i.placeholder || ''));
          let re = all.find(i => /结束|End/i.test(i.placeholder || ''));
          if (!rs || !re) {
            const lbl = Array.from(document.querySelectorAll('*')).find(e => e.children.length===0 && (e.textContent||'').includes('回测区间'));
            let c = lbl;
            for (let i=0;i<6 && c && (!rs || !re);i++){ c=c.parentElement; if(c){ const ins=c.querySelectorAll('input'); if(ins.length>=2){ rs=rs||ins[0]; re=re||ins[1]; } } }
          }
          const setv = (inp, v) => { if(!inp) return 'NOINPUT'; const s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set; s.call(inp, v); inp.dispatchEvent(new Event('input',{bubbles:true})); inp.dispatchEvent(new Event('change',{bubbles:true})); inp.dispatchEvent(new Event('blur',{bubbles:true})); return inp.value; };
          return {start: setv(rs, start), end: setv(re, end)};
        }""",
        {"start": start_s, "end": end_s},
    )
    # 结束日=今天：点结束日期 input 弹 antd RangePicker 面板（无"今天"按钮），点今天的日期单元格 .ant-picker-cell-today
    try:
        end_inp = page.locator("input[placeholder*='结束'], input[placeholder*='End']").first
        end_inp.click()
        today_cell = page.locator(".ant-picker-cell-today").first
        today_cell.wait_for(state="visible", timeout=5000)
        today_cell.click()
        page.wait_for_timeout(800)
        print("end-date today-cell clicked")
    except Exception as e:
        print(f"end-date today click failed: {e}")
    # 关掉可能弹出的 picker 面板，避免遮挡「立即分析」按钮。
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass
    return f"backtest_range best-effort(start={start_s}, end={end_s}): {res}"


def _parse_range_dates(date_range_text):
    """从 date_range 文本解析(开始日, 结束日)。结束日=区间里最后一个 yyyy-mm-dd 形态日期。"""
    if not date_range_text:
        return None, None
    m = re.findall(r"(\d{4})\D(\d{1,2})\D(\d{1,2})", date_range_text)
    if len(m) < 2:
        return None, None
    try:
        sy, smo, sd = (int(x) for x in m[0])
        ey, emo, ed = (int(x) for x in m[-1])
        return date(sy, smo, sd), date(ey, emo, ed)
    except ValueError:
        return None, None


def _warn_if_range_stale(date_range_text):
    """校验回测区间=硬性 10 年（开始日≈今天−10 年、结束日≈今天）。偏离就告警。"""
    start_d, end_d = _parse_range_dates(date_range_text)
    if not end_d:
        return
    today = date.today()
    try:
        want_start = today.replace(year=today.year - 10)
    except ValueError:
        want_start = today.replace(year=today.year - 10, day=28)
    end_off = (today - end_d).days
    interval_days = (end_d - start_d).days if start_d else 0
    msgs = []
    if abs(end_off) > 3:
        msgs.append(f"结束日 {end_d} ≠ 今天 {today}（差 {end_off} 天）")
    if start_d and not (3450 <= interval_days <= 3850):
        msgs.append(f"区间 {start_d}~{end_d} ≈ {interval_days/365:.1f} 年，非硬性 10 年")
    if msgs:
        print(f"[warn] 回测区间偏离硬性设定：{'；'.join(msgs)}。请在通徐 picker 手动把开始日设成 {want_start}、结束日设成 {today} 后重跑。")


def set_by_label(page, label, value):
    """按 label 文本定位 input，用 Playwright .fill() 填值。

    antd InputNumber 是 React 受控组件：用 native value setter + dispatchEvent 设值会「回弹」
    （实测期限能留下、首次观察敲出价/期末障碍价/末次观察敲出价/敲出价递减步长都回弹成默认值）。
    .fill() 走 Playwright 的 input 事件路径，能触发 React 合成 onChange 提交。返回 label: 当前值。"""
    inp = page.evaluate_handle(
        """(lbl) => {
          let el = null;
          for (const e of Array.from(document.querySelectorAll('div,span,label'))) {
            if (e.textContent.trim() === lbl) { el = e; break; }
          }
          if (!el) return null;
          let c = el;
          for (let i = 0; i < 6; i++) {
            c = c.parentElement;
            if (!c) break;
            const inp = c.querySelector('input');
            if (inp) return inp;
          }
          return null;
        }""",
        label,
    )
    el = inp.as_element()
    if not el:
        return f"{label}: NOTFOUND"
    try:
        el.click()
        el.fill(str(value))
        try:
            el.press("Tab")
        except Exception:
            pass
        val = el.input_value()
        return f"{label}: {val}"
    except Exception as e:
        return f"{label}: NOINPUT ({e})"


def set_by_label_candidates(page, candidates, value):
    """尝试一组候选 label，第一个定位到 input 的就填，返回结果串。用于字段名不确定的早利敲出票息区间。"""
    for lbl in candidates:
        res = set_by_label(page, lbl, value)
        if "NOTFOUND" not in res and "NOINPUT" not in res:
            return f"{lbl}: {res} (filled)"
    return f"candidates {candidates}: all NOTFOUND (value={value} not filled)"


def dump_form(page):
    """打印当前表单所有 input 的占位文本/值/父级文本，便于核对字段是否填上、学习字段名。"""
    pairs = page.evaluate(
        """() => {
          const out = [];
          document.querySelectorAll('input').forEach((inp, i) => {
            const ph = (inp.placeholder||'').trim();
            let parentText='';
            let c=inp.parentElement;
            for(let k=0;k<5 && c;k++){ c=c.parentElement; if(!c)break; const t=(c.innerText||c.textContent||'').trim().slice(0,40); if(t){parentText=t;break;} }
            out.push({i, ph, value: inp.value, parent: parentText});
          });
          return out;
        }"""
    )
    print("--- form dump ---")
    for p in pairs:
        print(f"  #{p.get('i')} ph={p.get('ph')!r} value={p.get('value')!r} parent={p.get('parent')!r}")
    print("--- /form dump ---")


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


def resolve_base_structure(name, args):
    """结构名 → 5 类基础结构之一(经典/凤凰/早利/蝶变/DCN)。

    歧义词(多倍锁盈/全保锁盈等无经典/早利关键词)按分段票息推断：
    前段票息 ≥ 后段 × 2（且后段 > 0）→早利；否则经典。"""
    n = (name or "DCN").strip()
    low = n.lower()
    if "dcn" in low:
        return "DCN"
    if "凤凰" in n or "phoenix" in low:
        return TEXT["phoenix"]
    if "蝶变" in n or "butterfly" in low:
        return TEXT["butterfly"]
    if "早利" in n or "early" in low:
        return TEXT["early"]
    if "经典" in n or "classic" in low:
        return TEXT["classic"]
    # 歧义词：按分段票息推断（前段 ≥ 后段×2 → 早利）
    r1 = float(args.rate1 or 0)
    r2 = float(args.rate2 or 0)
    if r2 > 0 and r1 >= r2 * 2:
        return TEXT["early"]
    return TEXT["classic"]


def click_single_structure_fcn(page):
    """单一结构类型恒点 FCN（所有结构都显式点，不靠系统默认）。

    定位「单一结构」标签父级容器内的 FCN 选项点击；定位不到 best-effort 点全局 FCN，
    不阻断流程。"""
    res = page.evaluate(
        """() => {
          const all = Array.from(document.querySelectorAll('*'));
          const lbl = all.find(e => e.children.length === 0 && (e.textContent||'').includes('单一结构'));
          if (lbl) {
            let c = lbl;
            for (let i=0;i<6 && c;i++){ c=c.parentElement; if(c){ const hit=Array.from(c.querySelectorAll('*')).find(e=>e.children.length===0 && (e.textContent||'').trim()==='FCN'); if(hit){ hit.click(); return 'clicked:in-section'; } } }
          }
          const fcn = all.find(e => e.children.length === 0 && (e.textContent||'').trim() === 'FCN');
          if (fcn) { fcn.click(); return 'clicked:fallback'; }
          return 'NOINPUT';
        }"""
    )
    print(f"single_struct FCN best-effort: {res}")
    return res


def inspect_form_structure(page):
    """诊断：dump 胜率回测表单结构选择区的真实 DOM，定位早利/经典等结构卡片与单一/组合结构模式切换的真实选择器。"""
    print("=== INSPECT: structure-selection DOM (text matches 早利/经典/凤凰/蝶变/DCN/单一结构/组合结构/基础结构) ===")
    hits = page.evaluate(
        """() => {
          const kws = ['早利','经典','凤凰','蝶变','DCN','单一结构','组合结构','基础结构'];
          const all = Array.from(document.querySelectorAll('body *'));
          const hits = all.filter(e => {
            const t = (e.textContent||'').trim();
            if (!t || t.length > 30) return false;
            return kws.some(k => t.includes(k));
          });
          return hits.map(e => {
            const r = e.getBoundingClientRect();
            const cs = getComputedStyle(e);
            const cn = (e.className && e.className.toString) ? e.className.toString() : '';
            return {
              tag: e.tagName.toLowerCase(),
              cls: cn.slice(0,60),
              text: (e.textContent||'').trim().slice(0,30),
              cursor: cs.cursor,
              onclick: !!e.onclick,
              isInput: e.tagName==='INPUT',
              inputType: e.tagName==='INPUT' ? (e.type||'') : '',
              name: e.name||'',
              value: e.tagName==='INPUT' ? String(e.value).slice(0,15) : '',
              checked: e.checked===true,
              rect: [Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)],
              parentCls: (e.parentElement && e.parentElement.className && e.parentElement.className.toString) ? e.parentElement.className.toString().slice(0,40) : '',
            };
          });
        }"""
    )
    for i, h in enumerate(hits or []):
        print(f"  [{i}] {h}")
    print("=== container outerHTML (first '组合结构' container, <=80 descendants) ===")
    html = page.evaluate(
        """() => {
          const all = Array.from(document.querySelectorAll('body *'));
          const c = all.find(e => (e.textContent||'').includes('组合结构') && e.querySelectorAll('*').length < 80);
          return c ? c.outerHTML.slice(0,3000) : 'NOTFOUND';
        }"""
    )
    print(html)
    print("=== coupon-section container (contains 'M至', 4-8 inputs) + its inputs ===")
    coupon = page.evaluate(
        """() => {
          const all = Array.from(document.querySelectorAll('body *'));
          const c = all.find(e => (e.textContent||'').includes('M至') && e.querySelectorAll('input').length>=4 && e.querySelectorAll('input').length<=8);
          if (!c) return 'NOTFOUND';
          const ins = Array.from(c.querySelectorAll('input')).map((inp,i) => ({i, ph:inp.placeholder||'', value:inp.value, disabled:inp.disabled, readOnly:inp.readOnly, type:inp.type||'', parentText:(inp.parentElement&&inp.parentElement.textContent||'').trim().slice(0,20)}));
          return {inputs: ins, html: c.outerHTML.slice(0,2000)};
        }"""
    )
    print(coupon)
    print("=== 期末障碍价 input detail ===")
    tb = page.evaluate(
        """() => {
          const ins = Array.from(document.querySelectorAll('input'));
          const t = ins.find(i => ((i.parentElement&&i.parentElement.textContent)||'').includes('期末障碍价'));
          if (!t) return 'NOTFOUND';
          return {value:t.value, disabled:t.disabled, readOnly:t.readOnly, type:t.type, parentText:(t.parentElement.textContent||'').trim().slice(0,40), parentHTML:(t.parentElement.outerHTML||'').slice(0,400)};
        }"""
    )
    print(tb)
    print("=== date picker (开始/结束日期 + 今天 btn) ===")
    dt = page.evaluate(
        """() => {
          const ins = Array.from(document.querySelectorAll('input'));
          const dates = ins.filter(i => /日期|开始|结束/.test(i.placeholder||'')).map(i => ({ph:i.placeholder, value:i.value, disabled:i.disabled, readOnly:i.readOnly}));
          const today = Array.from(document.querySelectorAll('*')).find(e => e.children.length===0 && (e.textContent||'').trim()==='今天');
          return {dates, todayBtn: today ? {tag:today.tagName.toLowerCase(), cls:(today.className||'').toString().slice(0,40), display:getComputedStyle(today).display, parentCls:((today.parentElement||{}).className||'').toString().slice(0,40)} : 'NOTFOUND'};
        }"""
    )
    print(dt)


def set_by_label_typing(page, label, value):
    """对 .fill() 不生效(回弹/清空)的 antd InputNumber，改用 click→Ctrl+A 全选→pressSequentially 逐字输入→Tab。
    定位逻辑同 set_by_label（label 文本→上溯找 input）。"""
    inp = page.evaluate_handle(
        """(lbl) => {
          let el = null;
          for (const e of Array.from(document.querySelectorAll('div,span,label'))) {
            if (e.textContent.trim() === lbl) { el = e; break; }
          }
          if (!el) return null;
          let c = el;
          for (let i = 0; i < 6; i++) {
            c = c.parentElement;
            if (!c) break;
            const inp = c.querySelector('input');
            if (inp) return inp;
          }
          return null;
        }""",
        label,
    )
    el = inp.as_element()
    if not el:
        return f"{label}: NOTFOUND"
    try:
        el.click()
        try:
            el.press("Control+a")
        except Exception:
            pass
        el.type(str(value), delay=30)
        try:
            el.press("Tab")
        except Exception:
            pass
        return f"{label}: {el.input_value()}"
    except Exception as e:
        return f"{label}: NOINPUT ({e})"


def set_knock_in(page, value):
    """敲入价 label 是动态'敲入价应小于敲出价X'，按父级文本前缀'敲入价'定位 input，逐字输入。
    填写逻辑：敲入价 硬性=1（产品不设敲入价，设1最贴近实际；满足敲入价<末次观察敲出价约束）。"""
    inp = page.evaluate_handle(
        """() => {
          const ins = Array.from(document.querySelectorAll('input'));
          return ins.find(i => {
            let c = i;
            for (let k=0;k<6;k++){
              c = c.parentElement;
              if (!c) break;
              if (((c.textContent)||'').trim().startsWith('敲入价')) return true;
            }
            return false;
          }) || null;
        }"""
    )
    el = inp.as_element()
    if not el:
        return "敲入价: NOTFOUND"
    try:
        el.click()
        try:
            el.press("Control+a")
        except Exception:
            pass
        el.type(str(value), delay=30)
        try:
            el.press("Tab")
        except Exception:
            pass
        return f"敲入价: {el.input_value()}"
    except Exception as e:
        return f"敲入价: NOINPUT ({e})"


def fill_split_coupon(page, args):
    """早利/蝶变分段票息：.split-coupon-wrap 容器内 input 按 DOM 顺序填
    [区间1起, 区间1止, 区间1票息, 区间2起, 区间2止, 区间2票息]。

    label 是通用"M至"/"%"(3个%无法按label区分区间1/2)，只能按容器内位置填。
    区间1票息字段可能是 disabled "待计算"(自动算)，跳过；区间2票息可填。"""
    wrap = page.locator(".split-coupon-wrap, .coupon-list").first
    try:
        count = wrap.locator("input").count()
    except Exception:
        print("split_coupon: NO_WRAP")
        return
    vals = [args.rate1_start, args.rate1_end, args.rate1, args.rate2_start, args.rate2_end, args.rate2]
    results = []
    for i, v in enumerate(vals):
        if i >= count:
            break
        inp = wrap.locator("input").nth(i)
        try:
            disabled = inp.evaluate("e => e.disabled || e.readOnly")
        except Exception:
            disabled = True
        if disabled:
            results.append(f"i{i}:SKIP(disabled)")
            continue
        try:
            inp.click()
            page.wait_for_timeout(100)
            inp.fill(str(v))
            try:
                inp.press("Tab")
            except Exception:
                pass
            val = inp.input_value()
            results.append(f"i{i}:{val}")
        except Exception as e:
            results.append(f"i{i}:ERR({e})")
    print(f"split_coupon: count={count} " + " | ".join(results))
    page.wait_for_timeout(300)


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


def _crop_fallback(path):
    """bounding-box 定位失败时的整页裁图兜底：
    去掉顶部导航栏、底部 1/3、右边 1/4，只留中间结果区（胜率/平均敲出时间/已完结合约表）。
    与 SKILL「先定位结果容器 bounding box」的优先口径一致；此为 box 定不到时的兜底。"""
    try:
        from PIL import Image
    except ImportError:
        return
    im = Image.open(path)
    w, h = im.size
    top = int(h * 0.10)        # 顶部约 10%：导航栏
    bottom = int(h * 2 / 3)    # 去掉底部 1/3
    right = int(w * 3 / 4)     # 去掉右边 1/4
    im.crop((0, top, right, bottom)).save(path)


def run(args):
    from playwright.sync_api import sync_playwright

    user, pwd = load_creds()
    if not user:
        print("[winrate_pending] ~/.claude/tongyu-creds.json not found")
        return

    _ws_info = []
    def _on_ws(ws):
        try:
            _ws_info.append({'open': ws.url})
            def _on_recv(payload):
                try:
                    s = str(payload)
                    if any(k in s for k in ('胜率','winrate','敲出','敲入','合约','profit','rate','盈利','亏损','90','9','data')):
                        _ws_info.append({'recv': s[:600]})
                except Exception:
                    pass
            ws.on("framereceived", _on_recv)
            def _on_sent(payload):
                try:
                    s = str(payload)
                    if any(k in s for k in ('分析','回测','winrate','backtest','analyze','calc','snowball','compute','data')):
                        _ws_info.append({'sent': s[:600]})
                except Exception:
                    pass
            ws.on("framesent", _on_sent)
        except Exception:
            pass

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
            page.on("websocket", _on_ws)
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
            structure = (args.structure or "DCN").strip()
            base = resolve_base_structure(structure, args)  # → 经典/凤凰/早利/蝶变/DCN
            is_seg_coupon = (base != "DCN")  # 非DCN(锁盈类)用分段敲出票息字段
            print(f"structure={structure} -> base={base}, seg_coupon={is_seg_coupon}")
            click_exact_text(page, base)
            page.wait_for_timeout(1000)
            # 单一结构类型恒点 FCN（所有结构都显式点，不靠系统默认）
            click_single_structure_fcn(page)
            page.wait_for_timeout(400)
            click_exact_text(page, TEXT["step_down"])
            page.wait_for_timeout(800)
            click_exact_text(page, TEXT["parachute"])
            page.wait_for_timeout(1000)
            click_exact_text(page, TEXT["locked"])
            page.wait_for_timeout(400)
            click_exact_text(page, TEXT["no_margin_call"])
            page.wait_for_timeout(400)
            # 公共字段：期限/首次观察敲出价/敲出价递减步长先填(末次观察敲出价会随 first_ko+step 自动联动)，
            # 再填期末障碍价/末次观察敲出价(=降落伞)覆盖自动联动的默认 85。
            # 锁盈类规则(用户): 末次观察敲出价=期末障碍价=降落伞; 敲入价=期末障碍价-0.1(使敲入价<末次观察敲出价满足"敲入价应小于敲出价"约束)。
            common_fields = [
                (TEXT["term"], args.term),
                (TEXT["first_ko"], args.ko),
                (TEXT["ko_step"], args.step_down),
                (TEXT["terminal_barrier"], args.parachute),
                (TEXT["last_ko"], args.parachute),
            ]
            for label, value in common_fields:
                print(set_by_label(page, label, value))
                page.wait_for_timeout(200)
            if args.lock != 3:
                print(set_by_label(page, TEXT["lock"], args.lock))
            # 末次观察敲出价二次覆盖（first_ko/step 联动可能重置回 85）。
            page.wait_for_timeout(300)
            print(set_by_label(page, TEXT["last_ko"], args.parachute))
            # 敲入价=1（硬性，产品不设敲入价）；期末障碍价=降落伞=68。表单 敲入价→期末障碍价 联动，
            # 先设敲入价=1、最后设期末障碍价=68 覆盖（若联动单向，期末障碍价=68+敲入价=1 可成分开）。
            if is_seg_coupon:
                page.wait_for_timeout(200)
                print(set_knock_in(page, 1))
            page.wait_for_timeout(200)
            print(set_by_label_typing(page, TEXT["terminal_barrier"], args.parachute))
            page.wait_for_timeout(200)
            # 二次覆盖：末次观察敲出价=68、期末障碍价=68（放最后覆盖敲入价联动，不再动敲入价）
            print(set_by_label(page, TEXT["last_ko"], args.parachute))
            print(set_by_label_typing(page, TEXT["terminal_barrier"], args.parachute))
            if getattr(args, "inspect_form", False):
                inspect_form_structure(page)
                return
            if is_seg_coupon:
                # .split-coupon-wrap 容器内按 DOM 顺序填区间起止+票息（label 是通用"M至"/"%"无法按label区分区间1/2，按位置填）。
                # 注：区间1票息字段可能 disabled "待计算"(自动算)，会被跳过——此时 33% 需另寻主字段，见 dump_form。
                fill_split_coupon(page, args)
                dump_form(page)
                if args.dump_form_only:
                    print("[dump_form_only] 表单已填+已dump，停在「立即分析」前。读上方 form dump 学字段名后，去掉 --dump-form-only 重跑。")
                    return
            else:
                # DCN：派息线 + 每月或有派息
                print(set_by_label(page, TEXT["coupon_barrier"], args.coupon_line))
                page.wait_for_timeout(150)
                print(set_by_label(page, TEXT["coupon"], args.coupon))
                page.wait_for_timeout(150)
            print(set_backtest_range(page))
            page.wait_for_timeout(300)
            import json as _json2
            _reqs = []
            _haina_resps = []
            _haina_reqs = []
            def _on_req(_req):
                try:
                    _reqs.append(_req.method + ' ' + _req.url)
                    if 'haina' in (_req.url or '').lower():
                        body = ''
                        try:
                            body = (_req.post_data or '')[:600]
                        except Exception:
                            body = '<body-unreadable>'
                        _haina_reqs.append({'method': _req.method, 'url': _req.url, 'body': body})
                except Exception:
                    pass
            def _on_resp(_resp):
                try:
                    if 'haina' in (_resp.url or '').lower():
                        body = ''
                        try:
                            body = _resp.text()[:400]
                        except Exception:
                            body = '<body-unreadable>'
                        _haina_resps.append({'status': _resp.status, 'url': _resp.url, 'body': body})
                except Exception:
                    pass
            page.on("request", _on_req)
            page.on("response", _on_resp)
            try:
                page.locator("button:has-text('立即分析')").first.click(timeout=5000)
                print("analyze button clicked (button locator)")
            except Exception as e:
                print(f"analyze button locator failed: {e}; fallback click_exact_text")
                click_exact_text(page, TEXT["analyze"])
            page.wait_for_timeout(3000)
            # type=submit 点击只触发埋点onClick; 试 form.requestSubmit() 直接触发表单 onSubmit(回测)
            try:
                page.evaluate("() => { const f = document.querySelector('form'); if (f) { try { f.requestSubmit(); } catch(e) { try { f.submit(); } catch(e2){} } } }")
                print("form.requestSubmit() called")
            except Exception as e:
                print(f"form.requestSubmit failed: {e}")
            page.wait_for_timeout(45000)
            try:
                page.remove_listener("request", _on_req)
                page.remove_listener("response", _on_resp)
            except Exception:
                pass
            _api_reqs = [u for u in _reqs if any(k in u.lower() for k in ('/api/','analy','backtest','winrate','calc','snowball','struct','quant','compute','haina','ws','socket'))][:25]
            print(f"analyze network reqs ({len(_reqs)} total, {len(_api_reqs)} api-like):", _json2.dumps(_api_reqs, ensure_ascii=False)[:1500])
            print("haina request:", _json2.dumps(_haina_reqs, ensure_ascii=False)[:1200])
            print("haina responses:", _json2.dumps(_haina_resps, ensure_ascii=False)[:1200])
            print("websocket info (early-listener):", _json2.dumps(_ws_info, ensure_ascii=False)[:2000])
            # 诊断：立即分析是否触发了重算（按钮状态/胜率卡/加载指示/错误toast）
            print("post-analyze:", page.evaluate(
                """() => {
                  const btn = Array.from(document.querySelectorAll('*')).find(e => e.children.length===0 && (e.textContent||'').trim()==='立即分析');
                  const wr = Array.from(document.querySelectorAll('*')).find(e => e.children.length===0 && (e.textContent||'').trim()==='胜率');
                  const errs = Array.from(document.querySelectorAll('.ant-message-error, .ant-message-notice-content, .ant-form-item-explain-error, .ant-notification-notice-message, .ant-message-notice')).slice(0,10).map(e=>(e.textContent||'').trim().slice(0,100));
                  // 结果区文本（胜率/已完结合约/平均敲出时间 所在容器）
                  const rc = Array.from(document.querySelectorAll('*')).find(e => (e.textContent||'').includes('已完结合约') && e.querySelectorAll('*').length < 60);
                  return {btnDisabled: btn?btn.disabled:'nobtn', winrateParent: wr?(wr.parentElement.textContent||'').trim().slice(0,40):'', errors: errs, resultArea: rc?(rc.textContent||'').trim().slice(0,200):'no-result-area', buttons: Array.from(document.querySelectorAll('button')).map(b=>({text:(b.textContent||'').trim().slice(0,20), disabled:b.disabled, type:b.type||''})).filter(b=>b.text)};
                }"""
            ))
            read_label = """(label) => {
              const el = Array.from(document.querySelectorAll('*')).find(e => e.children.length === 0 && e.textContent.trim() === label);
              return el ? el.parentElement.textContent.replace(label, '').trim() : null;
            }"""
            winrate = page.evaluate(read_label, TEXT["winrate"])
            date_range = page.evaluate(
                """() => {
                  // 先找含"回测区间"的叶子节点取父级文本
                  const els = Array.from(document.querySelectorAll('*'));
                  const t = els.find(e => e.children.length === 0 && (e.textContent||'').includes('回测区间'));
                  if (t && t.parentElement) {
                    const s = t.parentElement.textContent.replace('回测区间','').trim();
                    if (/20\\d{2}/.test(s)) return s;
                  }
                  // 兜底：正文里抓形如 2016-07-11 ~ 2026-07-10 / 2016年07月11日至2026年07月10日 的区间
                  const m = (document.body.innerText||'').match(/20\\d{2}[\\-\\/年.]\\d{1,2}[\\-\\/月.]\\d{1,2}[^0-9]{0,6}20\\d{2}[\\-\\/年.]\\d{1,2}[\\-\\/月.]\\d{1,2}/);
                  return m ? m[0] : null;
                }"""
            )
            box = None
            for _ in range(3):
                box = result_screenshot_box(page)
                if box:
                    break
                page.wait_for_timeout(1500)
            if box:
                page.screenshot(path=args.output, full_page=True, clip={
                    "x": float(box["x"]),
                    "y": float(box["y"]),
                    "width": float(box["width"]),
                    "height": float(box["height"]),
                })
            else:
                # 兜底：整页截图后裁掉顶部导航栏、底部 1/3、右边 1/4，只留中间结果区。
                page.screenshot(path=args.output, full_page=True)
                _crop_fallback(args.output)
            print(f"winrate: {winrate}")
            print(f"date_range: {date_range}")
            _warn_if_range_stale(date_range)
            print(f"screenshot: {args.output}")
        finally:
            ctx.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--structure", default="DCN", help="基础结构：DCN/经典/早利/凤凰/蝶变；歧义词(多倍锁盈/全保锁盈)按分段票息自动判早利或经典")
    parser.add_argument("--term", type=int, required=True)
    parser.add_argument("--lock", type=int, default=3)
    parser.add_argument("--ko", type=float, required=True)
    parser.add_argument("--step-down", type=float, required=True)
    parser.add_argument("--parachute", type=float, required=True)
    parser.add_argument("--coupon-line", type=float, default=0, help="DCN 派息线；早利不用")
    parser.add_argument("--coupon", type=float, default=0, help="DCN 每月或有派息；早利不用")
    # 早利锁盈敲出票息区间（DCN 忽略）
    parser.add_argument("--rate1-start", type=int, default=3)
    parser.add_argument("--rate1-end", type=int, default=18)
    parser.add_argument("--rate1", type=float, default=33)
    parser.add_argument("--rate2-start", type=int, default=19)
    parser.add_argument("--rate2-end", type=int, default=36)
    parser.add_argument("--rate2", type=float, default=0.75)
    parser.add_argument("--output", required=True)
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--dump-form-only", action="store_true", help="锁盈类(早利/经典)：填完公共字段+dump表单后停在「立即分析」前，用于学习字段名")
    parser.add_argument("--inspect-form", action="store_true", help="诊断：登录+导航到回测表单后dump结构选择区DOM再退出，用于定位早利/经典等结构卡片真实选择器")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
