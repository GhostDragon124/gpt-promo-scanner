# ChatGPT Team (Business) 促销码自动扫描工具

自动发现、验证 ChatGPT Team（现 ChatGPT Business）促销码，生成 Stripe 支付链接，收集折扣价格。

## 功能

- **全自动扫描** — 自动切换 Clash 代理节点，扫描所有地区促销码
- **价格收集** — 调用 metadata API 获取本地化折扣金额，实时汇率换算 USD
- **批量发现** — 基于 `公司名+国家码` 模式批量猜测新促销码
- **全矩阵交叉扫描** — 用已知 base name 交叉测试所有国家

## 前置条件

1. **Clash Verge**（或兼容 Clash API 的代理客户端）— 用于切换地区节点
2. **Python 3.9+**
3. **ChatGPT 账号**（免费版即可，无需订阅）

## 快速开始

### 1. 安装

```bash
git clone https://github.com/JUk1-GH/gpt-promo-scanner.git
cd gpt-promo-scanner
pip install -r requirements.txt
```

### 2. 配置

复制配置模板：

```bash
cp config.toml.example config.toml
```

需要填写两个配置：

#### 获取 accessToken

1. 浏览器打开 https://chatgpt.com 并登录
2. F12 → Console
3. 执行以下命令获取 token：

```javascript
const s = await (await fetch('/api/auth/session')).json();
console.log(s.accessToken);
```

4. 复制输出的字符串填入 `config.toml`：

```toml
[openai]
token = "eyJhbGciOi..."
```

### 3. 扫描

```bash
# 全自动扫描所有地区（自动切节点 + 价格收集）
python auto_scan.py

# 只扫描英国
python auto_scan.py GB

# 批量发现新促销码（全矩阵交叉扫描）
python discover_codes.py --cross

# 发现英国的新码
python discover_codes.py GB
```

## auto_scan.py 用法

| 命令 | 说明 |
|------|------|
| `python auto_scan.py` | 全自动扫描所有地区 |
| `python auto_scan.py GB` | 只扫描指定地区 |
| `python auto_scan.py --list` | 列出支持的地区 |
| `python auto_scan.py GB --open` | 扫描后自动打开 Stripe URL |
| `python auto_scan.py --no-price` | 跳过价格收集（更快） |

扫描结果保存在：
- `stripe_urls.txt` — 所有可用的 Stripe 支付链接
- `scan_results.json` — 结构化 JSON 结果

## discover_codes.py 用法

| 命令 | 说明 |
|------|------|
| `python discover_codes.py GB` | 批量发现英国新码 |
| `python discover_codes.py GB --preview` | 预览候选码（不验证） |
| `python discover_codes.py GB --auto-scan` | 发现后自动验证价格 |
| `python discover_codes.py --cross` | 全矩阵交叉扫描 |
| `python discover_codes.py --list` | 列出支持的国家 |

结果保存在 `discovery_{国家码}.json`。

## 已知有效码

### US — 当前账户可直接使用

| 促销码 | 价格(2人月付) | 折扣 | 公司 |
|--------|-------------|------|------|
| `thealloynetwork` | $30/月 | 40% | The Alloy Network |
| `alongsideus` | $30/月 | 40% | Alongside |
| `monicaius` | $30/月 | 40% | Monica AI |
| `talentgeniusus` | $25/月 | 50% | TalentGenius |
| `firstfocusus` | $25/月 | 50% | First Focus |
| `wildmangous` | $25/月 | 50% | WildMango |

### 其他地区 — 需对应节点付款

| 促销码 | 地区 | 原价(2人) | 实付(税前) | 折扣 | ≈ USD | 公司 |
|--------|------|----------|-----------|------|-------|------|
| `codestonede` | 🇩🇪 DE | €52 | €15.13/月 | 71% | $18/月 | Codestone |
| `codestonees` | 🇪🇸 ES | €52 | €14.89/月 | 65% | $18/月 | Codestone |
| `codestonefr` | 🇫🇷 FR | €52 | €15.01/月 | 65% | $18/月 | Codestone |
| `firstfocus` | 🇦🇺 AU | A$90 | A$45.00/月 | 50% | $33/月 | First Focus |
| `talentgeniusau` | 🇦🇺 AU | A$70 | A$35.00/月 | 50% | $25/月 | TalentGenius |
| `talentgeniusca` | 🇨🇦 CA | C$68 | C$34.00/月 | 50% | $25/月 | TalentGenius |
| `monicaica` | 🇨🇦 CA | C$68 | C$26.00/月 | 62% | $19/月 | Monica AI |
| `talentgeniusbr` | 🇧🇷 BR | R$260 | R$130.00/月 | 50% | $27/月 | TalentGenius |
| `wildmangofr` | 🇫🇷 FR | €52 | €21.67/月 | 50% | $26/月 | WildMango |
| `aibuildgroupgb` | 🇬🇧 GB | £36 | £18.00/月 | 50% | $25/月 | AI Build Group |
| `talentgeniusuk` | 🇬🇧 GB | £36 | £18.00/月 | 50% | $25/月 | TalentGenius |
| `wildmangoke` | 🇰🇪 KE | $50 | $23.20/月 | 54% | $23/月 | WildMango |
| `wildmangong` | 🇳🇬 NG | ₦67,200 | ₦33,600/月 | 50% | $25/月 | WildMango |
| `firstfocusnz` | 🇳🇿 NZ | NZ$82 | NZ$41.00/月 | 50% | $24/月 | First Focus |
| `wildmangoza` | 🇿🇦 ZA | R800 | R400.00/月 | 50% | $24/月 | WildMango |
| `thinkingmachinesth` | 🇹🇭 TH | ฿1,560 | ฿561.00/月 | 64% | $17/月 | Thinking Machines |
| `thinkingmachinessg` | 🇸🇬 SG | S$64 | S$27.25/月 | 57% | $22/月 | Thinking Machines |
| `thinkingmachinesph` | 🇵🇭 PH | ₱2,900 | ₱1,345.00/月 | 54% | $22/月 | Thinking Machines |

