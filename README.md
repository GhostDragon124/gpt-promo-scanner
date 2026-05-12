# ChatGPT Team (Business) 促销码自动扫描工具

**简体中文** | [English](README_EN.md)

[![LINUX DO](https://img.shields.io/badge/LINUX-DO-FFB003?style=flat-square)](https://linux.do/t/topic/2156521)

> 原创研究首发于 [Linux Do 社区](https://linux.do/t/topic/2156521)（一级用户才可查看）

ChatGPT Team（现 ChatGPT Business）标准价 $50/月（2 人）。OpenAI 给部分渠道合作伙伴发放了促销码，可以 40%~71% 折扣。

本项目提供一套完整的批量发现、验证、比价、支付工具链。跟着下面的流程一步步操作即可。

---

## 目录

- [前置准备](#前置准备)
- [第一步：生成候选码](#第一步生成候选码)
- [第二步：批量验证](#第二步批量验证)
- [第三步：收集价格](#第三步收集价格)
- [第四步：一键支付](#第四步一键支付)
- [结果解读](#结果解读)
- [实战技巧](#实战技巧)
- [踩坑记录](#踩坑记录)
- [文件说明](#文件说明)

---

## 前置准备

### 需要的环境

- **Clash Verge**（或兼容 Clash API 的代理客户端）— 用于切换不同国家的代理节点
- **Python 3.9+**
- **ChatGPT 账号**（免费版即可，不需要订阅）

### 1. 安装项目

```bash
git clone https://github.com/JUk1-GH/gpt-promo-scanner.git
cd gpt-promo-scanner
pip install -r requirements.txt
```

### 2. 配置 Clash

确保 Clash Verge 正在运行，脚本默认连接 `/tmp/verge/verge-mihomo.sock`（Unix socket）。

如果路径不同，修改 `config.toml` 中的 socket 配置。

### 3. 获取 accessToken

ChatGPT 的 API 需要登录凭证，通过浏览器获取：

**方法一（推荐）**：浏览器打开以下地址，在页面显示的 JSON 中找到 `accessToken` 字段：
```
https://chatgpt.com/api/auth/session
```

**方法二**：在 chatgpt.com 按 F12 → Console，执行：
```javascript
const s = await (await fetch('/api/auth/session')).json();
console.log(s.accessToken);
```

会输出一串以 `eyJ` 开头的字符串，复制它。

### 4. 配置 Token

```bash
cp config.toml.example config.toml
```

编辑 `config.toml`，把刚才获取的 token 填入：

```toml
[openai]
token = "eyJhbGciOi..."
```

> ⚠️ Token 有有效期（几小时到几天），过期后所有验证都会返回 `invalid_code`。每次跑脚本前如果发现全部是 `not found`，先去重新获取 token。

---

## 第一步：生成候选码

根据目前已发现的码，大部分遵循这个命名规律：

```
公司名(全小写去空格) + ISO 国家码(小写)
```

例如：`thinkingmachines` + `th` = `thinkingmachinesth`

但**不是绝对的**，存在明显例外：
- 有的码**没有国家后缀**（如 `firstfocus`，没有 AU）
- UK 码后缀不统一，有的用 `uk`（`talentgeniusuk`），有的用 `gb`（`aibuildgroupgb`）
- 可能还有其他未发现的命名变体

### 从哪找公司名单

有促销码的公司通常符合以下特征：

- **中小型 MSP（托管服务提供商）**，为中小企业提供 IT 支持
- **AI 工具公司**，特别是做 Chrome 插件、SaaS 产品的
- **区域性公司**，在一个或几个国家有业务

**确定不包含**：大型咨询公司（Accenture、Deloitte、McKinsey）、大型 MSP（SearchKings）、大型 IT 企业（Samsung SDS）。

### 方法一：用已知 base name 全矩阵扫描

项目内置了目前已发现的 9 个 base name，可以直接对它们做全矩阵交叉扫描（base name × 34 个国家）：

```bash
python discover_codes.py --cross
```

脚本会自动组合所有已知公司名 × 所有国家，逐个调 API 验证。这是最快发现新码的方式。

### 方法二：自己准备公司名单

把你认为可能有码的公司名列出来，按规则生成候选码，丢给脚本扫描。

也可以用 AI 帮你生成公司名单，提示词参考：

> 我正在寻找 ChatGPT Business 的促销码，命名规则是 `公司名全小写去空格 + 国家代码`。请帮我列出一些可能获得 OpenAI 促销码的 MSP 或 AI 工具公司，特别是：
> 1. 做 Chrome 插件的 AI 公司
> 2. 中小型 IT 服务商
> 3. 区域性 MSP

### discover_codes.py 用法详解

```bash
# 扫描指定地区（如英国 GB），使用内置的 base name 列表
python discover_codes.py GB

# 在扫描时额外添加自定义码（可以跟 --cross 一起用）
python discover_codes.py GB --add "mycompanygb"

# 全矩阵扫描：所有已知 base name × 所有国家
python discover_codes.py --cross

# 跟 --cross 时，额外添加自定义 base name 一起扫
python discover_codes.py --cross --add-base "mycompany"

# 预览候选码（不跑验证，只展示会扫哪些）
python discover_codes.py GB --preview

# 扫描完成后自动调用 auto_scan.py 收集价格
python discover_codes.py GB --auto-scan

# 列出脚本支持的国家列表
python discover_codes.py --list
```

结果会按 `ELIGIBLE`（可用）、`EXISTS`（存在但地区不匹配）、`not found`（不存在）三类保存到文件。

---

## 第二步：批量验证

候选码生成完毕后，用 `auto_scan.py` 进行全自动扫描验证。

这个脚本会自动：
1. 检测 Clash 模式和代理组
2. 按地区匹配节点关键字
3. 切换节点 → 测延迟 → 调 checkout API → 收集结果

### 扫描指定地区

```bash
# 只扫描英国 GB
python auto_scan.py GB

# 跳过价格收集（只验证是否存在，更快）
python auto_scan.py GB --no-price
```

适用于：你有明确的目标地区，或者只想确认刚发现的码是否能用。

### 全自动扫描所有地区

```bash
python auto_scan.py
```

脚本会遍历所有支持的地区，自动切换 Clash 节点，逐个验证并收集结果。这是最常用的模式。

### 扫描结果

```
扫描完成！结果已保存到：
- stripe_urls.txt — 所有可用的 Stripe 支付链接
- scan_results.json — 结构化 JSON 结果

共发现 X 个可用码（ELIGIBLE）
共发现 Y 个存在码（EXISTS）
```

### 其他选项

```bash
# 查看支持的地区列表
python auto_scan.py --list

# 扫描后自动用浏览器打开 Stripe 支付页面
python auto_scan.py GB --open
```

---

## 第三步：收集价格

`auto_scan.py` 默认会在验证后自动调用 metadata API 获取折扣信息，并实时换算美元价格。

```
code: thinkingmachinesth
  ✅ ELIGIBLE
  折扣: ฿999/月 off (≈ $17/人)
  2 人实付: ฿561/月 (≈ $17)
```

### 关于价格的重要说明

**官网标价是含税价，Stripe 用不含税价计算折扣。**

例如德国的标价是 €26/seat（含 19% VAT），但 Stripe 内部用 €26 ÷ 1.19 = €21.85/seat 作为 base price。直接用官网标价算实付会差很多。

**正确做法**：看 Stripe 支付页面的 pre-tax 金额。也可以在支付时修改账单地址到免税地区，免去税费。

> 注：脚本收集的价格是 API 返回的折扣值，并非最终实付。最准确的方式是直接打开 Stripe 页面查看。

---

## 第四步：一键支付

找到有效的促销码后，用 `open_stripe.py` 生成支付链接。

这个脚本完全独立，复制出去单独放也能用，只需要 curl_cffi 依赖。

### 用法

```bash
python3 open_stripe.py <促销码> <国家码> <accessToken>
```

需要三个参数：
1. **促销码** — 要使用的码
2. **国家码** — 对应节点的 ISO 国家码（大写）
3. **accessToken** — 从 chatgpt.com 获取的登录凭证（`eyJ...`）

### 示例

```bash
# 泰国节点
python3 open_stripe.py thinkingmachinesth TH eyJhbGciOi...

# 德国节点
python3 open_stripe.py codestonede DE eyJhbGciOi...

# 美国节点
python3 open_stripe.py wildmangous US eyJhbGciOi...
```

### 输出

```
🔗 thinkingmachinesth  [TH]

✅ 链接已生成，复制到浏览器打开：
https://checkout.stripe.com/c/pay/cs_xxx...
```

把链接复制到浏览器打开，确认折扣金额后即可付款。

> ⚠️ 每次使用前需先切换到对应国家的 Clash 节点。例如用 TH 码就先切到泰国节点。

---

## 结果解读

API 返回三种结果：

| 结果 | 含义 | 怎么办 |
|------|------|--------|
| `ELIGIBLE` | 可用，当前账号可直接付 | 直接生成 Stripe 链接支付 |
| `EXISTS` | 码存在，但当前节点地区不匹配 | 切到对应国家的节点再试 |
| `not found` | 不存在（或 token 过期） | 先确认 token 有效，再尝试其他公司名 |

### 为什么没有 ELIGIBLE？

`ELIGIBLE` 取决于你的 ChatGPT 账号地区和当前 Clash 节点的匹配度：

- 如果你的账号是 US 地区，切到 US 节点后 US 码可能就是 `ELIGIBLE`
- 切换到其他地区节点后，对应的本地化码可能变成 `ELIGIBLE`
- 同一账号对不同地区码的 `ELIGIBLE` 状态可能不同

大部分情况下，只要能拿到 `EXISTS` 就说明码是真实的，只是需要切对节点才能支付。

---

## 实战技巧

### 1. 找到更多公司名

有促销码的通常是中小型公司，不是大企业。试试这些思路：

- 搜索 "ChatGPT Team promo code" + AI 工具名
- 关注各国家的中小型 MSP 名单
- TG 上的一些优惠频道偶尔会流出新码
- 让 AI 帮你生成可能有合作的公司名单

### 2. 先验证一个再批量

```bash
# 先用 verify.py 单测一个码
# 或者直接用 discover_codes.py 跑单个地区
python discover_codes.py GB --preview
```

确保 Token 有效、Clash 正常工作后，再跑全量扫描。

### 3. 交叉扫描发现更多

发现一个新的 base name 后，用 `--cross` 做全矩阵扫描：

```bash
python discover_codes.py --cross --add-base "newcompany"
```

如果新公司跟已知公司有类似的多国业务模式，很可能在其他国家也有码。

### 4. 分步扫描避免被封

不要一次性扫太多请求。建议节奏：

1. 先跑 `--cross` 快速筛选（只调 eligibility API）
2. 把 `EXISTS` 的码整理出来
3. 分批用 `auto_scan.py` 收集价格

### 5. 及时更新 Token

Token 过期后所有请求都返回 `invalid_code`，会把有效码误判为不存在。可以设置 cron 定期获取新 token。

---

## 踩坑记录

### 1. CRN 报道的合作伙伴全部无效
初始按 OpenAI 公开合作的 MSP 公司名枚举，SearchKings、Samsung SDS 等全部没有促销码。公共合作伙伴 ≠ 有促销码的合作伙伴。

### 2. 跑大量请求前必须先测一个
一次生成 1286 个候选码直接开跑，全部被 Cloudflare 拉黑。任何批量操作前必须先用单个请求测试 API 可用性。

### 3. Clash 全局模式 vs 规则模式
脚本早期硬编码 `🤖 AI` 代理组，但 Clash 在 global 模式下 ChatGPT 流量走 `GLOBAL` 组，导致节点切换不生效。现已支持动态检测。

### 4. UK 国家后缀不统一
`talentgeniusuk` 有效但 `talentgeniusgb` 不存在；`aibuildgroupgb` 有效但 `aibuildgroupuk` 不存在。对 UK 必须两种后缀都试。

### 5. Cloudflare 限速
连续 ~50 个请求后 Cloudflare 开始拦截。脚本内置了间隔控制和自动切换节点机制，但如果仍遇到，手动放慢节奏。

### 6. 折扣是 per-seat 值
Metadata API 返回的 `discount.value` 是每席位的折扣，2 席位时实际省 = value × 2。

### 7. 促销码有有效期
部分码（如 `geccogb`、`codestonegb`）曾经可用，现已过期。码一旦过期就是永久失效，不可恢复。

### 8. pricing-data.js 含税 ≠ Stripe 不含税价
官网标价是含税价（含 VAT/GST），Stripe checkout 底层用不含税价计算折扣。不同国家 VAT 不同（DE 19%、FR 20%、GB 20%）。直接看 Stripe 页面的 pre-tax 金额最准，或者改账单地址到免税地区。

### 9. Token 过期导致全部 false negative（最大坑）
ChatGPT accessToken 有有效期（通常几小时到几天），过期后 eligibility API 对**任何码都返回 `invalid_code`**。在过期 token 下跑的大批量扫描，所有结果都是假的"不存在"。

**教训**：
- 每次跑扫描前脚本会自动验证 token（用已知有效码调 eligibility API）
- 如果验证失败会打印 `❌ Token 验证失败` 并退出
- 此时需重新从 chatgpt.com F12 Console 获取新 token

---

## 文件说明

| 文件 | 用途 |
|------|------|
| `auto_scan.py` | 全自动扫描 + 价格收集（第二步、第三步用） |
| `discover_codes.py` | 批量发现新促销码（第一步用） |
| `open_stripe.py` | 一键生成 Stripe 付款链接，完全独立可复制（第四步用） |
| `verify.py` | 手动验证单个码是否存在（快速测试用） |
| `config.py` | 配置读取模块 |
| `config.toml.example` | 配置模板 |
| `known_codes.json` | 已知有效码数据库（本地使用，不提交到 git） |

---

## 许可

[MIT](LICENSE)
