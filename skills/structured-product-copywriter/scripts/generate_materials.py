#!/usr/bin/env python3
"""一键生成结构化产品推介物料（支持复合结构自动拆分DCN+锁盈）。

用法(普通结构):
  xvfb-run -a python3 generate_materials.py --structure 早利 --term 36 --lock 3 --margin 50 \
    --ko 101 --step-down 0.5 --parachute 68 --rate1 33 --rate2 0.75 --rate1-start 3 --rate2-start 19 \
    --underlying 中证1000 --manager "青岛鹿秀" --product "鹿秀物华" \
    --entry-point 7800 --title "鹿秀物华-2倍早利锁盈"

用法(复合结构):
  xvfb-run -a python3 generate_materials.py --composite \
    --underlying 中证1000 --term 36 --lock 3 --ko 101 --step-down 0.5 --parachute 65 \
    --dcn-margin 100 --dcn-coupon-line 78 --dcn-coupon 0.699 --dcn-dividend-coupon 0.699 \
    --locky-margin 35 --locky-rate1 3.27 --locky-rate2 0.04 --locky-rate1-start 3 --locky-rate2-start 19 \
    --entry-point 7800 --manager "管理人" --product "产品名" --title "产品名-复合DCN锁盈"

脚本自动:
  1. 取当前点位(fetch_quote)
  2. 复合→分别跑DCN+锁盈的tongyu_winrate(直调API)→取两组WINRATE_RESULT
  3. 复合→分别跑DCN(product_card)+锁盈(product_card_locky)点位图
  4. 拼manifest(复合:第5节2图,第6节body+image+body+image)
  5. 跑create_feishu_doc.py建飞书云文档
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent
SCRIPTS = SKILL_DIR / "scripts"
ASSETS = SKILL_DIR / "assets"


def run(cmd, timeout=300):
    """运行命令，返回stdout。"""
    print(f"\n{'='*60}\nCMD: {cmd}\n{'='*60}")
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout, cwd=str(SKILL_DIR))
        print(r.stdout[-2000:] if len(r.stdout) > 2000 else r.stdout)
        if r.stderr:
            print("STDERR:", r.stderr[-500:])
        return r.stdout
    except subprocess.TimeoutExpired:
        print("TIMEOUT")
        return ""


def parse_winrate_result(stdout):
    """从tongyu_winrate.py输出里提取WINRATE_RESULT行。"""
    for line in stdout.split("\n"):
        if line.startswith("WINRATE_RESULT:"):
            parts = {}
            for kv in line[len("WINRATE_RESULT:"):].strip().split():
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    parts[k] = v
            return parts
    return None


def main():
    ap = argparse.ArgumentParser(description="一键生成推介物料")
    ap.add_argument("--composite", action="store_true", help="复合结构(月增产品)")
    ap.add_argument("--structure", default="早利", help="普通结构:DCN/经典/早利/凤凰/蝶变")
    ap.add_argument("--underlying", default="中证1000")
    ap.add_argument("--term", type=int, default=36)
    ap.add_argument("--lock", type=int, default=3)
    ap.add_argument("--ko", type=float, default=101)
    ap.add_argument("--step-down", type=float, default=0.5)
    ap.add_argument("--parachute", type=float, default=68)
    ap.add_argument("--entry-point", type=float, default=0, help="入场点位(0=自动fetch_quote)")
    ap.add_argument("--manager", default="")
    ap.add_argument("--product", default="")
    ap.add_argument("--title", default="")
    ap.add_argument("--margin", type=int, default=50)
    # 锁盈参数
    ap.add_argument("--rate1", type=float, default=33)
    ap.add_argument("--rate2", type=float, default=0.75)
    ap.add_argument("--rate1-start", type=int, default=3)
    ap.add_argument("--rate2-start", type=int, default=19)
    # DCN参数
    ap.add_argument("--coupon-line", type=float, default=78)
    ap.add_argument("--coupon", type=float, default=1.39)
    # 复合结构DCN子参数
    ap.add_argument("--dcn-margin", type=int, default=100)
    ap.add_argument("--dcn-coupon-line", type=float, default=78)
    ap.add_argument("--dcn-coupon", type=float, default=0.699)
    ap.add_argument("--dcn-dividend-coupon", type=str, default="0.699")
    # 复合结构锁盈子参数
    ap.add_argument("--locky-margin", type=int, default=35)
    ap.add_argument("--locky-rate1", type=float, default=3.27)
    ap.add_argument("--locky-rate2", type=float, default=0.04)
    ap.add_argument("--locky-rate1-start", type=int, default=3)
    ap.add_argument("--locky-rate2-start", type=int, default=19)
    args = ap.parse_args()

    ASSETS.mkdir(exist_ok=True)

    # 1. 取当前点位
    entry_point = args.entry_point
    if entry_point == 0:
        print("=== 取当前点位 ===")
        out = run(f"python3 scripts/fetch_quote.py {args.underlying}")
        for line in out.split("\n"):
            if "最新点位" in line:
                try:
                    entry_point = float(line.split(":")[-1].strip())
                except ValueError:
                    pass
                break
        if entry_point == 0:
            print("ERROR: 取不到点位，请用 --entry-point 指定")
            return

    # 2. 胜率回测
    winrate_results = {}  # {结构名: {winrate, start, end, card}}

    if args.composite:
        print("\n" + "="*60)
        print("复合结构：严格串行跑 DCN + 锁盈 胜率（共用profile，必须串行+清lock）")
        print("="*60)

        # DCN胜率（先跑）
        dcn_out = f"assets/tongyu-winrate-DCN.png"
        # 清profile lock，确保profile不被上一个进程锁住
        run("rm -f /root/.claude/tongyu-profile/Singleton* 2>/dev/null")
        stdout = run(
            f"xvfb-run -a python3 scripts/tongyu_winrate.py "
            f"--structure DCN --term {args.term} --lock {args.lock} --margin {args.dcn_margin} "
            f"--ko {args.ko} --step-down {args.step_down} --parachute {args.parachute} "
            f"--coupon-line {args.dcn_coupon_line} --coupon {args.dcn_coupon} "
            f"--dividend-coupon {args.dcn_dividend_coupon} --option-structure SNOWBALL_FIXED "
            f"--rate1 0 --rate2 0 --output {dcn_out} --headed"
        )
        wr = parse_winrate_result(stdout)
        if wr:
            winrate_results["DCN"] = wr
            print(f"✅ DCN胜率: {wr.get('winrate','?')}")
        else:
            print("❌ DCN胜率: 直调API失败(检查token/profile)")

        # 清profile lock，等DCN的浏览器完全退出
        run("rm -f /root/.claude/tongyu-profile/Singleton* 2>/dev/null; sleep 3")

        # 锁盈胜率（后跑，串行）
        locky_out = f"assets/tongyu-winrate-锁盈.png"
        stdout = run(
            f"xvfb-run -a python3 scripts/tongyu_winrate.py "
            f"--structure 早利 --term {args.term} --lock {args.lock} --margin {args.locky_margin} "
            f"--ko {args.ko} --step-down {args.step_down} --parachute {args.parachute} "
            f"--rate1 {args.locky_rate1} --rate2 {args.locky_rate2} "
            f"--rate1-start {args.locky_rate1_start} --rate2-start {args.locky_rate2_start} "
            f"--dividend-coupon 0 --option-structure SNOWBALL_FLOATING "
            f"--output {locky_out} --headed"
        )
        wr = parse_winrate_result(stdout)
        if wr:
            winrate_results["锁盈"] = wr
            print(f"✅ 锁盈胜率: {wr.get('winrate','?')}")
        else:
            print("❌ 锁盈胜率: 直调API失败(检查token/profile)")

        # 清lock
        run("rm -f /root/.claude/tongyu-profile/Singleton* 2>/dev/null")

    else:
        # 普通结构(单结构)
        out_file = f"assets/tongyu-winrate-{args.underlying}.png"
        is_dcn = args.structure.upper() == "DCN"
        stdout = run(
            f"xvfb-run -a python3 scripts/tongyu_winrate.py "
            f"--structure {args.structure} --term {args.term} --lock {args.lock} --margin {args.margin} "
            f"--ko {args.ko} --step-down {args.step_down} --parachute {args.parachute} "
            + (f"--coupon-line {args.coupon_line} --coupon {args.coupon} "
               f"--dividend-coupon {args.coupon} --option-structure SNOWBALL_FIXED --rate1 0 --rate2 0 "
               if is_dcn else
               f"--rate1 {args.rate1} --rate2 {args.rate2} "
               f"--rate1-start {args.rate1_start} --rate2-start {args.rate2_start} "
               f"--dividend-coupon 0 --option-structure SNOWBALL_FLOATING ")
            + f"--output {out_file} --headed"
        )
        wr = parse_winrate_result(stdout)
        if wr:
            winrate_results[args.structure] = wr
            print(f"{args.structure}胜率: {wr.get('winrate','?')}")

    # 3. 产品点位图
    if args.composite:
        # DCN点位图
        run(
            f"python3 scripts/product_card.py --underlying {args.underlying} "
            f"--term {args.term} --lock {args.lock} --margin {args.dcn_margin} "
            f"--ko {args.ko} --step-down {args.step_down} --parachute {args.parachute} "
            f"--coupon-line {args.dcn_coupon_line} --coupon {args.dcn_coupon} "
            f"--entry-point {entry_point} --output assets/product-card-DCN.png"
        )
        # 锁盈点位图
        run(
            f"xvfb-run -a python3 scripts/product_card_locky.py "
            f"--title '{args.product}-{args.structure}' "
            f"--term {args.term} --lock {args.lock} --margin {args.locky_margin} "
            f"--ko {args.ko} --step-down {args.step_down} --parachute {args.parachute} "
            f"--parachute-months {args.term} "
            f"--rate1-start {args.locky_rate1_start} --rate1-end {args.locky_rate1_start+15} "
            f"--rate1 {args.locky_rate1} "
            f"--rate2-start {args.locky_rate2_start} --rate2-end {args.term} "
            f"--rate2 {args.locky_rate2} "
            f"--entry-point {entry_point} --output assets/product-card-锁盈.png"
        )
    else:
        is_dcn = args.structure.upper() == "DCN"
        if is_dcn:
            run(
                f"python3 scripts/product_card.py --underlying {args.underlying} "
                f"--term {args.term} --lock {args.lock} --margin {args.margin} "
                f"--ko {args.ko} --step-down {args.step_down} --parachute {args.parachute} "
                f"--coupon-line {args.coupon_line} --coupon {args.coupon} "
                f"--entry-point {entry_point} --output assets/product-card-{args.underlying}.png"
            )
        else:
            run(
                f"xvfb-run -a python3 scripts/product_card_locky.py "
                f"--title '{args.product}-{args.structure}' "
                f"--term {args.term} --lock {args.lock} --margin {args.margin} "
                f"--ko {args.ko} --step-down {args.step_down} --parachute {args.parachute} "
                f"--parachute-months {args.term} "
                f"--rate1-start {args.rate1_start} --rate1-end {args.rate1_start+15} "
                f"--rate1 {args.rate1} "
                f"--rate2-start {args.rate2_start} --rate2-end {args.term} "
                f"--rate2 {args.rate2} "
                f"--entry-point {entry_point} --output assets/product-card-{args.underlying}.png"
            )

    # 4. 托管户核验
    if args.manager:
        run(f"python3 scripts/fetch_custody_info.py --manager '{args.manager}' --output assets/custody-{args.manager}.png")

    # 5. AMAC截图
    if args.manager and args.product:
        run(f"python3 scripts/amac_screenshot.py --manager '{args.manager}' --product '{args.product}' --outdir assets")

    # 6. 拼manifest
    print("\n=== 拼manifest ===")
    title = args.title or f"{args.product}-{args.structure}"

    sections = [
        {"type":"subheading","text":"产品结构文字版（长版）"},
        {"type":"copy_file","path":"copy_long.txt"},
        {"type":"subheading","text":"产品结构文字版（短版）"},
        {"type":"copy_file","path":"copy_short.txt"},
        {"type":"subheading","text":"产品公告群通知"},
        {"type":"body","text":""},
        {"type":"subheading","text":"稳定版接龙通知"},
        {"type":"body","text":""},
    ]

    # 第5节:点位图
    sections.append({"type":"subheading","text":"产品派息与敲出观察点位表图片"})
    if args.composite:
        sections.append({"type":"image","path":"assets/product-card-DCN.png","caption":"DCN结构点位表"})
        sections.append({"type":"image","path":"assets/product-card-锁盈.png","caption":"锁盈结构点位表"})
    else:
        sections.append({"type":"image","path":f"assets/product-card-{args.underlying}.png","caption":"产品派息与敲出观察点位表图片"})

    # 第6节:胜率
    sections.append({"type":"subheading","text":"产品胜率数据"})
    if args.composite:
        dcn_wr = winrate_results.get("DCN", {})
        locky_wr = winrate_results.get("锁盈", {})
        sections.append({"type":"body","text":f"DCN结构：回测时间从{dcn_wr.get('start','待补')}到{dcn_wr.get('end','待补')}，本产品胜率：{dcn_wr.get('winrate','待补')}"})
        sections.append({"type":"image","path":"assets/tongyu-winrate-DCN.png","caption":"DCN胜率数据"})
        sections.append({"type":"body","text":f"锁盈结构：回测时间从{locky_wr.get('start','待补')}到{locky_wr.get('end','待补')}，本产品胜率：{locky_wr.get('winrate','待补')}"})
        sections.append({"type":"image","path":"assets/tongyu-winrate-锁盈.png","caption":"锁盈胜率数据"})
    else:
        wr = list(winrate_results.values())[0] if winrate_results else {}
        card_path = f"assets/tongyu-winrate-{args.underlying}.png" if not args.composite else ""
        sections.append({"type":"body","text":f"回测时间从{wr.get('start','待补')}到{wr.get('end','待补')}，本产品胜率：{wr.get('winrate','待补')}%"})
        sections.append({"type":"image","path":card_path,"caption":"产品胜率数据"})

    # 第7-12节
    sections.append({"type":"subheading","text":"一页通"})
    sections.append({"type":"body","text":"[图片待补: 一页通]"})
    sections.append({"type":"subheading","text":"注意事项"})
    sections.append({"type":"body","text":"申购费：（待补充）\n赎回费：（待补充）\n基金合同：（待补充）"})
    sections.append({"type":"subheading","text":"管理人-基金业协会公示图"})
    sections.append({"type":"body","text":args.manager or "管理人名称待补"})
    sections.append({"type":"image","path":"assets/amac-manager.png","caption":"管理人基金业协会公示图"})
    sections.append({"type":"subheading","text":"产品-基金业协会公示图"})
    sections.append({"type":"body","text":args.product or "产品名称待补"})
    sections.append({"type":"image","path":"assets/amac-product.png","caption":"产品基金业协会公示图"})
    sections.append({"type":"subheading","text":"托管募集账户核对"})
    custody_body = "账户：[待补充]\n账号：[待补充]\n银行：[待补充]"
    if args.manager and (ASSETS / f"custody-{args.manager}.png").exists():
        custody_body += f"\n募集户核对地址：见下方截图"
        sections.append({"type":"body","text":custody_body})
        sections.append({"type":"image","path":f"assets/custody-{args.manager}.png","caption":"托管户核验方式"})
    else:
        custody_body += "\n[托管户核验方式待补]"
        sections.append({"type":"body","text":custody_body})
    sections.append({"type":"subheading","text":"销售常见问题"})
    sections.append({"type":"link_list","items":[]})

    manifest = {
        "product_name": args.product,
        "product_short_name": args.product.split("私募")[0] if args.product else "",
        "structure_name": args.structure if not args.composite else "复合DCN锁盈",
        "sections": sections,
    }

    manifest_path = SKILL_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"manifest saved: {manifest_path}")

    # 7. 建飞书云文档
    print("\n=== 建飞书云文档 ===")
    run(
        f"WORKBENCH_BASE_URL=http://127.0.0.1:3001 "
        f"python3 scripts/create_feishu_doc.py --manifest manifest.json --title '{title}'"
    )

    print(f"\n{'='*60}")
    print("物料生成完成！")
    if args.composite:
        print(f"DCN胜率: {winrate_results.get('DCN',{}).get('winrate','?')}")
        print(f"锁盈胜率: {winrate_results.get('锁盈',{}).get('winrate','?')}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
