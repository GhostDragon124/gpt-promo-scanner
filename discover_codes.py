#!/usr/bin/env python3
"""ChatGPT Team 促销码大规模发现工具

对指定国家/地区，批量生成候选人名并快速验证。

用法:
  python discover_codes.py GB                    # 批量发现英国码
  python discover_codes.py GB --auto-scan        # 发现后自动切节点验证价格
  python discover_codes.py GB --preview          # 预览候选码列表（不验证）
  python discover_codes.py GB --code-only        # 只输出有效码名（每行一个）
  python discover_codes.py --list                # 列出支持的国家
"""
import json
import os
import re
import sys
import time
from datetime import datetime

import config

OUTPUT_DIR = config.get_output_dir()

# ─── 国家定义 ────────────────────────────────────────────────

COUNTRIES = {
    "GB": {"name": "英国", "cc": "gb", "currency": "GBP"},
    "US": {"name": "美国", "cc": "us", "currency": "USD"},
    "AU": {"name": "澳洲", "cc": "au", "currency": "AUD"},
    "CA": {"name": "加拿大", "cc": "ca", "currency": "CAD"},
    "DE": {"name": "德国", "cc": "de", "currency": "EUR"},
    "FR": {"name": "法国", "cc": "fr", "currency": "EUR"},
    "ES": {"name": "西班牙", "cc": "es", "currency": "EUR"},
    "IT": {"name": "意大利", "cc": "it", "currency": "EUR"},
    "NL": {"name": "荷兰", "cc": "nl", "currency": "EUR"},
    "IE": {"name": "爱尔兰", "cc": "ie", "currency": "EUR"},
    "NZ": {"name": "新西兰", "cc": "nz", "currency": "NZD"},
    "BR": {"name": "巴西", "cc": "br", "currency": "BRL"},
    "ZA": {"name": "南非", "cc": "za", "currency": "ZAR"},
    "KE": {"name": "肯尼亚", "cc": "ke", "currency": "USD"},
    "NG": {"name": "尼日利亚", "cc": "ng", "currency": "NGN"},
    "JP": {"name": "日本", "cc": "jp", "currency": "JPY"},
    "IN": {"name": "印度", "cc": "in", "currency": "INR"},
    "SG": {"name": "新加坡", "cc": "sg", "currency": "SGD"},
    "KR": {"name": "韩国", "cc": "kr", "currency": "KRW"},
    "SE": {"name": "瑞典", "cc": "se", "currency": "SEK"},
    "NO": {"name": "挪威", "cc": "no", "currency": "NOK"},
    "DK": {"name": "丹麦", "cc": "dk", "currency": "DKK"},
    "FI": {"name": "芬兰", "cc": "fi", "currency": "EUR"},
    "CH": {"name": "瑞士", "cc": "ch", "currency": "CHF"},
    "AT": {"name": "奥地利", "cc": "at", "currency": "EUR"},
    "BE": {"name": "比利时", "cc": "be", "currency": "EUR"},
    "MX": {"name": "墨西哥", "cc": "mx", "currency": "MXN"},
    "AE": {"name": "阿联酋", "cc": "ae", "currency": "AED"},
    "SA": {"name": "沙特", "cc": "sa", "currency": "SAR"},
    "IL": {"name": "以色列", "cc": "il", "currency": "ILS"},
    "TR": {"name": "土耳其", "cc": "tr", "currency": "TRY"},
    "PL": {"name": "波兰", "cc": "pl", "currency": "PLN"},
    "CZ": {"name": "捷克", "cc": "cz", "currency": "CZK"},
    "RO": {"name": "罗马尼亚", "cc": "ro", "currency": "RON"},
}


# ─── 公司名生成 ──────────────────────────────────────────────

def normalize(name):
    """生成公司名变体"""
    name = name.strip()
    base = re.sub(r'[\s\-_./,&+\']', '', name).lower()
    variants = {base}
    if base.startswith('the'):
        variants.add(base[3:])
    words = re.split(r'[\s\-_./,&+\']+', name.lower())
    if len(words) > 1:
        variants.add(''.join(w[0] for w in words if w))
        variants.add(words[0])
        variants.add(''.join(words[:2]))
    for suffix in ['technologies', 'services', 'solutions', 'group', 'international',
                   'consulting', 'systems', 'software', 'security', 'labs', 'digital',
                   'global', 'partners', 'limited', 'ltd', 'corp', 'inc']:
        if base.endswith(suffix):
            variants.add(base[:-len(suffix)])
    seen = set()
    result = []
    for v in sorted(variants):
        if v and v not in seen:
            seen.add(v)
            result.append(v)
    return result


