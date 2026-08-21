import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import logging
import random
import time
from datetime import datetime, timedelta
import config
import llm_client
import job_fetcher

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


def send_email(to_email: str, subject: str, body: str) -> bool:
    """
    Transmits an email via SMTP with proper exception handling.
    """
    if not config.EMAIL_USER or not config.EMAIL_PASS:
        logging.warning("SMTP Credentials missing in environment variables. Email transmission simulated/skipped.")
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = config.EMAIL_USER
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        server = smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT)
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
        return datetime.min
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return datetime.min


def execute_daily_sequence():
    """
    Executes the daily outbound sequence for new pitches and follow-ups.
    """
    data = load_tracker()
    if not data:
        logging.info("No records found in tracker ledger.")
        return

    today = datetime.utcnow()
    today_str = today.strftime("%Y-%m-%d")
    changes_made = False

    logging.info("Starting Daily Outbound Execution Sequence...")

    for item in data:
        status = item.get("status")
        contact_name = item.get("contact_name", "Recruiter")
        contact_email = item.get("contact_email", "")
        company = item.get("company", "the company")
        role = item.get("role", "Software Engineer")
        last_action_date_str = item.get("last_action_date", "")
        last_action_date = parse_date(last_action_date_str)
        followup_count = item.get("followup_count", 0)

        # Safety Skip: Stopped, bounced, saved, or missing email
        if status in ["REPLIED_STOPPED", "EMAIL_BOUNCED", "JOB_LINK_SAVED"] or not contact_email:
            continue

        # Extra Guard: Convert generic email targets (e.g. careers@, jobs@) to JOB_LINK_SAVED
        if job_fetcher.is_generic_email(contact_email):
            logging.info(f"Skipping cold email to generic email '{contact_email}' for {role} at {company}. Updating status to JOB_LINK_SAVED.")
            item["status"] = "JOB_LINK_SAVED"
            item["last_action_date"] = today_str
            item["history"].append({
                "date": today_str,
                "action": f"Generic contact email {contact_email} detected. Converted status to JOB_LINK_SAVED to prevent bounce."
            })
            changes_made = True
            continue

        # Loop A: Pending Outreach
        if status == "PENDING_OUTREACH":
            logging.info(f"Processing NEW OUTREACH for {contact_name} ({contact_email}) - Role: {role} at {company}")
            try:
                pitch_data = llm_client.generate_pitch(contact_name, company, role)
                sent = send_email(contact_email, pitch_data["subject"], pitch_data["body"])

                if sent:
                    item["status"] = "OUTREACH_SENT"
                    item["last_action_date"] = today_str
                    if "history" not in item:
                        item["history"] = []
                    item["history"].append({
                        "date": today_str,
                        "action": f"Sent initial referral pitch to {contact_email}."
                    })
                    changes_made = True

                # Random stagger delay between emails
                stagger = random.randint(5, 15)
                logging.info(f"Stagging next action by {stagger} seconds to maintain email reputation...")
                time.sleep(stagger)

            except Exception as e:
                logging.error(f"Error processing outreach for {contact_email}: {e}")

        # Loop B: Follow ups
        elif status == "OUTREACH_SENT":
            days_since_last = (today - last_action_date).days
            if days_since_last >= config.DAYS_BETWEEN_FOLLOWUP and followup_count < config.MAX_FOLLOWUPS:
                logging.info(f"Processing FOLLOW-UP #{followup_count + 1} for {contact_name} ({contact_email}) - {days_since_last} days since last action")
                try:
                    followup_data = llm_client.generate_followup(contact_name, company, role)
                    sent = send_email(contact_email, followup_data["subject"], followup_data["body"])

                    if sent:
                        item["followup_count"] = followup_count + 1
                        item["status"] = "FOLLOWUP_SENT"
                        item["last_action_date"] = today_str
                        if "history" not in item:
                            item["history"] = []
                        item["history"].append({
                            "date": today_str,
                            "action": f"Sent follow-up pitch #{followup_count + 1} to {contact_email}."
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


if __name__ == "__main__":
    execute_daily_sequence()
