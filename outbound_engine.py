import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import json
import logging
import random
import time
from datetime import datetime, timezone
from pathlib import Path
import config
import llm_client
import job_fetcher
import email_validator

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def load_tracker():
    """Loads tracker.json data safely."""
    if not config.TRACKER_FILE.exists():
        logging.warning(f"Tracker file {config.TRACKER_FILE} does not exist.")
        return []
    try:
        with open(config.TRACKER_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error reading tracker.json: {e}")
        return []


def save_tracker(data):
    """Saves data back to tracker.json with clean formatting."""
    try:
        with open(config.TRACKER_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logging.info("Successfully updated tracker.json ledger.")
    except Exception as e:
        logging.error(f"Failed to save tracker.json: {e}")


def send_email(to_email: str, subject: str, body: str, is_digest: bool = False, attach_resume: bool = True) -> bool:
    """
    Transmits an email via SMTP with proper MX validation, RFC PDF attachment, and exception handling.
    """
    to_email = to_email.strip()

    # Pre-flight Syntax, MX, and Mailbox Check
    if not is_digest:
        is_deliverable, reason = email_validator.verify_smtp_mailbox_deliverable(to_email)
        if not is_deliverable:
            logging.error(f"Cannot send email to {to_email}: {reason}. Aborting delivery.")
            return False
    else:
        if not email_validator.validate_email_syntax(to_email):
            logging.error(f"Invalid digest recipient email syntax: {to_email}")
            return False

    if not config.EMAIL_USER or not config.EMAIL_PASS:
        logging.warning(f"SMTP Credentials missing in environment variables. Email transmission to {to_email} simulated/skipped.")
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = config.EMAIL_USER
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        # Attach Resume PDF for outbound job pitches / follow-ups
        if not is_digest and attach_resume:
            resume_path = None
            configured_path = getattr(config, "CANDIDATE_RESUME_PATH", "")
            if configured_path:
                p = Path(configured_path)
                if p.exists() and p.is_file():
                    resume_path = p

            if not resume_path:
                repo_resume = Path(__file__).parent / "Saurao_Dalvi_Resume.pdf"
                if repo_resume.exists() and repo_resume.is_file():
                    resume_path = repo_resume

            if resume_path:
                try:
                    with open(resume_path, "rb") as f:
                        part = MIMEApplication(f.read(), _subtype="pdf")
                    part.add_header("Content-Disposition", "attachment", filename="Saurao Dalvi.pdf")
                    msg.attach(part)
                    logging.info(f"Attached resume PDF ({resume_path.name}) as 'Saurao Dalvi.pdf'")
                except Exception as att_err:
                    logging.warning(f"Could not attach resume {resume_path}: {att_err}")
            else:
                logging.warning("Resume PDF not found on disk. Email sent without attachment.")

        server = smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT, timeout=15)
        server.starttls()
        server.login(config.EMAIL_USER, config.EMAIL_PASS)
        server.send_message(msg)
        server.quit()

        logging.info(f"Email successfully sent to {to_email} with subject: '{subject}'")
        return True
    except Exception as e:
        logging.error(f"Failed to send email to {to_email}: {e}")
        return False


def parse_date(date_str: str) -> datetime:
    """Parses date string or returns epoch if invalid."""
    if not date_str:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)