# ============================================================
# 已知已验证的 Base Name（在所有国家中有效的）
# ============================================================
KNOWN_BASES = [
    "aibuildgroup", "wildmango", "firstfocus", "codestone",
    "talentgenius", "thealloynetwork", "alongside", "monicai",
    "thinkingmachines",
    "trintel", "noranalytos", "infoseekai", "datroai", "vouchapi",
]

# ============================================================
# UK AI SaaS / AI 工具公司（新增！）
# ============================================================
# 基于已知有效码的公司画像分析：
#   - AI SaaS 工具（TalentGenius, Monica AI, Alongside 模式）
#   - 中小型，有自己的 AI 产品，面向 SMB
# ============================================================
UK_AI_COMPANIES = [
    # ── UK HR/AI Recruiting Tech (20) ──
    "Beamery", "Metaview", "Jack & Jill AI", "Huzzle",
    "Tribepad", "Clevry", "ThriveMap", "Applied",
    "Rungway", "Perkbox", "Pip Decks", "Reward Gateway",
    "Arctic Shores", "Sova", "Fasthr",
    "Detech", "Jobbio", "SpottedHerMes",
    "Cognisium", "SnapHire",

    # ── UK Marketing/AdTech AI (35) ──
    "Searchable", "Flick AI", "Decima2", "Joggle",
    "Adzooma", "BrightBid", "Brandwatch", "Peerius",
    "Qubit", "Yieldify", "Ozone", "Pure360",
    "RedEye", "Echobox", "Pulsar", "Chattermill",
    "Ometria", "SmartFocus", "Conversocial", "Spektrix",
    "Piwik PRO", "Brand24", "BuzzRadar", "Meltwater",
    "Determ", "NewsWhip", "Talkwalker", "TrendHERO",
    "Kamma", "Hubb", "Signal Media", "Digimind",
    "Taggify", "Percolate", "TrendKite",

    # ── UK Content/Creative AI (25) ──
    "Shothik AI", "Wordsmith AI", "Starwriters", "First Concepts",
    "ContentCal", "Lumen5", "FilmBot", "Jukedeck",
    "Sonantic", "Papercup", "SpeechKit", "Sonix",
    "Krisp", "Murf", "Respeecher", "Haiper",
    "InVideo", "Pictory", "OpusClip", "Type Studio",
    "Audlent", "Speechmatics", "AudioTelligence",
    "AI Music", "Boomy",

    # ── UK Fintech/Accounting AI (35) ──
    "Cleo", "Pento", "Menna AI", "Marloo",
    "Swoop", "Fluidly", "Pulse", "Countingup",
    "Coconut", "FreeAgent", "Crunch", "TaxScouts",
    "Previse", "9fin", "DueCourse", "iwoca",
    "MarketFinance", "Tide", "Monese", "TransferGo",
    "WorldRemit", "Azimo", "Currencycloud", "TrueLayer",
    "Chip", "Plum", "Moneybox", "Wealthify",
    "Trading 212", "Freetrade",
    "Revolut", "Monzo", "Starling", "OakNorth",
    "Kroo",

    # ── UK Customer Service/Sales AI (20) ──
    "Elyos AI", "Ascendea", "PolyAI", "DigitalGenius",
    "Netomi", "Crisp", "Olark", "HelpShift",
    "Astound", "Elevio", "Gorgias", "Trengo",
    "Chaport", "Intercom", "Freshchat",
    "Ada", "Zendesk", "Freshdesk", "Cobrowser",
    "Customer IO",

    # ── UK Legal AI (18) ──
    "Luminance", "ThoughtRiver", "Definely", "Juro",
    "Genie AI", "Legl", "Wavelength Law", "Netlaw",
    "Avoka", "Eccobridge", "ClauseBase", "Lawhive",
    "Robin AI", "Jaxon", "Della",
    "Spellbook", "Alexi", "Paxton AI",

    # ── UK EdTech AI (18) ──
    "CENTURY Tech", "Sparx", "Seneca", "Tassomai",
    "Pi-Top", "Microbit", "BibliU", "Perlego",
    "Kortext", "MyTutor", "Tutorful", "Atom Learning",
    "EdPlace", "Third Space Learning", "Studiosity",
    "Kano Computing", "SAM Labs", "Natterhub",

    # ── UK Healthcare/Life Sciences AI (20) ──
    "Cera Care", "Kheiron Medical", "Medopad",
    "Skin Analytics", "Optellum", "PatchAi", "Healx",
    "Relation", "MindFoundry", "Kortical", "RapidBird",
    "AI Build", "POKit", "Binfluencer",
    "Owkin", "Ibex", "Pimloc",
    "Infogrid", "ChAI", "Zegami",

    # ── UK Data/Analytics AI (25) ──
    "Seldon", "Monolith", "Diffblue", "SignalBox",
    "Streetbees", "Preamble", "Thought Machine",
    "TheAX", "Mapify", "Loc AI", "Quantexa",
    "Featurespace", "Onfido", "Tessian",
    "StoryStream", "Boomtrain", "Kaskada", "RavenPack",
    "Signal Media", "DataSift",
    "GeoPhy", "StatusToday", "Artificial Labs",
    "Concirrus", "nPlan",

    # ── UK Cybersecurity AI (15) ──
    "Geordie AI", "Panaseer", "Egress", "Garrison",
    "ZoneFox", "Glasswall", "RedSocks", "Senseon",
    "Snyk", "Cybereason", "Blue Prism",
    "Traceable", "Darklantern", "Auth0", "Okta",

    # ── UK Property/Real Estate AI (12) ──
    "Mashroom", "Nested", "Boomin", "Goodlord",
    "Ozo", "Plentific", "Fixflo", "Kestrix",
    "Hubble", "Essensys", "Density", "Locale",

    # ── UK AI — OpenAI 生态线索 (5) ──
    "MDJM", "Gecco", "Tractable",
    "Satavia", "Satus",

    # ── UK Productivity/Collaboration AI (18) ──
    "Granola", "SolveAI", "Attio",
    "Zero One Creative", "Dataline Labs",
    "Capsule", "Pipeline CRM", "OnePageCRM",
    "Teamgate", "NetHunt", "Freshsales",
    "Close CRM", "Copper", "Nimble", "Insightly",
    "Blue Prism", "Tray.io", "Paddle",

    # ── UK 更多 AI/科技公司 (10) ──
    "Made Tech", "Kainos", "Kin + Carta",
    "AND Digital", "Scott Logic", "Version 1",
    "Cloudreach", "Appsbroker", "Ancoris",
    "Do IT",
]


