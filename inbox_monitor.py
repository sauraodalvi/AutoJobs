import imaplib
import email
from email.header import decode_header
import json
import logging
from datetime import datetime
import config

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
    Connects to IMAP inbox, searches for replies from tracked recruiters,
    and updates their record status to REPLIED_STOPPED.
    """
    data = load_tracker()
    if not data:
        logging.info("No tracking entries found to monitor.")
        return

    # Filter targets waiting for response
    active_targets = {
        clean_email_address(item["contact_email"]): item
        for item in data
        if item.get("status") in ["OUTREACH_SENT", "FOLLOWUP_SENT"] and item.get("contact_email")
    }

    if not active_targets:
        logging.info("No active outreach threads requiring reply monitoring.")
        return

    logging.info(f"Monitoring replies for {len(active_targets)} active recruiter contact(s)...")

    if not config.EMAIL_USER or not config.EMAIL_PASS:
        logging.warning("EMAIL_USER or EMAIL_PASS not configured. Skipping IMAP inbox check.")
        return

    try:
        mail = imaplib.IMAP4_SSL(config.IMAP_SERVER, config.IMAP_PORT)
        mail.login(config.EMAIL_USER, config.EMAIL_PASS)
        mail.select("INBOX")

        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        updated_count = 0

        # Check each target email individually or search UNSEEN messages
        for target_email, record in active_targets.items():
            try:
                # Search for unread messages or messages from target email
                status, search_data = mail.search(None, f'(FROM "{target_email}")')
                if status != "OK" or not search_data[0]:
                    continue

                mail_ids = search_data[0].split()
                if mail_ids:
                    logging.info(f"🚨 REPLY DETECTED from recruiter {target_email} for role '{record['role']}' at '{record['company']}'!")
                    
                    # Update status in the main record list
                    for item in data:
                        if clean_email_address(item.get("contact_email")) == target_email and item.get("status") in ["OUTREACH_SENT", "FOLLOWUP_SENT"]:
                            item["status"] = "REPLIED_STOPPED"
                            item["last_action_date"] = today_str
                            item["history"].append({
                                "date": today_str,
                                "action": f"Reply detected from {target_email}. Automated sequence stopped."
                            })
                            updated_count += 1

            except Exception as target_err:
                logging.error(f"Error checking IMAP for target {target_email}: {target_err}")

        mail.logout()

        if updated_count > 0:
            save_tracker(data)
            logging.info(f"Updated {updated_count} record(s) to REPLIED_STOPPED state.")
        else:
            logging.info("No new recruiter replies detected in inbox.")

    except Exception as e:
        logging.error(f"IMAP Connection or Auth failure: {e}")


if __name__ == "__main__":
    process_incoming_replies()
