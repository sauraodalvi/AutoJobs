# AutoJobs: Autonomous Job Application & Recruiter Outreach Agent

**AutoJobs** is an open-source autonomous job referral sourcing, direct application kit generator, and intelligent follow-up agent tailored for **Saurao Dalvi** (Targeting **Product Manager**, **Associate Product Manager (APM)**, and **AI Product Manager** roles in **Pune, EU, Japan, Singapore, Indonesia, and Remote**).

The application runs headlessly in the cloud using **GitHub Actions** on a daily cron schedule (`09:00 AM IST / 03:30 AM UTC`) and can also be scheduled locally on Windows via **Windows Task Scheduler**. State is natively persisted in git using `tracker.json`.

---

## 🚀 Key Features

- **Dual-Action Pipeline (Direct Apply + Cold Outreach)**:
  - **Cold Outreach**: Discovers and validates recruiter emails with DNS MX deliverability checks, synthesizes personalized referral pitches, and handles follow-ups.
  - **Direct Applications**: Auto-synthesizes tailored, high-converting cover letters and application answers for direct job links, saved to `cover_letters/`.
- **09:00 AM Daily Morning Briefing**: Sends an automated daily briefing email directly to candidate (`sauraodalvi97@gmail.com`) with 1-click apply links, tailored cover letter files, and outreach progress.
- **DNS MX & RFC Email Validation (`email_validator.py`)**: Eliminates invalid and bouncing email addresses by verifying domain Mail Exchange (MX) records and syntax before any email is queued or transmitted.
- **IMAP Response & Bounce Monitoring**: Checks inbox for unread recruiter replies (automatically halting future follow-ups) and flags delivery bounce notifications.
- **Multi-State Transaction Ledger (`tracker.json`)**: Tracks state across `APPLICATION_READY`, `JOB_LINK_SAVED`, `PENDING_OUTREACH`, `OUTREACH_SENT`, `FOLLOWUP_SENT`, and `REPLIED_STOPPED`.
- **LiteLLM OpenRouter / Groq Integration**: Crafts natural, high-impact messages customized with candidate's AI PM achievements.

---

## 🛠 File Architecture

```
├── .github/workflows/agent.yml  # 09:00 AM IST GitHub Actions daily workflow & state push
├── email_validator.py            # DNS MX verification, RFC regex syntax, and domain sanitization
├── config.py                     # Environment config & location/role filters
├── candidate_profile.py          # Saurao Dalvi's resume highlights & pitch prompt builder
├── job_fetcher.py                # Sourcing engine for PM/APM roles in Pune, EU, JP, SG, ID, Remote
├── contact_finder.py             # Verified recruiter discovery with MX validation
├── cover_letter_generator.py     # Tailored 3-paragraph cover letters for saved job leads
├── llm_client.py                 # LiteLLM pitch, follow-up, and cover letter synthesizer
├── inbox_monitor.py              # IMAP inbox reply listener & bounce tracker
├── outbound_engine.py            # SMTP queue processor & 09:00 AM Daily Digest dispatcher
├── main.py                       # Orchestration entry point
├── scheduler.py                  # Python local background scheduler
├── run_agent.bat                 # 1-click local execution script
├── setup_windows_task.bat        # 1-click Windows 09:00 AM Task Scheduler setup
├── tracker.json                  # Native flat-file state database
├── requirements.txt              # Dependencies
├── .env.example                  # Environment variable reference
└── README.md                     # Documentation
```

---

## ⏰ 09:00 AM Scheduling Setup

### Option 1: GitHub Actions (Cloud - Recommended)
The GitHub Actions workflow in `.github/workflows/agent.yml` is scheduled at `30 3 * * *` (03:30 AM UTC = **09:00 AM IST**).

Ensure the following Secrets are configured in your GitHub Repository (**Settings > Secrets and variables > Actions > New repository secret**):

| Secret Name | Description | Example / Recommended Value |
|---|---|---|
| `OPENROUTER_API_KEY` | OpenRouter API Key | `sk-or-v1-...` |
| `GROQ_API_KEY` | Groq API Key (optional fallback) | `gsk_...` |
| `EMAIL_USER` | Your email address | `sauraodalvi97@gmail.com` |
| `EMAIL_PASS` | Gmail App Password (16-character) | `xxxx yyyy zzzz wwww` |
| `IMAP_SERVER` | IMAP Server host | `imap.gmail.com` |
| `SMTP_SERVER` | SMTP Server host | `smtp.gmail.com` |

### Option 2: Local Windows Task Scheduler
To schedule the agent to run automatically on your Windows PC every day at 09:00 AM:
1. Double-click `setup_windows_task.bat` (or run in Command Prompt).
2. It registers a native Windows task `AutoJobsDailyAgent` that triggers `run_agent.bat` daily at 09:00 AM.

---

## ⚙️ Running Locally & Testing

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure `.env`**:
   ```bash
   copy .env.example .env
   # Add your EMAIL_USER, EMAIL_PASS, and OPENROUTER_API_KEY
   ```

3. **Run One-Off Execution**:
   ```bash
   run_agent.bat
   # or
   python main.py
   ```

4. **Check Status Report**:
   ```bash
   python status_report.py
   ```

5. **Run Unit Tests**:
   ```bash
   python test_agent.py
   ```