def execute_daily_sequence():
    """
    Executes the daily outbound sequence for new pitches and follow-ups.
    """
    data = load_tracker()
    if not data:
        logging.info("No records found in tracker ledger.")
        return

    today = datetime.now(timezone.utc)
    today_str = today.strftime("%Y-%m-%d")
    changes_made = False
    new_pitches_sent_today = 0

    logging.info("Starting Daily Outbound Execution Sequence...")

    for item in data:
        status = item.get("status")
        contact_name = item.get("contact_name", "Recruiter")
        contact_email = item.get("contact_email", "").strip()
        company = item.get("company", "the company")
        role = item.get("role", "Product Manager")
        apply_url = item.get("apply_url", "")
        last_action_date_str = item.get("last_action_date", "")
        last_action_date = parse_date(last_action_date_str)
        followup_count = item.get("followup_count", 0)
        outreach_style = item.get("outreach_style", "recruiter")

        # Safety Skip: Stopped, bounced, saved, application ready, blacklisted, or missing email
        blacklist = getattr(config, "BLACKLIST_COMPANIES", [])
        if any(b.lower() in company.lower() for b in blacklist):
            continue

        if status in ["REPLIED_STOPPED", "EMAIL_BOUNCED", "JOB_LINK_SAVED", "APPLICATION_READY"] or not contact_email:
            continue

        # Extra Guard: Convert generic/invalid email targets to APPLICATION_READY
        is_valid_email, reason = email_validator.is_valid_recruiter_email(contact_email, verify_mx=True, allow_hiring_channels=True)
        if not is_valid_email:
            logging.info(f"Skipping cold email to invalid target '{contact_email}' for {role} at {company} ({reason}). Updating status to APPLICATION_READY.")
            item["status"] = "APPLICATION_READY"
            item["contact_email"] = ""
            changes_made = True
        if email_validator.is_hiring_channel_email(contact_email):
            is_deliv, probe_reason = email_validator.verify_smtp_mailbox_deliverable(contact_email, timeout=4)
            if not is_deliv or "250" not in probe_reason:
                logging.info(f"Skipping cold email to unverified channel '{contact_email}' for {role} at {company} ({probe_reason}). Staging as APPLICATION_READY.")
                item["status"] = "APPLICATION_READY"
                item["contact_email"] = ""
                changes_made = True
                continue

        # Loop A: Pending Outreach
        if status == "PENDING_OUTREACH":
            max_pitches = getattr(config, "MAX_DAILY_PITCHES", 5)
            if new_pitches_sent_today >= max_pitches:
                logging.info(f"Reached daily maximum pitch limit ({max_pitches}). Pausing remaining new outreaches for today.")
                continue

            logging.info(f"Processing NEW OUTREACH for {contact_name} ({contact_email}) - Role: {role} at {company}")
            try:
                pitch_data = llm_client.generate_pitch(contact_name, company, role, apply_url, style=outreach_style)
                sent = send_email(contact_email, pitch_data["subject"], pitch_data["body"], attach_resume=True)

                if sent:
                    new_pitches_sent_today += 1
                    item["status"] = "OUTREACH_SENT"
                    item["last_action_date"] = today_str
                    if "history" not in item:
                        item["history"] = []
                    item["history"].append({
                        "date": today_str,
                        "action": f"Sent initial pitch ({pitch_data['subject']}) with attached resume to {contact_email}."
                    })
                    changes_made = True

                # Random stagger delay between emails
                stagger = random.randint(5, 15)
                logging.info(f"Staggering next action by {stagger} seconds to maintain email reputation...")
                time.sleep(stagger)

            except Exception as e:
                logging.error(f"Error processing outreach for {contact_email}: {e}")

        # Loop B: Follow ups
        elif status == "OUTREACH_SENT":
            days_since_last = (today - last_action_date).days
            if days_since_last >= config.DAYS_BETWEEN_FOLLOWUP and followup_count < config.MAX_FOLLOWUPS:
                logging.info(f"Processing FOLLOW-UP #{followup_count + 1} for {contact_name} ({contact_email}) - {days_since_last} days since last action")
                try:
                    followup_data = llm_client.generate_followup(contact_name, company, role, apply_url, style=outreach_style)
                    sent = send_email(contact_email, followup_data["subject"], followup_data["body"], attach_resume=False)

                    if sent:
                        item["followup_count"] = followup_count + 1
                        item["status"] = "FOLLOWUP_SENT"
                        item["last_action_date"] = today_str
                        if "history" not in item:
                            item["history"] = []
                        item["history"].append({
                            "date": today_str,
                            "action": f"Sent follow-up pitch #{followup_count + 1} ({followup_data['subject']}) to {contact_email}."
                        })
                        changes_made = True

                    stagger = random.randint(5, 15)
                    logging.info(f"Staggering next action by {stagger} seconds...")
                    time.sleep(stagger)

                except Exception as e:
                    logging.error(f"Error processing follow-up for {contact_email}: {e}")

    if changes_made:
        save_tracker(data)
        logging.info("Outbound execution sequence completed with ledger updates.")
    else:
        logging.info("Outbound execution sequence completed. No ledger state changes were made.")


