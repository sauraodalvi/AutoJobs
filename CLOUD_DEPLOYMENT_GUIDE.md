# 🚀 AutoJobs Cloud n8n Referral AI Agent & Copilot — Deployment Guide

This guide details how to deploy **AutoJobs Referral AI Agent** to the cloud using **n8n** and host the **Visual Talent Copilot Dashboard**, matching and exceeding the workflow of **Uplers Referral AI Agent (Happpy Agent)**.

---

## 1. Cloud Architecture Overview

```mermaid
flowchart TD
    subgraph Client["1. Candidate Copilot Layer"]
        A[Browser Bookmarklet on LinkedIn / Careers] -->|1-Click Capture| W[n8n Webhook / Dashboard]
        UI[AutoJobs Visual Web Copilot] -->|Ingest Job & View Dossiers| W
    end

    subgraph n8n_Cloud["2. Cloud n8n Workflow (24/7 on Cloud)"]
        W --> B[Profile Context: Saurao Dalvi - AI PM]
        B --> C[Gemini 2.5 Referral AI Synthesis Node]
        C --> D1[LinkedIn InMail Note <300 Chars]
        C --> D2[Zero-Effort Forwardable HR Blurb]
        C --> D3[Direct Hiring Manager Pitch]
        C --> D4[Automated Follow-up Sequence (Day 3 & Day 7)]
        
        D3 --> E[Gmail / SMTP Automated Dispatch]
        E --> F[IMAP Inbox Reply Listener: Auto-Pauses Sequence]
    end

    subgraph Alerts["3. Instant Real-Time Notifications"]
        C --> T[Telegram / Discord Alert Bot with 1-Click Search Links]
        C --> DB[(Google Sheets / Supabase Ledger)]
    end
```

---

## 2. Deploying n8n to the Cloud (Free / Low Cost Options)

### Option A: 1-Click Deploy on Railway (Recommended)
1. Go to [Railway.app](https://railway.app/) and create an account.
2. Click **New Project** $\to$ **Deploy from Template** $\to$ Search **n8n**.
3. Set the following Environment Variables in Railway:
   - `N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=true`
   - `N8N_DEFAULT_BINARY_DATA_MODE=filesystem`
   - `WEBHOOK_URL=https://your-app-name.up.railway.app/`
4. Click **Deploy**. Your cloud n8n instance will be live at `https://your-app-name.up.railway.app`.

### Option B: Deploy on Render
1. Go to [Render.com](https://render.com/).
2. Create a **Web Service** $\to$ choose Docker image: `n8nio/n8n:latest`.
3. Add a persistent disk mounted at `/home/node/.n8n`.
4. Deploy!

### Option C: Official n8n Cloud
1. Sign up on [n8n.io/cloud](https://n8n.io/cloud).

---

## 3. Importing the AutoJobs Referral AI Workflow

1. Open your cloud n8n dashboard.
2. Click **Workflows** $\to$ **Add Workflow** $\to$ Click the **`...` menu** top right $\to$ **Import from File**.
3. Select `n8n_referral_ai_agent_workflow.json` from this repository.
4. Configure your Credentials:
   - **Gemini / OpenAI API**: Add your OpenRouter API Key or Google Gemini API Key.
   - **Telegram Bot (Optional for instant mobile push)**:
     1. Create a free bot with `@BotFather` on Telegram.
     2. Get your `Bot Token` and your `Chat ID` (via `@userinfobot`).
     3. Add to the Telegram node.
   - **Gmail / SMTP (Optional for automated outbound)**:
     - Use your Gmail App Password (`EMAIL_USER=sauraodalvi97@gmail.com`).
5. Click **Save** and toggle the workflow to **Active**.

---

## 4. Hosting the Visual Talent Copilot Dashboard

The dashboard in `dashboard/` is 100% static HTML/CSS/JS and can be hosted anywhere for free:

### 1-Click Free Hosting on Netlify or Vercel:
1. Drag and drop the `dashboard/` folder into [Netlify Drop](https://app.netlify.com/drop) or push to GitHub and connect to Vercel/GitHub Pages.
2. Your live dashboard will be accessible from your phone and laptop at `https://your-autojobs-copilot.netlify.app`.

### Local Quick Preview:
To test locally right now:
```bash
# In the AutoJobs repository directory:
.\.venv\Scripts\python.exe -m http.server 8000
```
Open your browser at: `http://localhost:8000/dashboard/`

---

## 5. Setting up the 1-Click Chrome/Brave Bookmarklet

1. Open your browser Bookmarks Bar (`Ctrl+Shift+B` or `Cmd+Shift+B`).
2. Open the AutoJobs Dashboard at `http://localhost:8000/dashboard/`.
3. Drag the **"📌 AutoJobs 1-Click Capture"** button directly to your browser's Bookmarks Bar.
4. Whenever you are looking at a job on LinkedIn, Greenhouse, Lever, or a career page, click the bookmark:
   - It automatically extracts the company and title.
   - It opens your Referral AI Agent Copilot and synthesizes the exact LinkedIn connect note, forwardable employee blurb, and hiring manager pitch in under 1 second.
