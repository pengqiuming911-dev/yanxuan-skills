#!/usr/bin/env python3
"""获取指数/个股最新点位,用于结构化产品推介文案的点位换算。

只依赖 Python 标准库(无需 pip install)。优先腾讯接口(无需 Referer),
失败则依次尝试新浪、东方财富。任一源拿到有效价格即返回。

用法:
  python fetch_quote.py                  # 默认中证1000
  python fetch_quote.py 中证1000
  python fetch_quote.py sh000852         # 直接给代码也行
  python fetch_quote.py 沪深300

输出最后一行固定为 "最新点位: <数字>",便于上游程序读取。
全部失败时退出码 1,并提示手动提供点位。
"""
import sys
import json
import urllib.request

# 标的名 -> 行情代码。新增标的在这里加一行即可。
NAME2CODE = {
    "中证1000": "sh000852",
    "中证500": "sh000905",
    "沪深300": "sh000300",
    "沪深300指数": "sh000300",
    "上证指数": "sh000001",
    "上证50": "sh000016",
    "创业板指": "sz399006",
    "创业板指数": "sz399006",
    "科创50": "sh000688",
    "中证A500": "sh932000",
}


def _get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=8) as r:
        raw = r.read()
    # 腾讯/新浪中文常为 GBK;先试 GBK 再试 UTF-8
    for enc in ("gbk", "utf-8"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def _is_number(s):
    try:
        float(s)
        return True
    except (TypeError, ValueError):
        return False


def from_tencent(code):
    """腾讯接口: v_sh000852="1~000852~中证1000~8810.34~8790.50~..."  第4段为最新价。"""
    text = _get(f"https://qt.gtimg.cn/q={code}")
    seg = text.split('"', 2)[1] if '"' in text else ""
    parts = seg.split("~")
    name = parts[1] if len(parts) > 1 else code   # parts[1]=名称, parts[2]=代码, parts[3]=最新价
    cur = parts[3] if len(parts) > 3 else ""
    return name, cur


def from_sina(code):
    """新浪接口: hq_str_sh000852="中证1000,开盘,昨收,最新,..."  第4段为最新价。需 Referer。"""
    text = _get(
        f"https://hq.sinajs.cn/list={code}",
        headers={"User-Agent": "Mozilla/5.0", "Referer": "https://finance.sina.com.cn"},
    )
    seg = text.split('"', 2)[1] if '"' in text else ""
    parts = seg.split(",")
    name = parts[0] if parts else code
    cur = parts[3] if len(parts) > 3 else ""
    return name, cur


def from_eastmoney(code):
    """东方财富 push2 接口,返回 JSON。f43 为最新价(单位:分,需 /100)。"""
    prefix = "1" if code.startswith("sh") else "0"
    secid = f"{prefix}.{code[2:]}"
    url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields=f43,f58"
    data = json.loads(_get(url)).get("data") or {}
    name = data.get("f58") or code
    f43 = data.get("f43")
    if f43 is None:
        return name, ""
    return name, str(f43 / 100.0)


def fetch(code):
    last_err = "未知错误"
    for fn in (from_tencent, from_sina, from_eastmoney):
        try:
            name, cur = fn(code)
            if _is_number(cur):
                return name, float(cur), fn.__name__
            last_err = f"{fn.__name__} 返回无效价格: {cur!r}"
        except Exception as e:  # 网络不通/接口变更等
            last_err = f"{fn.__name__} 异常: {e}"
    return None, None, last_err


def resolve_code(arg):
    """支持中文名、代码、大小写。"""
    if arg in NAME2CODE:
        return NAME2CODE[arg]
    low = arg.lower()
    for k, v in NAME2CODE.items():
        if k.lower() == low:
            return v
    # 直接给代码(如 sh000852 / sz399006)
    a = arg.lower()
    if a.startswith(("sh", "sz")) and len(a) >= 8:
        return a
    return None


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else "中证1000"
    code = resolve_code(arg)
    if not code:
        print(f"无法识别标的「{arg}」。请用中文名(如 中证1000)或代码(如 sh000852)。")
        sys.exit(1)

    name, cur, src = fetch(code)
    if cur is None:
        print(f"⚠️ 自动获取失败({src})。请手动提供 {arg} 当前点位。")
        sys.exit(1)

    print(f"标的: {name} ({code})")
    print(f"数据来源: {src}")
    print(f"最新点位: {cur}")


if __name__ == "__main__":
    main()