# ============================================================
# UK 特定公司列表 — 大规模的
# ============================================================

def build_uk_candidates(dedup_set=None):
    """生成英国地区的候选人名列表

    dedup_set: 已有候选集，生成的候选会自动排除其中的项
    """
    names = set()

    # 1. 已验证的 Base Name — 同时尝试 +gb 和 +uk
    for b in KNOWN_BASES:
        names.add(f"{b}gb")
        names.add(f"{b}uk")     # talentgeniusuk 证明这个模式存在

    # 2. 新的 UK AI 公司
    for name in UK_AI_COMPANIES:
        variants = normalize(name)
        for v in variants:
            if len(v) < 3:  # 太短的变体（2字母缩写）不太可能是有效码
                continue
            names.add(v + "gb")
            names.add(v + "uk")
            names.add(v + "couk")
            names.add(v)

    # 3. UK MSP / IT 服务公司（旧的列表）
    uk_companies = [
        # 大型 UK MSP
        "Computacenter", "Softcat", "CDW UK", "Insight UK",
        "XMA", "Trustmarque", "Wavenet", "Alternative Networks",
        "Daisy Group", "Claranet", "Maintel", "Node4",
        "M247", "GCI", "Redwood", "Six Degrees",
        "Exponential-e", "ANS Group", "UKFast", "KCOM",
        "Jisc", "Kerv", "Boxxe", "SCC",
        "Mitel UK", "Azzure IT", "Whitegold", "Baltimore",
        # UK 云/技术公司
        "Rackspace UK", "Endava", "Avanade", "Thoughtworks",
        "Capgemini UK", "Elastic", "Palantir", "Sophos",
        "Darktrace", "DeepMind", "Synthesia", "Stability",
        "Sage", "InterSystems", "MicroFocus", "OpenText",
        # UK AI/科技创业公司
        "Wayve", "Graphcore", "Synthesia", "Huma",
        "Babylon", "BenevolentAI", "Exscientia", "DeepMind",
        "InstaDeep", "Faculty", "Centauric", "SignalAI",
        # UK 院校/非营利
        "UCL", "Imperial", "Cambridge", "Oxford", "Edinburgh",
        # UK 电信/连接
        "BT Group", "Vodafone UK", "EE", "Sky UK", "TalkTalk",
        "Virgin Media", "Three UK", "G.Network", "Hyperoptic",
        "CityFibre", "Toob", "CommunityFibre",
        # CRN UK Top VAR/MSP
        "Advania", "Apogee", "Bytes", "CHP", "CKS", "ClerksWell",
        "Content+Cloud", "CPS", "Creative ITC", "Dabber",
        "Datalink", "EACS", "Eagle", "Epaton", "Eqalix",
        "Excel", "Express", "Extreme", "Exsel", "FCS",
        "Focus", "Foursys", "Goss", "HCS", "Heath", "Hyve",
        "Intelligent", "Intercity", "Involeo", "IPG",
        "Jola", "Jumar", "Khipu", "Krystal", "Liverton",
        "Longira", "Lucidica", "Magnet", "Mako", "Mansfield",
        "Marval", "MCSA", "Mint", "Morris", "Nasstar",
        "Neos", "Network", "Nexus", "Nottingham", "Ocs",
        "Onecom", "Onetech", "Onyx", "Open", "Orange",
        "Osiris", "Osw", "Oxygen", "Parity", "PCS",
        "Peak", "PeterConnects", "Pinnacle", "Portland",
        "Prodec", "Pulsant", "Qcom", "Qolcom", "RedMoor",
        "Reply", "Risual", "Rock", "Roke", "Rydal",
        "Saepio", "Saints", "SCC", "Sentinel", "Severn",
        "Sharptext", "Silverbug", "Simply", "Six",
        "Softcat", "Solnet", "Sound", "Sparta", "Splash",
        "Storm", "Sydney", "Syscap", "Systems", "Talus",
        "Tata", "TCS", "Techdata", "Telent", "Telsoc",
        "Thomas", "Tiscali", "TP", "Ubertas", "UKFast",
        "Uniden", "Vayant", "Versutile", "Virgin", "Vorboss",
        "Vox", "Wavenet", "Westcoast", "Wifinity", "XMA",
        "Zynstra",
    ]

    for name in uk_companies:
        variants = normalize(name)
        for v in variants:
            names.add(v + "gb")
            names.add(v)
            names.add(v + "couk")
            names.add(v + "uk")

    # 去重：去掉已在 dedup_set 中的码
    if dedup_set:
        old_count = len(names)
        names -= dedup_set
        removed = old_count - len(names)
        if removed:
            print(f"  🔄 去重: 移除 {removed} 个已测码, 剩余 {len(names)} 个新候选")
        else:
            print(f"  ✅ 无重复候选")

    # 过滤：去掉太短的（至少 4 字符）和纯国家码
    names = {n for n in names if len(n) >= 4}

    return sorted(names)


