"""一键打开 ChatGPT Team 促销码 Stripe 支付页面

自动切换 Clash 节点并生成对应地区的 Stripe checkout URL，在浏览器中打开。

用法:
  python open_stripe.py                    # 打开所有码的 Stripe 页面
  python open_stripe.py GB                 # 只打开指定地区
  python open_stripe.py GB US              # 打开多个地区
  python open_stripe.py --list             # 列出所有可用码
  python open_stripe.py --codes            # 按促销码名打开（自动切节点）
"""
import json, sys, time, subprocess, webbrowser
from urllib.parse import quote
from datetime import datetime

import config

CLASH_SOCKET = config.get_clash_socket()
PROXY_URL = config.get_proxy_url()
TOKEN = config.get_token()

# ─── 地区定义 ────────────────────────────────────────────────

REGIONS = {
    "US": {
        "keywords": ["美国", "🇺🇸"],
        "codes": [
            ("thealloynetwork", "USD", "The Alloy Network", "$30/月"),
            ("alongsideus", "USD", "Alongside", "$30/月"),
            ("monicaius", "USD", "Monica AI", "$30/月"),
            ("talentgeniusus", "USD", "TalentGenius", "$25/月"),
            ("firstfocusus", "USD", "First Focus", "$25/月"),
            ("wildmangous", "USD", "WildMango", "$25/月"),
        ],
    },
    "GB": {
        "keywords": ["英国", "🇬🇧"],
        "codes": [
            ("aibuildgroupgb", "GBP", "AI Build Group", "£18/月"),
            ("talentgeniusuk", "GBP", "TalentGenius", "£18/月"),
        ],
    },
    "AU": {
        "keywords": ["澳洲", "澳大利亚", "🇦🇺"],
        "codes": [
            ("firstfocus", "AUD", "First Focus", "A$45/月"),
            ("talentgeniusau", "AUD", "TalentGenius", "A$35/月"),
        ],
    },
    "DE": {
        "keywords": ["德国", "🇩🇪"],
        "codes": [("codestonede", "EUR", "Codestone", "€15.13/月")],
    },
    "FR": {
        "keywords": ["法国", "🇫🇷"],
        "codes": [
            ("codestonefr", "EUR", "Codestone", "€15.01/月"),
            ("wildmangofr", "EUR", "WildMango", "€21.67/月"),
        ],
    },
    "ES": {
        "keywords": ["西班牙", "🇪🇸"],
        "codes": [("codestonees", "EUR", "Codestone", "€14.89/月")],
    },
    "CA": {
        "keywords": ["加拿大", "🇨🇦"],
        "codes": [
            ("talentgeniusca", "CAD", "TalentGenius", "C$34/月"),
            ("monicaica", "CAD", "Monica AI", "C$26/月"),
        ],
    },
    "BR": {
        "keywords": ["巴西", "🇧🇷"],
        "codes": [("talentgeniusbr", "BRL", "TalentGenius", "R$130/月")],
    },
    "NZ": {
        "keywords": ["新西兰", "🇳🇿"],
        "codes": [("firstfocusnz", "NZD", "First Focus", "NZ$41/月")],
    },
    "KE": {
        "keywords": ["肯尼亚", "🇰🇪"],
        "codes": [("wildmangoke", "USD", "WildMango", "$23.20/月")],
    },
    "ZA": {
        "keywords": ["南非", "🇿🇦"],
        "codes": [("wildmangoza", "ZAR", "WildMango", "R400/月")],
    },
    "NG": {
        "keywords": ["尼日利亚", "🇳🇬"],
        "codes": [("wildmangong", "NGN", "WildMango", "₦33,600/月")],
    },
    "TH": {
        "keywords": ["泰国", "🇹🇭"],
        "codes": [("thinkingmachinesth", "THB", "Thinking Machines", "฿561/月")],
    },
    "SG": {
        "keywords": ["新加坡", "🇸🇬"],
        "codes": [("thinkingmachinessg", "SGD", "Thinking Machines", "S$27.25/月")],
    },
    "PH": {
        "keywords": ["菲律宾", "🇵🇭"],
        "codes": [("thinkingmachinesph", "PHP", "Thinking Machines", "₱1,345/月")],
    },
}

REGION_LABELS = {
    "US": "🇺🇸 美国", "GB": "🇬🇧 英国", "AU": "🇦🇺 澳洲",
    "DE": "🇩🇪 德国", "FR": "🇫🇷 法国", "ES": "🇪🇸 西班牙",
    "CA": "🇨🇦 加拿大", "BR": "🇧🇷 巴西", "NZ": "🇳🇿 新西兰",
    "KE": "🇰🇪 肯尼亚", "ZA": "🇿🇦 南非", "NG": "🇳🇬 尼日利亚",
    "TH": "🇹🇭 泰国", "SG": "🇸🇬 新加坡", "PH": "🇵🇭 菲律宾",
}

# ─── 工具函数 ────────────────────────────────────────────────

def _clash_api(path, method="GET", data=None):
    url = f"http://localhost{path}"
    cmd = ["curl", "-s", "--unix-socket", CLASH_SOCKET]
    if method != "GET":
        cmd += ["-X", method]
    if data:
        cmd += ["-H", "Content-Type: application/json", "-d", json.dumps(data)]
    cmd.append(url)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    if r.returncode != 0 and method != "PUT":
        print(f"  ⚠ Clash API 错误: {r.stderr}")
    try:
        return json.loads(r.stdout) if r.stdout.strip() else {}
    except json.JSONDecodeError:
        return {}


def _proxy_group():
    raw = _clash_api("/configs")
    mode = raw.get("mode", "rule")
    return "GLOBAL" if mode == "global" else config.get_proxy_group(mode)


