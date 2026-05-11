#!/usr/bin/env python3
"""计算所有促销码的实际价格（pricing-data.js base price - metadata discount）

用法:
  python3 calc_prices.py              # 全量计算
  python3 calc_prices.py GB           # 只算指定地区
"""
import json, os, re, subprocess, sys, time
from urllib.parse import quote
from datetime import datetime

import config

# ─── 配置 ────────────────────────────────────────────────────
CLASH_SOCKET = config.get_clash_socket()
PROXY_URL = config.get_proxy_url()
TOKEN = config.get_token()

# ─── 读取 pricing-data.js ──────────────────────────────────
PRICING_JS = os.path.expanduser("~/statistic ChatGPT/data/pricing-data.js")
if not os.path.exists(PRICING_JS):
    PRICING_JS = "/Volumes/SSD/statistic ChatGPT/data/pricing-data.js"

with open(PRICING_JS) as f:
    content = f.read()

match = re.search(r'PRICING_DATA\s*=\s*(\[[\s\S]*?\]);', content)
pricing_data = json.loads(match.group(1))

BASE = {}
for entry in pricing_data:
    bm = entry.get("prices", {}).get("businessMonth")
    if bm and "amount" in bm:
        BASE[entry["code"]] = {"amount": bm["amount"], "currency": entry["currency"]}

# ─── 地区节点关键字 ──────────────────────────────────────────
REGION_KEYWORDS = {
    "US": ["美国", "🇺🇸"],
    "GB": ["英国", "🇬🇧"],
    "AU": ["澳洲", "澳大利亚", "🇦🇺"],
    "DE": ["德国", "🇩🇪"],
    "FR": ["法国", "🇫🇷"],
    "ES": ["西班牙", "🇪🇸"],
    "CA": ["加拿大", "🇨🇦"],
    "BR": ["巴西", "🇧🇷"],
    "NZ": ["新西兰", "🇳🇿"],
    "KE": ["肯尼亚", "🇰🇪"],
    "ZA": ["南非", "🇿🇦"],
    "NG": ["尼日利亚", "🇳🇬"],
    "TH": ["泰国", "🇹🇭"],
    "SG": ["新加坡", "🇸🇬"],
    "PH": ["菲律宾", "🇵🇭"],
}

REGION_LABELS = {
    "US": "🇺🇸 US", "GB": "🇬🇧 GB", "AU": "🇦🇺 AU", "DE": "🇩🇪 DE",
    "FR": "🇫🇷 FR", "ES": "🇪🇸 ES", "CA": "🇨🇦 CA", "BR": "🇧🇷 BR",
    "NZ": "🇳🇿 NZ", "KE": "🇰🇪 KE", "ZA": "🇿🇦 ZA", "NG": "🇳🇬 NG",
    "TH": "🇹🇭 TH", "SG": "🇸🇬 SG", "PH": "🇵🇭 PH",
}

# ─── 促销码定义 ──────────────────────────────────────────────
# (code, country_cc)
ALL_CODES = [
    ("thealloynetwork", "US"),
    ("alongsideus", "US"),
    ("monicaius", "US"),
    ("talentgeniusus", "US"),
    ("firstfocusus", "US"),
    ("wildmangous", "US"),
    # 非 US
    ("firstfocus", "AU"),
    ("talentgeniusau", "AU"),
    ("talentgeniusbr", "BR"),
    ("talentgeniusca", "CA"),
    ("monicaica", "CA"),
    ("codestonede", "DE"),
    ("codestonees", "ES"),
    ("codestonefr", "FR"),
    ("wildmangofr", "FR"),
    ("aibuildgroupgb", "GB"),
    ("talentgeniusuk", "GB"),
    ("wildmangoke", "KE"),
    ("firstfocusnz", "NZ"),
    ("wildmangong", "NG"),
    ("wildmangoza", "ZA"),
    ("thinkingmachinesth", "TH"),
    ("thinkingmachinessg", "SG"),
    ("thinkingmachinesph", "PH"),
]