# ============================================================
# 其他国家的候选列表（可扩展）
# ============================================================

def _build_old_only():
    """只生成旧版 UK 候选码列表（用于去重参考）"""
    # 重现旧的 build_uk_candidates() 逻辑
    names = set()
    for b in KNOWN_BASES:
        names.add(f"{b}gb")

    uk_companies = [  # 老的公司列表（不含 UK_AI_COMPANIES）
        "Computacenter", "Softcat", "CDW UK", "Insight UK",
        "XMA", "Trustmarque", "Wavenet", "Alternative Networks",
        "Daisy Group", "Claranet", "Maintel", "Node4",
        "M247", "GCI", "Redwood", "Six Degrees",
        "Exponential-e", "ANS Group", "UKFast", "KCOM",
        "Jisc", "Kerv", "Boxxe", "SCC",
        "Mitel UK", "Azzure IT", "Whitegold", "Baltimore",
        "Rackspace UK", "Endava", "Avanade", "Thoughtworks",
        "Capgemini UK", "Elastic", "Palantir", "Sophos",
        "Darktrace", "DeepMind", "Synthesia", "Stability",
        "Sage", "InterSystems", "MicroFocus", "OpenText",
        "Wayve", "Graphcore", "Synthesia", "Huma",
        "Babylon", "BenevolentAI", "Exscientia", "DeepMind",
        "InstaDeep", "Faculty", "Centauric", "SignalAI",
        "UCL", "Imperial", "Cambridge", "Oxford", "Edinburgh",
        "BT Group", "Vodafone UK", "EE", "Sky UK", "TalkTalk",
        "Virgin Media", "Three UK", "G.Network", "Hyperoptic",
        "CityFibre", "Toob", "CommunityFibre",
        "Advania", "Apogee", "Bytes", "CHP", "CKS", "ClerksWell",
        "Content+Cloud", "CPS", "Creative ITC", "Dabber",
        "Datalink", "EACS", "Eagle", "Epaton", "Eqalix",
        "Excel", "Express", "Extreme", "Exsel", "FCS",
        "Focus", "Foursys", "Goss", "HCS", "Heath", "Hyve",
        "Intelligent", "Intercity", "Involeo", "IPG",
        "Jola", "Jumar", "Khipu", "Krystal", "Liverton",
        "Longira", "Lucidica", "Magnet", "Mako", "Mansfield",
        "Marval", "MCSA", "Mint", "Morris", "Nasstar",
        "Neos", "Network", "Nexus", "Nottingham", "Ocs",
        "Onecom", "Onetech", "Onyx", "Open", "Orange",
        "Osiris", "Osw", "Oxygen", "Parity", "PCS",
        "Peak", "PeterConnects", "Pinnacle", "Portland",
        "Prodec", "Pulsant", "Qcom", "Qolcom", "RedMoor",
        "Reply", "Risual", "Rock", "Roke", "Rydal",
        "Saepio", "Saints", "SCC", "Sentinel", "Severn",
        "Sharptext", "Silverbug", "Simply", "Six",
        "Softcat", "Solnet", "Sound", "Sparta", "Splash",
        "Storm", "Sydney", "Syscap", "Systems", "Talus",
        "Tata", "TCS", "Techdata", "Telent", "Telsoc",
        "Thomas", "Tiscali", "TP", "Ubertas", "UKFast",
        "Uniden", "Vayant", "Versutile", "Virgin", "Vorboss",
        "Vox", "Wavenet", "Westcoast", "Wifinity", "XMA",
        "Zynstra",
    ]

    for name in uk_companies:
        variants = normalize(name)
        for v in variants:
            names.add(v + "gb")
            names.add(v)
            names.add(v + "couk")
            names.add(v + "uk")

    return sorted(names)


