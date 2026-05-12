# ChatGPT Team (Business) Promo Code Scanner

[![LINUX DO](https://img.shields.io/badge/LINUX-DO-FFB003?style=flat-square)](https://linux.do/t/topic/2156521)
[![中文](https://img.shields.io/badge/中文-README-2196F3?style=flat-square)](README.md)

> Original research first published on [Linux Do Community](https://linux.do/t/topic/2156521) (level-1 users only)
>
> Currently covering **17 countries** with **34 valid promo codes**, up to 71% off

Auto-discover, validate ChatGPT Team (now ChatGPT Business) promo codes, generate Stripe payment links, and collect discount pricing.

## Features

- **Automated scanning** — auto-switch Clash proxy nodes, scan all regions
- **Price collection** — fetch localized discounts via metadata API, real-time USD conversion
- **Batch discovery** — guess new promo codes using `company+country` naming pattern
- **Full-matrix cross-scan** — test all countries against known base names

## Prerequisites

1. **Clash Verge** (or any Clash API-compatible proxy client) — for region node switching
2. **Python 3.9+**
3. **ChatGPT account** (free tier works, no subscription needed)

## Quick Start

### 1. Install

```bash
git clone https://github.com/JUk1-GH/gpt-promo-scanner.git
cd gpt-promo-scanner
pip install -r requirements.txt
```

### 2. Configuration

```bash
cp config.toml.example config.toml
```

#### Obtain an accessToken

1. Open https://chatgpt.com and log in
2. F12 → Console
3. Run the following command:

```javascript
const s = await (await fetch('/api/auth/session')).json();
console.log(s.accessToken);
```

4. Copy the output into `config.toml`:

```toml
[openai]
token = "eyJhbGciOi..."
```

### 3. Scanning

```bash
# Full auto-scan all regions (auto node switch + price collection)
python auto_scan.py

# Scan a specific region (e.g. GB)
python auto_scan.py GB

# Matrix cross-scan for new codes
python discover_codes.py --cross

# Discover codes for a specific region
python discover_codes.py GB
```

## auto_scan.py Usage

| Command | Description |
|------|------|
| `python auto_scan.py` | Full auto-scan all regions |
| `python auto_scan.py <region>` | Scan a specific region, e.g. `GB`, `US` |
| `python auto_scan.py --list` | List supported regions |
| `python auto_scan.py <region> --open` | Auto-open Stripe URLs after scan |
| `python auto_scan.py --no-price` | Skip price collection (faster) |

Results saved to:
- `stripe_urls.txt` — All available Stripe payment links
- `scan_results.json` — Structured JSON results

## discover_codes.py Usage

| Command | Description |
|------|------|
| `python discover_codes.py <region>` | Batch-discover codes for a region |
| `python discover_codes.py <region> --preview` | Preview candidates (no validation) |
| `python discover_codes.py <region> --auto-scan` | Auto-verify prices after discovery |
| `python discover_codes.py --cross` | Full-matrix cross-scan |
| `python discover_codes.py --list` | List supported countries |

Results saved to `discovery_{country_code}.json`.

## How It Works

### Naming Convention

All promo codes follow the same pattern:
```
[company_name_lowercase_no_spaces][ISO_country_code_lowercase]
```

Exception: UK codes use inconsistent suffixes — some use `uk`, others `gb`.

### Validation API

Quickly check if a code exists without generating a Stripe URL:

```
GET /backend-api/promotions/eligibility/{code}?type=promo
Authorization: Bearer <token>
```

Response:
- `is_eligible: true` → **Available**
- `ineligible_reason.code: "user_not_eligible"` → **Exists but region mismatch**
- `ineligible_reason.code: "invalid_code"` → **Invalid**

### Auto-Scan Flow

```
Detect Clash mode (rule/global)
  → Identify proxy group (🤖 AI / GLOBAL)
  → US: switch node → checkout API → metadata API → price
  → Other regions: match keyword → ping → switch → checkout → metadata → price
  → Real-time USD conversion
  → Summary output + save files
```

## Pitfalls

### 1. CRN-reported partners all invalid
Initial enumeration using OpenAI's public MSP partners (SearchKings, Samsung SDS, etc.) yielded zero promo codes. Public partner ≠ promo code partner.

### 2. Always test one request first before bulk
Generated 1286 candidates at once — all blocked by Cloudflare. Always test a single request first.

### 3. Clash Global vs Rule mode
Script hardcoded the `🤖 AI` proxy group, but in Global mode traffic goes through the `GLOBAL` group. Fixed by dynamically detecting the mode via `/configs`.

### 4. Inconsistent UK country suffix
`talentgeniusuk` is valid but `talentgeniusgb` is not; `aibuildgroupgb` is valid but `aibuildgroupuk` is not. Must try both suffixes for UK codes.

### 5. Cloudflare Rate Limiting
Cloudflare blocks after ~50 consecutive requests. Mitigation: rate-limit (150-200ms interval), switch nodes when blocked, use a fresh Session per request.

### 6. Discount is per-seat
The `discount.value` from the metadata API is per-seat. For 2 seats, actual savings = value × 2.

### 7. Promo codes expire
`geccogb` and `codestonegb` were once the cheapest (~£11/month) but have since expired, returning `invalid_code`.

### 8. pricing-data.js includes tax, Stripe uses pre-tax
The official pricing page shows **tax-inclusive** prices (with VAT/GST), but Stripe checkout calculates discounts on **pre-tax** prices. E.g., DE shows €26/seat on the website, but Stripe uses €21.85/seat (€26 ÷ 1.19 VAT). Check the Stripe page for pre-tax amounts, or set billing address to a tax-free region.

### 9. Expired token causes false negatives (biggest pitfall)
ChatGPT accessTokens expire (hours to days). An expired token causes the eligibility API to return **`invalid_code` for every code**, including valid ones. This led to ~70,000 wasted API calls.

**Lessons**:
- Script auto-validates the token before each scan using a known valid code
- Prints `❌ Token 验证失败` and exits on failure
- Re-obtain a fresh token from chatgpt.com F12 Console
- Never trust mass `invalid_code` results unless the token is confirmed valid

## Files

| File | Purpose |
|------|---------|
| `auto_scan.py` | Full auto-scan + price collection |
| `discover_codes.py` | Batch-discover new promo codes |
| `verify.py` | Simple validator (edit the CODES list manually) |
| `config.py` | Configuration loader |
| `config.toml.example` | Config template |
| `known_codes.json` | Known valid codes DB (local use, not committed) |

## License

[MIT](LICENSE)
