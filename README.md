# Happpy-Clone: Autonomous Referral & Job Application Agent

**Happpy-Clone** is an open-source, 100% free autonomous referral sourcing and intelligent follow-up agent for **Saurao Dalvi** (Targeting **Product Manager** & **Associate Product Manager** roles in **Pune, EU, Japan, Singapore, Indonesia, and Remote**).

The application runs headlessly in the cloud using **GitHub Actions** on a daily cron schedule (`09:00 UTC`). State is natively persisted in git using `tracker.json`.

---

## 🚀 Key Features

- **Multi-State Transaction Ledger (`tracker.json`)**: Tracks state across `PENDING_OUTREACH`, `OUTREACH_SENT`, `FOLLOWUP_SENT`, and `REPLIED_STOPPED`.
- **Targeted Sourcing**: Dedicated focus on PM/APM roles in Pune, European Union, Japan, Singapore, Indonesia, and Remote.
- **Candidate Resume Integration**: Embedded profile context from Saurao Dalvi's resume (3+ yrs AI PM experience, 0-to-1 launches at FlytBase, CrelioHealth, Sprinto) to generate crisp, high-converting 3-sentence referral pitches.
- **IMAP Response Monitoring**: Checks inbox for unread recruiter replies. Automatically updates status to `REPLIED_STOPPED` and halts future follow-ups for that contact.
- **SMTP Outbound Engine**: Sends personalized pitches and follow-up emails with random 5–15 second delays to maintain sender reputation and avoid anti-spam limits.
- **LiteLLM OpenRouter / Groq Integration**: Generates crisp, non-templated text using free models (`google/gemini-2.5-flash` or `meta-llama/llama-3-8b`).
- **GitHub Actions Auto-Commit**: Automatically commits updated state back to repository at the end of each daily execution run.

---

## 🛠 File Architecture

```
├── .github/workflows/agent.yml  # Daily GitHub Actions workflow & state push
├── config.py                     # Environment config & location/role filters
├── candidate_profile.py          # Saurao Dalvi's resume highlights & pitch prompt builder
├── job_fetcher.py                # Sourcing engine for PM/APM roles in Pune, EU, JP, SG, ID, Remote
├── llm_client.py                 # LiteLLM pitch and follow-up synthesizer
├── inbox_monitor.py              # IMAP inbox reply listener (stops thread on response)
├── outbound_engine.py            # SMTP queue processor (Pitches + Follow-ups with stagger)
├── main.py                       # Orchestration entry point
├── tracker.json                  # Native flat-file state database
├── requirements.txt              # Dependencies
├── .env.example                  # Environment variable reference
└── README.md                     # Documentation
```

---

## 🔑 GitHub Secrets Configuration

Add the following Secrets to your GitHub Repository (**Settings > Secrets and variables > Actions > New repository secret**):

| Secret Name | Description | Example / Recommended Value |
|---|---|---|
| `OPENROUTER_API_KEY` | OpenRouter API Key | `sk-or-v1-...` |
| `EMAIL_USER` | Your email address | `sauraodalvi97@gmail.com` |
| `EMAIL_PASS` | Gmail App Password (16-char) | `xxxx yyyy zzzz wwww` |
| `IMAP_SERVER` | IMAP Server host | `imap.gmail.com` |
| `SMTP_SERVER` | SMTP Server host | `smtp.gmail.com` |

---

## ⚙️ Running Locally

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure `.env`**:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. **Run Main Workflow**:
   ```bash
   python main.py
   ```