# ─── Clash API ────────────────────────────────────────────────
def _curl(path, method="GET", data=None):
    url = f"http://localhost{path}"
    cmd = ["curl", "-s", "--unix-socket", CLASH_SOCKET]
    if method != "GET":
        cmd += ["-X", method]
    if data:
        cmd += ["-H", "Content-Type: application/json", "-d", json.dumps(data)]
    cmd.append(url)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    return r.stdout

def _clash_mode():
    raw = _curl("/configs")
    return json.loads(raw).get("mode", "rule")

def _proxy_group():
    mode = _clash_mode()
    return config.get_proxy_group(mode)

def get_current_node():
    raw = json.loads(_curl("/proxies"))
    return raw.get("proxies", {}).get(_proxy_group(), {}).get("now", "?")

def switch_to(node):
    group = _proxy_group()
    _curl(f"/proxies/{quote(group, safe='')}", method="PUT", data={"name": node})

def pick_node(keywords):
    raw = json.loads(_curl("/proxies"))
    proxies = raw.get("proxies", {})
    group = proxies.get(_proxy_group(), {})
    skip = {"Selector", "URLTest", "Fallback", "Direct", "Reject", "Compatible", "Pass"}
    nodes = [n for n in group.get("all", [])
             if proxies.get(n, {}).get("type") not in skip]
    matched = [n for n in nodes for kw in keywords if kw in n]
    return matched[0] if matched else None

# ─── Metadata API ──────────────────────────────────────────────
def get_metadata(code):
    from curl_cffi import requests as cffi_requests
    session = cffi_requests.Session(impersonate="chrome136")
    if PROXY_URL:
        session.proxies = {"https": PROXY_URL, "http": PROXY_URL}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Authorization": f"Bearer {TOKEN}",
    }
    try:
        resp = session.get(
            f"https://chatgpt.com/backend-api/promotions/metadata/{code}?type=promo",
            headers=headers, timeout=15
        )
        data = resp.json()
        return data.get("metadata") or data
    except Exception as e:
        return {"error": str(e)}

# ─── 汇率 ──────────────────────────────────────────────────────
def get_rates():
    try:
        import urllib.request
        resp = urllib.request.urlopen("https://open.er-api.com/v6/latest/USD", timeout=10)
        return json.loads(resp.read())["rates"]
    except:
        return {"USD":1,"GBP":0.73,"EUR":0.85,"AUD":1.38,"CAD":1.37,"BRL":4.92,
                "NZD":1.68,"ZAR":16.39,"NGN":1360,"THB":34,"SGD":1.32,"PHP":56}

def to_usd(amount, ccy, rates):
    if ccy == "USD":
        return round(amount, 2)
    r = rates.get(ccy)
    return round(amount / r, 2) if r else None

# ─── 主逻辑 ────────────────────────────────────────────────────
CURRENCY_SYMBOLS = {
    "USD": "$", "GBP": "£", "EUR": "€", "AUD": "A$", "CAD": "C$",
    "BRL": "R$", "NZD": "NZ$", "ZAR": "R", "NGN": "₦", "THB": "฿", "SGD": "S$", "PHP": "₱",
}