> 所有码均适用 ChatGPT Business 计划，48 个月固定折扣。

## 工作原理

### 命名规则

所有促销码遵循同一模式：
```
[公司名(全小写去空格)][ISO 国家码(小写)]
```

例外：部分码无国家后缀（如 `firstfocus`），有些 UK 码用 `uk` 而非 `gb`（如 `talentgeniusuk`）。

### 验证 API

无需生成 Stripe URL 即可快速判断码是否存在：

```
GET /backend-api/promotions/eligibility/{code}?type=promo
Authorization: Bearer <token>
```

响应：
- `is_eligible: true` → **可用**
- `ineligible_reason.code: "user_not_eligible"` → **存在但地区不匹配**
- `ineligible_reason.code: "invalid_code"` → **不存在**

### 自动扫描流程

```
检测 Clash 模式 (rule/global)
  → 确定代理组 (🤖 AI / GLOBAL)
  → 对美国：切换 US 节点 → checkout API → metadata API → 价格
  → 遍历各地区：匹配节点关键字 → 测延迟 → 切换 → checkout → metadata → 价格
  → 实时汇率换算 USD
  → 汇总输出 + 保存文件
```

## 踩坑记录

### 1. CRN 报道的合作伙伴全部无效
初始按 OpenAI 公开合作的 MSP 公司名枚举，SearchKings、Samsung SDS 等全部没有促销码。公共合作伙伴 ≠ 有促销码的合作伙伴。

### 2. 跑大量请求前必须先测一个
一次生成 1286 个候选码直接开跑，全部被 Cloudflare 拉黑。任何批量操作前必须先用单个请求测试 API 可用性。

### 3. Clash 全局模式 vs 规则模式
脚本早期硬编码 `🤖 AI` 代理组，但 Clash 在 global 模式下 ChatGPT 流量走 `GLOBAL` 组，导致节点切换不生效。通过 `/configs` 端点动态检测当前模式解决。

### 4. UK 国家后缀不统一
`talentgeniusuk` 有效但 `talentgeniusgb` 不存在；`aibuildgroupgb` 有效但 `aibuildgroupuk` 不存在。对 UK 必须两种后缀都试。

### 5. Cloudflare 限速
连续 ~50 个请求后 Cloudflare 开始拦截。需要控制频率 (150-200ms 间隔)、被限速时切换节点、每次请求用新 Session。

### 6. 折扣是 per-seat 值
Metadata API 返回的 `discount.value` 是每席位的折扣，2 席位时实际省 = value × 2。

### 7. 促销码有有效期
`geccogb` 和 `codestonegb` 曾是最便宜的码（~£11/月），现已过期返回 `invalid_code`。

### 8. pricing-data.js 含税 ≠ Stripe 不含税价
官网 `chatgpt.com/#pricing` 的 Business 标价是**含税价**（含 VAT/GST），但 Stripe checkout 内部用**不含税价**计算折扣。例如 DE 官网显示 €26/seat，但 Stripe 实际用 €21.85/seat（€26 ÷ 1.19 VAT）。不同国家 VAT 不同（DE 19%、FR 20%、GB 20% 等），直接用官网标价计算实付会产生偏差。开 Stripe 页面看 pre-tax 金额最准，或者修改账单地址到免税地区可免去税费。

## 公司分布

```
TalentGenius    → US($25)  AU($25)  BR($27)  CA($25)  GB($25)
WildMango       → US($25)  FR($26)  KE($23)  NG($25)  ZA($24)
First Focus     → US($25)  AU($33)  NZ($24)
Codestone       → DE($18)  ES($18)  FR($18)
Monica AI       → US($30)  CA($19)
The Alloy Network→ US($30)
Alongside       → US($30)
AI Build Group  → GB($25)
Thinking Machines → TH($17) SG($22) PH($22)
```

有码的公司全是中小型 MSP/IT 服务和 AI 工具公司，不是大型咨询公司。

## 文件说明

| 文件 | 用途 |
|------|------|
| `auto_scan.py` | 全自动扫描 + 价格收集 |
| `discover_codes.py` | 批量发现新促销码 |
| `verify.py` | 简单验证脚本（手工改 CODES 列表即可用） |
| `config.py` | 配置读取模块 |
| `config.toml.example` | 配置模板 |
| `known_codes.json` | 已知有效码数据库 |

## 许可

[MIT](LICENSE)
