# ChatGPT Team (Business) 促销码自动扫描工具

[![LINUX DO](https://img.shields.io/badge/LINUX-DO-FFB003?style=flat-square)](https://linux.do/t/topic/2156521)
[![English](https://img.shields.io/badge/English-README_EN-4CAF50?style=flat-square)](README_EN.md)

> 原创研究首发于 [Linux Do 社区](https://linux.do/t/topic/2156521)（一级用户才可查看）
>
> 目前已枚举 **17 个国家** 共 **34 个有效促销码**，最高折扣 71%

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

# 只扫描指定地区（如英国 GB）
python auto_scan.py GB

# 批量发现新促销码（全矩阵交叉扫描）
python discover_codes.py --cross

# 发现指定地区的新码
python discover_codes.py GB
```

## auto_scan.py 用法

| 命令 | 说明 |
|------|------|
| `python auto_scan.py` | 全自动扫描所有地区 |
| `python auto_scan.py <地区>` | 只扫描指定地区，如 `GB`、`US` |
| `python auto_scan.py --list` | 列出支持的地区 |
| `python auto_scan.py <地区> --open` | 扫描后自动打开 Stripe URL |
| `python auto_scan.py --no-price` | 跳过价格收集（更快） |

扫描结果保存在：
- `stripe_urls.txt` — 所有可用的 Stripe 支付链接
- `scan_results.json` — 结构化 JSON 结果

## discover_codes.py 用法

| 命令 | 说明 |
|------|------|
| `python discover_codes.py <地区>` | 批量发现指定地区新码 |
| `python discover_codes.py <地区> --preview` | 预览候选码（不验证） |
| `python discover_codes.py <地区> --auto-scan` | 发现后自动验证价格 |
| `python discover_codes.py --cross` | 全矩阵交叉扫描 |
| `python discover_codes.py --list` | 列出支持的国家 |

结果保存在 `discovery_{国家码}.json`。

## 工作原理

### 命名规则

所有促销码遵循同一模式：
```
[公司名(全小写去空格)][ISO 国家码(小写)]
```

例外：UK 码后缀不统一，有的用 `uk` 有的用 `gb`。

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

### 9. Token 过期导致全部 false negative（最大坑）
ChatGPT accessToken 有有效期（通常几小时到几天），过期后 eligibility API **对任何码都返回 `invalid_code`**，包括本来有效的码。在过期 token 下跑的大批量扫描，所有结果都是假的 "不存在"，浪费了大量 API 调用（约 70,000 次）。

**教训**：
- 每次跑扫描前脚本会自动验证 token（用已知有效码调 eligibility API）
- 如果验证失败会打印 `❌ Token 验证失败` 并退出
- 此时需重新从 chatgpt.com F12 Console 获取新 token
- 不要相信大量 `invalid_code` 的结果 — 除非先确认 token 有效

## 文件说明

| 文件 | 用途 |
|------|------|
| `auto_scan.py` | 全自动扫描 + 价格收集 |
| `discover_codes.py` | 批量发现新促销码 |
| `verify.py` | 简单验证脚本（手工改 CODES 列表即可用） |
| `config.py` | 配置读取模块 |
| `config.toml.example` | 配置模板 |
| `known_codes.json` | 已知有效码数据库（本地使用，不提交） |

## 许可

[MIT](LICENSE)