def send_daily_digest(recipient_email: str = None) -> bool:
    """
    Sends a structured morning briefing digest to Saurao Dalvi with:
    - Submitted applications (Email & Web)
    - Outbound cold referral pitch statuses
    - Direct application links + tailored cover letter locations
    - Any incoming replies or bounce notices
    """
    data = load_tracker()
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    target_email = recipient_email or config.CANDIDATE_EMAIL or config.EMAIL_USER

    if not target_email:
        logging.warning("No candidate recipient email configured for daily digest.")
        return False

    counts = {
        "APPLIED_EMAIL": 0,
        "APPLIED_ONLINE": 0,
        "PENDING_OUTREACH": 0,
        "OUTREACH_SENT": 0,
        "FOLLOWUP_SENT": 0,
        "APPLICATION_READY": 0,
        "JOB_LINK_SAVED": 0,
        "REPLIED_STOPPED": 0,
        "EMAIL_BOUNCED": 0
    }

    applied_items = []
    application_ready_items = []
    outreach_items = []

    for item in data:
        st = item.get("status", "JOB_LINK_SAVED")
        counts[st] = counts.get(st, 0) + 1
        if st in ["APPLIED_EMAIL", "APPLIED_ONLINE"]:
            applied_items.append(item)
        elif st in ["APPLICATION_READY", "JOB_LINK_SAVED"] and item.get("apply_url"):
            application_ready_items.append(item)
        elif st in ["OUTREACH_SENT", "FOLLOWUP_SENT", "PENDING_OUTREACH"]:
            outreach_items.append(item)

    subject = f"🚀 AutoJobs Morning Briefing - {today_str} ({len(application_ready_items)} Kits Ready | {counts.get('OUTREACH_SENT', 0)} Pitches)"

    body_lines = [
        f"Hi {config.CANDIDATE_NAME},",
        "",
        f"Here is your AutoJobs autonomous agent daily briefing for {today_str}:",
        "",
        "=" * 60,
        "📊 PIPELINE & APPLICATION METRICS",
        "=" * 60,
        f"• 1-Click Application Kits Ready:     {len(application_ready_items)}",
        f"• Verified Recruiter Pitches Sent:    {counts.get('OUTREACH_SENT', 0)}",
        f"• Direct Email Applications Sent:     {counts.get('APPLIED_EMAIL', 0)}",
        f"• Follow-ups Sent:                   {counts.get('FOLLOWUP_SENT', 0)}",
        f"• Total Target Positions Tracked:    {len(data)}",
        "",
    ]

    if applied_items:
        body_lines.extend([
            "=" * 60,
            "✅ AUTONOMOUS APPLICATIONS SUBMITTED",
            "=" * 60
        ])
        for idx, job in enumerate(applied_items[:8], 1):
            comp = job.get("company", "Company")
            role = job.get("role", "Product Manager")
            st = job.get("status", "APPLIED")
            contact = job.get("contact_email", "")
            date_app = job.get("date_applied", today_str)
            body_lines.append(f"{idx}. {role} at {comp} [{st}] - {date_app}")
            if contact:
                body_lines.append(f"   ✉️ Submitted To: {contact}")
            body_lines.append("")

    if outreach_items:
        body_lines.extend([
            "=" * 60,
            "✉️ ACTIVE RECRUITER OUTREACH THREADS",
            "=" * 60
        ])
        for job in outreach_items[:5]:
            comp = job.get("company", "Company")
            role = job.get("role", "Product Manager")
            contact = job.get("contact_name", "Recruiter")
            email = job.get("contact_email", "")
            st = job.get("status", "")
            body_lines.append(f"• {role} at {comp} -> {contact} ({email}) [{st}]")
        body_lines.append("")

    if application_ready_items:
        body_lines.extend([
            "=" * 60,
            "🎯 1-CLICK READY TARGETS & PRE-BUILT KITS",
            "=" * 60
        ])
        for idx, job in enumerate(application_ready_items[:5], 1):
            comp = job.get("company", "Company")
            role = job.get("role", "Product Manager")
            loc = job.get("location", "Remote")
            url = job.get("apply_url", "N/A")
            body_lines.append(f"{idx}. {role} at {comp} ({loc})")
            body_lines.append(f"   👉 Direct Apply Link: {url}")
            body_lines.append(f"   📁 Tailored Cover Letter: cover_letters/{comp}_{role}.txt")
            body_lines.append("")

    # High-Value Referral Targets
    import referral_engine
    top_referral_jobs = sorted(
        data,
        key=lambda j: referral_engine.calculate_referral_priority(j.get("role", ""), j.get("company", ""), j.get("location", ""), j.get("description", ""))[0],
        reverse=True
    )[:5]

    if top_referral_jobs:
        body_lines.extend([
            "=" * 60,
            "⭐ TOP REFERRAL TARGETS & 1-CLICK LINKEDIN DISCOVERY",
            "=" * 60
        ])
        for idx, job in enumerate(top_referral_jobs, 1):
            comp = job.get("company", "Company")
            role = job.get("role", "Product Manager")
            loc = job.get("location", "Remote")
            stars, fit = referral_engine.calculate_referral_priority(role, comp, loc, job.get("description", ""))
            li_search = referral_engine.generate_linkedin_search_url(comp, role, loc)
            body_lines.append(f"{idx}. {'⭐' * stars} {role} at {comp}")
            body_lines.append(f"   🔍 Find Referrers / Hiring Managers on LinkedIn:")
            body_lines.append(f"      {li_search}")
            body_lines.append(f"   📋 1-Click Referral Packet: referrals/{comp}_{role}.txt")
            body_lines.append("")

    body_lines.append("=" * 60)
    body_lines.append("Generated automatically by AutoJobs Autonomous Agent.")
    body = "\n".join(body_lines)

    logging.info(f"Dispatching 09:00 AM Daily Digest to {target_email}...")
    return send_email(target_email, subject, body, is_digest=True, attach_resume=False)


if __name__ == "__main__":
    execute_daily_sequence()