def get_all_nodes():
    raw = _clash_api("/proxies")
    proxies = raw.get("proxies", {})
    group = proxies.get(_proxy_group(), {})
    current = group.get("now", "?")
    nodes = []
    for name in group.get("all", []):
        info = proxies.get(name)
        if info and info.get("type") not in (
            "Selector", "URLTest", "Fallback", "Direct", "Reject", "Compatible", "Pass",
        ):
            nodes.append(name)
    return nodes, current


def match_nodes(nodes, keywords):
    return [n for n in nodes for kw in keywords if kw in n]


def switch_node(node_name):
    group_name = _proxy_group()
    _clash_api(f"/proxies/{quote(group_name, safe='')}", method="PUT", data={"name": node_name})
    time.sleep(1.5)


def get_stripe_url(code, country, currency):
    """调用 checkout API 生成 Stripe URL"""
    from curl_cffi import requests as cffi_requests

    session = cffi_requests.Session(impersonate="chrome136")
    if PROXY_URL:
        session.proxies = {"https": PROXY_URL, "http": PROXY_URL}

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "plan_name": "chatgptteamplan",
        "team_plan_data": {
            "workspace_name": f"Team{int(time.time())}",
            "price_interval": "month",
            "seat_quantity": 2,
        },
        "billing_details": {"country": country, "currency": currency},
        "promo_code": code,
        "cancel_url": "https://chatgpt.com/",
        "checkout_ui_mode": "hosted",
    }
    try:
        resp = session.post(
            "https://chatgpt.com/backend-api/payments/checkout",
            json=payload, headers=headers, timeout=20,
        )
        data = resp.json()
        url = data.get("url", "")
        return url if url.startswith("https://") else None
    except Exception as e:
        print(f"  ❌ checkout API 错误: {e}")
        return None


# ─── 主逻辑 ──────────────────────────────────────────────────

def cmd_list():
    """列出所有可用码"""
    print(f"\n{'='*60}")
    print(f"ChatGPT Team 促销码列表（共 25 个码，覆盖 15 个地区）")
    print(f"{'='*60}")

    for rc in sorted(REGIONS.keys()):
        region = REGIONS[rc]
        label = REGION_LABELS.get(rc, rc)
        print(f"\n{label}:")
        for code, _currency, company, price in region["codes"]:
            price_str = f" 实付 {price}" if price != "—" else " 价格待查"
            print(f"  {code:<30s} {company:<20s}{price_str}")


def cmd_open(region_codes=None, code_names=None):
    """打开 Stripe 页面"""
    if not TOKEN or TOKEN.startswith("eyJ") is False:
        print("❌ 错误: 请先在 config.toml 中配置 accessToken")
        sys.exit(1)

    nodes, _ = get_all_nodes()

    # 确定要处理的地区
    targets = []
    if code_names:
        # 按码名查找
        code_to_region = {}
        for rc, region in REGIONS.items():
            for code, currency, company, price in region["codes"]:
                code_to_region[code] = (rc, currency, company, price)
        for name in code_names:
            if name in code_to_region:
                rc, currency, company, price = code_to_region[name]
                targets.append((rc, [(name, currency, company, price)]))
            else:
                print(f"  ⚠ 未知码: {name}")
    elif region_codes:
        for rc in region_codes:
            if rc in REGIONS:
                targets.append((rc, REGIONS[rc]["codes"]))
            else:
                print(f"  ⚠ 未知地区: {rc}")
    else:
        for rc in sorted(REGIONS.keys()):
            targets.append((rc, REGIONS[rc]["codes"]))

    print(f"\n{'='*60}")
    print(f"🚀 打开 Stripe 支付页面 — {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}")

    all_urls = []

    for rc, codes in targets:
        region = REGIONS[rc]
        label = REGION_LABELS.get(rc, rc)
        keywords = region["keywords"]

        # 查找并切换节点（US 码不需要切）
        if rc == "US":
            matched = match_nodes(nodes, keywords)
            if matched:
                print(f"\n📍 {label}")
                switch_node(matched[0])
        else:
            matched = match_nodes(nodes, keywords)
            if not matched:
                print(f"\n⚠ {label} — 没有找到对应节点，跳过")
                continue
            print(f"\n📍 {label} — 切换到 {matched[0]}")
            switch_node(matched[0])

        for code, currency, company, price in codes:
            print(f"  🔗 {code:<30s} ", end="", flush=True)
            url = get_stripe_url(code, rc if rc != "US" else rc, currency)
            if url:
                print(f"✅ 已打开")
                webbrowser.open(url)
                all_urls.append((code, rc, url, price))
                time.sleep(0.5)
            else:
                print(f"❌ 生成失败")

    # 保存 URL
    if all_urls:
        save_path = "stripe_urls.txt"
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(f"ChatGPT Team Promo Stripe URLs — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write(f"共 {len(all_urls)} 个可用码\n\n")
            for code, rc, url, price in all_urls:
                label = REGION_LABELS.get(rc, rc)
                f.write(f"{code} [{label}] 实付 {price}\n{url}\n\n")
        print(f"\n✅ URL 已保存到 {save_path}")


# ─── 入口 ────────────────────────────────────────────────────

def print_usage():
    print(__doc__)


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args or "--help" in args or "-h" in args:
        print_usage()
        sys.exit(0)

    if "--list" in args:
        cmd_list()
        sys.exit(0)

    if args[0] == "--codes":
        cmd_open(code_names=args[1:])
        sys.exit(0)

    # 默认：按地区码打开
    valid_regions = [rc for rc in args if rc.upper() in REGIONS]
    if valid_regions:
        cmd_open(region_codes=[r.upper() for r in valid_regions])
    else:
        print(f"未知参数: {args}")
        print_usage()