def main(target_cc=None):
    rates = get_rates()
    print(f"{'='*80}")
    print(f"💲 ChatGPT Team 促销码 — 实际价格计算")
    print(f"{'='*80}")
    print(f"  汇率基准: USD 1 | 时间: {datetime.now().strftime('%H:%M:%S')}")
    print()

    results = []

    # 按地区分组
    by_region = {}
    for code, cc in ALL_CODES:
        if target_cc and cc != target_cc:
            continue
        by_region.setdefault(cc, []).append(code)

    last_region = None
    for cc in sorted(by_region.keys()):
        codes = by_region[cc]
        label = REGION_LABELS.get(cc, cc)

        # 切节点
        if cc != last_region:
            keywords = REGION_KEYWORDS.get(cc)
            if keywords:
                node = pick_node(keywords)
                if node:
                    switch_to(node)
                    time.sleep(1)
                    curr = get_current_node()
                    print(f"\n📍 {label} → {curr}")
                else:
                    print(f"\n⚠️  {label} — 无匹配节点，可能失败")
            time.sleep(0.3)
            last_region = cc

        for code in codes:
            base_info = BASE.get(cc, BASE.get("US"))
            if not base_info:
                print(f"\n  {code}: 无 base 价格数据")
                continue

            base_per_seat = base_info["amount"]
            base_ccy = base_info["currency"]
            base_2 = base_per_seat * 2

            meta = get_metadata(code)
            time.sleep(0.5)

            discount = (meta.get("discount") or {}) if not meta.get("error") else {}
            discount_val = discount.get("value")
            discount_ccy = discount.get("currency_code", base_ccy)
            duration = (meta.get("duration") or {}).get("num_periods")

            if discount_val is not None:
                actual = base_2 - discount_val
                actual_usd = to_usd(actual, base_ccy, rates)
                pct = round(discount_val / base_2 * 100)
                actual_str = f"{actual:.2f} {base_ccy}"
                usd_str = f"${actual_usd}" if actual_usd else "?"
            else:
                actual = None
                actual_usd = None
                pct = None
                actual_str = "❌ metadata 失败"
                usd_str = ""

            sym = CURRENCY_SYMBOLS.get(base_ccy, base_ccy + " ")
            print(f"  {code:<23s}  base: {sym}{base_per_seat}/seat ×2={sym}{base_2:.0f}", end="")
            if discount_val is not None:
                print(f"  -{discount_val} = {actual_str}  ≈ ${actual_usd}/月  (-{pct}%)")
            else:
                err = meta.get("error", "空响应")
                print(f"  ❌ {err}")

            results.append({
                "code": code, "region": cc,
                "base_per_seat": base_per_seat, "base_currency": base_ccy,
                "base_2_total": base_2,
                "discount_value": discount_val, "discount_currency": discount_ccy,
                "actual_price": actual, "actual_usd": actual_usd,
                "discount_pct": pct, "duration_months": duration,
            })

    # ─── 汇总表格 ─────────────────────────────────────────────
    print(f"\n\n{'='*80}")
    print("📊 结果汇总")
    print(f"{'='*80}")
    print(f"{'促销码':<25s} {'地区':<4s} {'原价2人':<12s} {'折扣%':<6s} {'实付/月':<14s} {'≈ USD':<8s} {'时长'}")
    print("-" * 80)
    for r in results:
        if r["actual_price"] is not None:
            sym = CURRENCY_SYMBOLS.get(r["base_currency"], "")
            base2 = f"{sym}{r['base_2_total']:.0f}"
            actual = f"{sym}{r['actual_price']:.2f}"
            usd = f"${r['actual_usd']}" if r.get("actual_usd") else "?"
            pct = f"-{r['discount_pct']}%" if r.get("discount_pct") is not None else "?"
            dur = f"{r['duration_months']}m" if r.get("duration_months") else "?"
        else:
            base2 = "?"
            actual = "❌"
            usd = ""
            pct = "?"
            dur = "?"
        print(f"  {r['code']:<23s} {r['region']:<4s} {base2:<12s} {pct:<6s} {actual:<14s} {usd:<8s} {dur}")

    # ─── 保存 ─────────────────────────────────────────────────
    out = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "results": results,
    }
    save_path = os.path.join(config.get_output_dir(), "price_calc_results.json")
    with open(save_path, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\n✅ 已保存: {save_path}")

if __name__ == "__main__":
    target = sys.argv[1].upper() if len(sys.argv) > 1 else None
    main(target)
