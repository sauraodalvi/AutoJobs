import imaplib
import email
from email.header import decode_header
import json
import logging
from datetime import datetime, timezone
import config
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


def clean_email_address(addr: str) -> str:
    """Normalizes and extracts clean email address string."""
    if not addr:
        return ""
    addr = addr.lower().strip()
    if "<" in addr and ">" in addr:
        addr = addr.split("<")[1].split(">")[0].strip()
    return addr


def process_incoming_replies():
    """
    Connects to IMAP inbox, searches for:
    1. Direct recruiter replies (updates status to REPLIED_STOPPED)
    2. Bounce notifications from Mailer Daemon / Postmaster (updates status to EMAIL_BOUNCED)
    """
    data = load_tracker()
    if not data:
        logging.info("No tracking entries found to monitor.")
        return

    if not config.EMAIL_USER or not config.EMAIL_PASS:
        logging.warning("EMAIL_USER or EMAIL_PASS not configured. Skipping IMAP inbox check.")
        return

    # Filter targets waiting for response or with sent emails
    active_targets = {
        clean_email_address(item["contact_email"]): item
        for item in data
        if item.get("status") in ["OUTREACH_SENT", "FOLLOWUP_SENT", "PENDING_OUTREACH"] and item.get("contact_email")
    }

    if not active_targets:
        logging.info("No active outreach threads requiring inbox / bounce monitoring.")
        return

    logging.info(f"Monitoring inbox & bounces for {len(active_targets)} active recruiter contact(s)...")

    try:
        mail = imaplib.IMAP4_SSL(config.IMAP_SERVER, config.IMAP_PORT)
        mail.login(config.EMAIL_USER, config.EMAIL_PASS)
        mail.select("INBOX")

        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        replies_updated = 0
        bounces_updated = 0

        # --- 1. Check Recruiter Direct Replies ---
        for target_email, record in list(active_targets.items()):
            try:
                status, search_data = mail.search(None, f'(FROM "{target_email}")')
                if status == "OK" and search_data[0]:
                    mail_ids = search_data[0].split()
                    if mail_ids:
                        logging.info(f"🚨 REPLY DETECTED from recruiter {target_email} for role '{record['role']}' at '{record['company']}'!")
                        for item in data:
                            if clean_email_address(item.get("contact_email")) == target_email and item.get("status") in ["OUTREACH_SENT", "FOLLOWUP_SENT"]:
                                item["status"] = "REPLIED_STOPPED"
                                item["last_action_date"] = today_str
                                item["history"].append({
                                    "date": today_str,
                                    "action": f"Reply detected from {target_email}. Automated sequence stopped."
                                })
                                replies_updated += 1
            except Exception as target_err:
                logging.error(f"Error checking IMAP replies for {target_email}: {target_err}")

        # --- 2. Check Bounce Notifications (Mailer Daemon / Delivery Failures) ---
        bounce_queries = [
            '(FROM "mailer-daemon")',
            '(FROM "postmaster")',
            '(SUBJECT "Delivery Status Notification")',
            '(SUBJECT "Address not found")',
            '(SUBJECT "Mail Delivery Subsystem")',
        ]

        bounce_msg_ids = set()
        for b_query in bounce_queries:
            try:
                b_status, b_search = mail.search(None, b_query)
                if b_status == "OK" and b_search[0]:
                    for m_id in b_search[0].split():
                        bounce_msg_ids.add(m_id)
            except Exception as b_search_err:
                logging.debug(f"Bounce search query '{b_query}' notice: {b_search_err}")

        if bounce_msg_ids:
            logging.info(f"Found {len(bounce_msg_ids)} potential bounce message(s) in inbox. Inspecting contents...")

        for m_id in bounce_msg_ids:
            try:
                b_status, msg_data = mail.fetch(m_id, "(RFC822)")
                if b_status != "OK" or not msg_data:
                    continue

                raw_email = msg_data[0][1]
                if isinstance(raw_email, bytes):
                    msg = email.message_from_bytes(raw_email)
                else:
                    msg = email.message_from_string(raw_email)

                # Extract body text
                body_text = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            payload = part.get_payload(decode=True)
                            if payload:
                                body_text += payload.decode("utf-8", errors="ignore") + "\n"
                else:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        body_text = payload.decode("utf-8", errors="ignore")

                subject_text = str(msg.get("Subject", ""))
                full_content = f"{subject_text}\n{body_text}".lower()

                # Check if any active target email is mentioned in the bounce message
                for target_email, record in list(active_targets.items()):
                    if target_email in full_content:
                        logging.warning(f"⚠️ BOUNCE CONFIRMED for {target_email} ({record['company']} - {record['role']})!")
                        for item in data:
                            if clean_email_address(item.get("contact_email")) == target_email:
                                if item.get("status") not in ["EMAIL_BOUNCED", "REPLIED_STOPPED"]:
                                    item["status"] = "EMAIL_BOUNCED"
                                    item["last_action_date"] = today_str
                                    item["history"].append({
                                        "date": today_str,
                                        "action": f"Automated bounce detected for {target_email}. Status set to EMAIL_BOUNCED."
                                    })
                                    bounces_updated += 1

            except Exception as bounce_err:
                logging.error(f"Error parsing bounce message ID {m_id}: {bounce_err}")

        mail.logout()

        if replies_updated > 0 or bounces_updated > 0:
            save_tracker(data)
            logging.info(f"Inbox scrub complete: {replies_updated} reply(ies) stopped, {bounces_updated} bounce(s) flagged.")
        else:
            logging.info("Inbox scrub complete: No new replies or bounces detected.")

    except Exception as e:
        logging.error(f"IMAP Connection or Auth failure: {e}")


if __name__ == "__main__":
    process_incoming_replies()
