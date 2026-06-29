# Security Policy

## 🛡️ Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | ✅ Active |
| < 1.0   | ❌ Pre-release, no security backports |

---

## 🚨 Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

If you discover a vulnerability — especially one that could leak API keys, drain funds, or compromise a deployed instance — please report it privately:

- 📧 **Email**: [moyy@moyvip.com](mailto:moyy@moyvip.com)
- 💬 **Telegram**: [@rubuskap](https://t.me/rubuskap) (DM only, no group)

Include:
1. **Description** of the issue and its impact
2. **Steps to reproduce** — minimal config / commands
3. **Affected versions** if known
4. **Your suggested fix** if you have one (optional)

### Response time

- **Initial acknowledgement**: within **48 hours**
- **Severity triage**: within **7 days**
- **Patch + disclosure**: depends on severity (see below)

### Disclosure timeline

- **Critical** (key leak, RCE, fund drain) — patch in **< 7 days**, coordinated disclosure
- **High** (privilege escalation, denial of service) — patch in **< 14 days**
- **Medium / Low** — patch in next minor release

---

## ⚠️ Known Risk Surfaces

These are inherent to the project's design — keep them in mind when deploying:

### API keys
- All exchange + LLM keys live in `.env` — **never commit this file**
- `.gitignore` excludes `.env` by default
- Rotate keys after any suspected leak

### Paper mode default
- The agent ships in **paper mode** to prevent accidental real-money trades
- Switching to live mode requires an explicit config flag — review before deploying
- Always run paper for at least 1 week on a new strategy before going live

### LLM prompt injection
- News + sentiment plugins fetch external text and pass it to the LLM
- A malicious news article could attempt to override the system prompt
- Mitigations: prompt isolation, rate limits, decision sanity checks (built-in)
- **Don't trust LLM output blindly** — risk guards must always run after the LLM decision

### Notifier plugins
- Telegram / Discord webhooks can leak trade data if URLs are exposed
- Treat webhook URLs as **secrets** — store in `.env`, never in code

### Dependency vulnerabilities
- Run `pip audit` periodically — we don't have automated CVE scanning yet
- Pin versions in production (`pip freeze > requirements.lock.txt`)

---

## 🔒 Best Practices for Operators

If you deploy `trade-agent` on a VPS:

- ✅ **Run as non-root user** (the systemd unit ships with `User=tradeagent`)
- ✅ **Restrict outbound network** to known exchange + LLM endpoints
- ✅ **Enable 2FA** on every exchange account
- ✅ **Use API keys with trading-only scope** — no withdrawal, no transfer
- ✅ **IP-whitelist API keys** at the exchange where possible
- ✅ **Set daily loss limits** in both the agent config AND the exchange
- ✅ **Monitor `journalctl -u trade-agent`** — set up Telegram alerts for crashes

---

## 📜 Disclosure Hall of Fame

Researchers who responsibly disclose will be credited here (with your permission).

_No reports yet._

---

Thank you for helping keep trade-agent users safe. 🙏