def build_candidates(country_code, dedup_set=None):
    """为指定国家生成候选人名"""
    if country_code == "GB":
        return build_uk_candidates(dedup_set)

    if country_code == "TR":
        return _build_tr_candidates(dedup_set)

    # 默认：UK bases × 国家码
    names = set()
    for b in KNOWN_BASES:
        names.add(f"{b}{country_code.lower()}")
    return sorted(names)


def _build_tr_candidates(dedup_set=None):
    """加载土耳其公司候选码（从外部文件）"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    tr_file = os.path.join(base_dir, "turkish_candidates.txt")
    names = set()
    if os.path.exists(tr_file):
        with open(tr_file) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("//"):
                    continue
                # 格式: "公司名 → 候选码" 或者直接 "候选码"
                if "→" in line:
                    code = line.split("→")[-1].strip()
                else:
                    code = line.strip()
                if code and len(code) >= 4:
                    names.add(code)
    else:
        # 后备：从 KNOWN_BASES 生成 tr 码
        for b in KNOWN_BASES:
            names.add(f"{b}tr")
    # 去重
    if dedup_set:
        names -= dedup_set
    return sorted(names)


# ============================================================
# 全矩阵交叉扫描
# ============================================================

CROSS_DEDUP_FILE = os.path.join(OUTPUT_DIR, ".candidates_cross_old.txt")


def build_cross_matrix():
    """生成全矩阵交叉候选：8 base × 48 国家码"""
    names = set()

    # 总是尝试 base + countrycode
    for b in KNOWN_BASES:
        for cc in COUNTRIES:
            suffix = cc.lower()
            names.add(f"{b}{suffix}")
            names.add(b)  # 也试无后缀（如 firstfocus）

    # 加载去重集
    dedup = _load_cross_dedup()
    if dedup:
        old_count = len(names)
        names -= dedup
        print(f"  🔄 去重: 移除 {old_count - len(names)} 个已测码, 剩余 {len(names)} 个新候选")

    names = {n for n in names if len(n) >= 4}
    return sorted(names)


def _load_cross_dedup():
    """加载所有已知的跨国家已测候选"""
    tested = set()

    # 1. 从 cross dedup 文件（如果存在）
    if os.path.exists(CROSS_DEDUP_FILE):
        with open(CROSS_DEDUP_FILE) as f:
            tested.update(line.strip() for line in f if line.strip())

    # 2. 从已有 discovery 结果文件收集
    for fname in os.listdir(OUTPUT_DIR):
        if fname.startswith("discovery_") and fname.endswith(".json"):
            path = os.path.join(OUTPUT_DIR, fname)
            try:
                with open(path) as f:
                    data = json.load(f)
                for key in ("eligible", "exists"):
                    for code in data.get(key, []):
                        tested.add(code)
                for code in data.get("errors", {}):
                    tested.add(code)
            except Exception:
                pass

    return tested if tested else None


# ─── Token ───────────────────────────────────────────────────

def _load_token():
    return config.get_token()


# ─── Token 验证（用 Session API，不依赖促销码）────


def validate_token():
    """验证 accessToken 是否仍然有效

    使用 Session API (/api/auth/session) 检测 token 有效性，不依赖任何促销码。
    若 Session API 不通，再用 eligibility API 验证一次确认。
    必须在每次批量扫描前调用，否则过期 token 会导致全部 false negative。
    """
    from curl_cffi import requests as cffi_requests

    token = _load_token()
    session = cffi_requests.Session(impersonate="chrome136")
    proxy_url = config.get_proxy_url()
    session.proxies = {"https": proxy_url, "http": proxy_url}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }

    # 方法1: Session API（最可靠，不依赖任何促销码）
    try:
        resp = session.get("https://chatgpt.com/api/auth/session", headers=headers, timeout=10)
        data = resp.json()
        if data.get("user"):
            return  # Token 有效
    except Exception:
        pass

    # 方法2: 用 dummy 码调 eligibility API 辅助确认
    # Session API 可能在其他场景返回空 user，但 eligibility 仍可用
    try:
        url = "https://chatgpt.com/backend-api/promotions/eligibility/_dummy_token_check_000?type=promo"
        resp = session.get(url, headers=headers, timeout=10)
        data = resp.json()
        if "error" not in data:
            return  # eligibility API 接受了 token → 有效
    except Exception:
        pass

    # 两个方法都失败 → token 无效
    print(f"\n{'='*60}")
    print(f"❌ Token 验证失败 — accessToken 已过期或无效")
    print(f"{'='*60}")
    print(f"\n  ⚠️  继续扫描将全部返回 invalid_code 或 401 (false negative)")
    print(f"\n  🔧 解决方法:")
    print(f"     1. 浏览器登录 chatgpt.com")
    print(f"     2. F12 → Console")
    print(f"     3. 执行:")
    print(f"        const s = await (await fetch('/api/auth/session')).json();")
    print(f"        console.log(s.accessToken);")
    print(f"     4. 复制新 token 到 config.toml 或环境变量 OPENAI_TOKEN")
    print(f"{'='*60}\n")
    sys.exit(1)


def batch_check(candidates, delay=0.2):
    """批量验证码是否存在（用 eligibility API，不切节点也能判断存在性）

    参数:
        candidates: 待验证码列表
        delay: 请求间隔秒数

    返回: {code: "EXISTS"|"ELIGIBLE"|"not_found"|"error"}
    """
    # 先验证 token 是否有效（用 Session API，不依赖促销码）
    validate_token()

    from curl_cffi import requests as cffi_requests

    token = _load_token()
    if not token:
        print("❌ 无法读取 TOKEN")
        sys.exit(1)

    session = cffi_requests.Session(impersonate="chrome136")
    proxy_url = config.get_proxy_url()
    session.proxies = {"https": proxy_url, "http": proxy_url}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }

    results = {}
    total = len(candidates)
    found = 0

    print(f"\n🔍 批量验证 {total} 个候选码...")
    print(f"{'='*60}")

    for i, code in enumerate(candidates, 1):
        try:
            url = f"https://chatgpt.com/backend-api/promotions/eligibility/{code}?type=promo"
            resp = session.get(url, headers=headers, timeout=10)
            data = resp.json()

            if data.get("is_eligible"):
                results[code] = "ELIGIBLE"
                found += 1
                print(f"  ✅ [{i:3d}/{total}] {code:<35s} ELIGIBLE!")
            else:
                reason = data.get("ineligible_reason", {})
                rc = reason.get("code", "")
                if rc == "user_not_eligible":
                    results[code] = "EXISTS"
                    found += 1
                    print(f"  🔶 [{i:3d}/{total}] {code:<35s} EXISTS")
                elif rc == "invalid_code":
                    results[code] = "not_found"
                else:
                    results[code] = f"unknown({rc})"
                    if rc:
                        print(f"  ❓ [{i:3d}/{total}] {code:<35s} {rc}")
        except Exception as e:
            results[code] = "error"
            print(f"  ❌ [{i:3d}/{total}] {code:<35s} error: {str(e)[:40]}")

        # 进度提示
        if (i % 50 == 0):
            print(f"  ... {i}/{total}, found {found} so far")

        time.sleep(delay)

    return results


# ─── 验证价格（需要切节点）──────────────────────────────────

def verify_prices(found_codes, country_code):
    """对已发现的有效码，切到对应节点验证价格"""
    cc = country_code.lower()
    info = COUNTRIES.get(country_code, {})

    from auto_scan import (
        switch_to, list_nodes, get_current_node, get_clash_mode,
        try_checkout, fetch_metadata, extract_price_info,
        get_base_checkout, format_price_line, format_usd_line,
    )

    cur, nodes = list_nodes()
    region_keywords = {
        "GB": ["英国", "🇬🇧"],
        "US": ["美国", "🇺🇸"],
        # 扩展...
    }
    keywords = region_keywords.get(country_code, [country_code])

    matched = [n for n in nodes for kw in keywords if kw in n]
    if not matched:
        print(f"\n⚠️  找不到 {country_code} 节点，跳过价格验证")
        return found_codes

    print(f"\n{'='*60}")
    print(f"🔄 切到 {country_code} 节点验证价格")
    print(f"{'='*60}")
    switch_to(matched[0])
    time.sleep(0.5)
    print(f"  当前节点: {get_current_node()}")

    enriched = []
    for entry in found_codes:
        code = entry["code"]
        print(f"\n  🔄 {code} ...", end=" ", flush=True)

        try:
            country = info.get("name", country_code)
            currency = info.get("currency", "USD")
            url, status, err, _ = try_checkout(code, country_code, currency)
            if not url:
                print(f"❌ checkout失败: {str(err)[:50]}")
                enriched.append(entry)
                continue

            print("checkout OK", end=", ", flush=True)
            time.sleep(0.3)

            meta = fetch_metadata(code)
            time.sleep(0.3)

            base = get_base_checkout(country_code, currency)
            pi = extract_price_info(meta, base)

            if pi:
                pl = format_price_line(pi)
                usd = format_usd_line(pi)
                print(f"{pl} ({usd})")
            else:
                print("无折扣信息")

            entry.update({
                "stripe_url": url,
                "price_info": pi,
            })
        except Exception as e:
            print(f"❌ error: {str(e)[:50]}")

        enriched.append(entry)
        time.sleep(0.5)

    return enriched


# ─── 入口 ────────────────────────────────────────────────────

DEDUP_FILE = os.path.join(OUTPUT_DIR, ".candidates_gb_old.txt")


def _load_prev_candidates():
    """加载之前批量验证过的候选码列表，用于去重"""
    if os.path.exists(DEDUP_FILE):
        with open(DEDUP_FILE) as f:
            return {line.strip() for line in f if line.strip()}
    return None


def _save_prev_candidates(candidates):
    """保存候选码列表供以后去重"""
    with open(DEDUP_FILE, "w") as f:
        for c in candidates:
            f.write(c + "\n")


def main():
    if "--list" in sys.argv:
        print("支持的国家:")
        for cc, info in sorted(COUNTRIES.items()):
            print(f"  {cc}  {info['name']}  ({info['currency']})")
        return

    auto_scan = "--auto-scan" in sys.argv
    preview = "--preview" in sys.argv
    code_only = "--code-only" in sys.argv
    gen_old = "--gen-old" in sys.argv

    # ── --cross: 全矩阵交叉扫描（不需要指定国家）──
    if "--cross" in sys.argv:
        candidates = build_cross_matrix()
        print(f"\n📍 全矩阵交叉: 8 bases × {len(COUNTRIES)} 国家")
        print(f"📋 候选码数: {len(candidates)}")
        if preview:
            print(f"\n候选码预览:")
            for c in candidates:
                print(f"  {c}")
            return

        results = batch_check(candidates, delay=0.15)

        eligible = [c for c, r in results.items() if r == "ELIGIBLE"]
        exists = [c for c, r in results.items() if r == "EXISTS"]
        errors = {c: r for c, r in results.items() if r not in ("EXISTS", "ELIGIBLE", "not_found")}

        print(f"\n{'='*60}")
        print(f"📊 全矩阵交叉扫描完成")
        print(f"{'='*60}")
        print(f"  总测试:  {len(candidates)}")
        print(f"  ✅ ELIGIBLE: {len(eligible)}")
        print(f"  🔶 EXISTS: {len(exists)}")
        print(f"  总计有效: {len(eligible) + len(exists)}")
        if errors:
            print(f"  ⚠️  异常: {len(errors)}")
        if eligible:
            print(f"\n✅ ELIGIBLE:")
            for c in eligible: print(f"  {c}")
        if exists:
            print(f"\n🔶 EXISTS:")
            for c in exists: print(f"  {c}")
        if errors:
            print(f"\n⚠️  异常:")
            for c, r in errors.items(): print(f"  {c}: {r}")

        result_path = os.path.join(OUTPUT_DIR, "discovery_cross.json")
        with open(result_path, "w") as f:
            json.dump({
                "target": "CROSS",
                "scan_time": datetime.now().isoformat(),
                "total_tested": len(candidates),
                "eligible": eligible, "exists": exists, "errors": errors,
            }, f, indent=2, ensure_ascii=False)
        print(f"\n📝 结果已保存: {result_path}")
        if code_only:
            for c in eligible + exists: print(c)
        return

    # ── --gen-old: 只生成旧的候选列表供去重 ──
    if gen_old:
        old = _build_old_only()
        _save_prev_candidates(old)
        print(f"📝 已保存 {len(old)} 个旧候选码到 {DEDUP_FILE}")
        return

    # ── 解析目标国家 ──
    target = None
    for cc in COUNTRIES:
        if cc in sys.argv:
            target = cc
            break
    if not target:
        print("用法: python discover_codes.py [国家码] [选项]")
        print("示例: python discover_codes.py GB")
        print("      python discover_codes.py GB --auto-scan")
        print("      python discover_codes.py GB --preview")
        print("      python discover_codes.py GB --gen-old")
        print("      python discover_codes.py --cross")
        print("      python discover_codes.py --list")
        sys.exit(1)

    # ── 国家扫描模式 ──
    dedup_set = _load_prev_candidates()
    if dedup_set:
        print(f"📋 加载 {len(dedup_set)} 个已测码用于去重")
    else:
        print("⚠️  未找到去重文件，可能包含已测码")

    candidates = build_candidates(target, dedup_set)
    print(f"\n📍 目标地区: {COUNTRIES[target]['name']} ({target})")
    print(f"📋 候选码数: {len(candidates)}")

    if preview:
        print(f"\n候选码预览（前 50 个）:")
        for c in candidates[:50]:
            print(f"  {c}")
        print(f"  ... 共 {len(candidates)} 个")
        return

    # 批量验证
    results = batch_check(candidates, delay=0.15)

    # 分类
    eligible = [c for c, r in results.items() if r == "ELIGIBLE"]
    exists = [c for c, r in results.items() if r == "EXISTS"]
    errors = {c: r for c, r in results.items() if r not in ("EXISTS", "ELIGIBLE", "not_found")}

    # 汇总
    found_codes = []
    print(f"\n{'='*60}")
    print(f"📊 扫描完成")
    print(f"{'='*60}")
    print(f"  总测试:  {len(candidates)}")
    print(f"  ✅ ELIGIBLE: {len(eligible)}")
    print(f"  🔶 EXISTS: {len(exists)}")
    print(f"  总计有效: {len(eligible) + len(exists)}")
    if errors:
        print(f"  ⚠️  异常: {len(errors)}")

    if eligible:
        print(f"\n✅ ELIGIBLE (可直接使用):")
        for c in eligible:
            print(f"  {c}")
            found_codes.append({"code": c, "status": "ELIGIBLE"})

    if exists:
        print(f"\n🔶 EXISTS (存在，需对应地区):")
        for c in exists:
            print(f"  {c}")
            found_codes.append({"code": c, "status": "EXISTS"})

    if errors:
        print(f"\n⚠️  异常结果:")
        for c, r in errors.items():
            print(f"  {c}: {r}")

    # 保存结果
    result_path = os.path.join(OUTPUT_DIR, f"discovery_{target}.json")
    with open(result_path, "w") as f:
        json.dump({
            "target": target,
            "scan_time": datetime.now().isoformat(),
            "total_tested": len(candidates),
            "eligible": eligible,
            "exists": exists,
            "errors": errors,
        }, f, indent=2, ensure_ascii=False)
    print(f"\n📝 结果已保存: {result_path}")

    # --code-only 只打印有效码
    if code_only:
        for c in eligible + exists:
            print(c)

    # --auto-scan 自动验证价格
    if auto_scan and found_codes:
        print(f"\n{'='*60}")
        print(f"🚀 开始价格验证...")
        print(f"{'='*60}")
        enriched = verify_prices(found_codes, target)

        # 保存带价格的完整结果
        enriched_path = os.path.join(OUTPUT_DIR, f"discovery_{target}_priced.json")
        with open(enriched_path, "w") as f:
            json.dump({
                "target": target,
                "scan_time": datetime.now().isoformat(),
                "results": enriched,
            }, f, indent=2, ensure_ascii=False)
        print(f"\n📝 带价格的结果: {enriched_path}")


if __name__ == "__main__":
    main()
