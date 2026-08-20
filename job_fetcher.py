"""
Job Fetcher and Referral Lead Discovery Module
Targeting Product Manager & Associate Product Manager (APM) roles in:
- Pune, India
- European Union (EU / Germany / Netherlands / France)
- Japan
- Singapore
- Indonesia
- Remote
"""

import json
import logging
import uuid
from datetime import datetime
import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def load_tracker():
    if not config.TRACKER_FILE.exists():
        return []
    try:
        with open(config.TRACKER_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_tracker(data):
    try:
        with open(config.TRACKER_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logging.info("Saved updated tracker database.")
    except Exception as e:
        logging.error(f"Error saving tracker: {e}")


def is_target_role_and_location(role: str, location: str) -> bool:
    """Checks if role and location match the candidate's preferred criteria."""
    role_match = any(target.lower() in role.lower() for target in ["product manager", "associate product manager", "apm", "ai product manager"])
    loc_match = any(loc.lower() in location.lower() for loc in config.TARGET_LOCATIONS)
    return role_match and loc_match


def sync_target_jobs(new_jobs_list=None):
    """
    Syncs new targeted job leads into tracker.json.
    Ensures no duplicate entries for company + role.
    """
    existing_data = load_tracker()
    existing_keys = {f"{item.get('company', '').lower()}_{item.get('role', '').lower()}" for item in existing_data}
    today_str = datetime.utcnow().strftime("%Y-%m-%d")

    # High-quality sample initial targets matching Pune, EU, Japan, Singapore, Indonesia & Remote
    sample_jobs = [
        {
            "company": "FlytBase",
            "role": "AI Product Manager",
            "location": "Pune, India",
            "contact_name": "Recruiting Manager",
            "contact_email": "careers@flytbase.com"
        },
        {
            "company": "Revolut",
            "role": "Product Manager - AI Platform",
            "location": "Remote / EU",
            "contact_name": "Talent Acquisition",
            "contact_email": "recruitment@revolut.com"
        },
        {
            "company": "Mercari",
            "role": "Associate Product Manager",
            "location": "Tokyo, Japan / Remote",
            "contact_name": "Hiring Lead",
            "contact_email": "jobs@mercari.com"
        },
        {
            "company": "Grab",
            "role": "Product Manager - Consumer Experience",
            "location": "Singapore / Remote",
            "contact_name": "Tech Recruiter",
            "contact_email": "careers@grab.com"
        },
        {
            "company": "GoTo Group",
            "role": "Product Manager",
            "location": "Jakarta, Indonesia / Remote",
            "contact_name": "Talent Partner",
            "contact_email": "recruitment@gotocompany.com"
        }
    ]

    jobs_to_process = new_jobs_list if new_jobs_list is not None else sample_jobs
    added_count = 0

    for job in jobs_to_process:
        key = f"{job['company'].lower()}_{job['role'].lower()}"
        if key not in existing_keys:
            new_record = {
                "job_id": f"job_{uuid.uuid4().hex[:8]}",
                "company": job["company"],
                "role": job["role"],
                "location": job.get("location", "Remote"),
                "contact_name": job.get("contact_name", "Hiring Team"),
                "contact_email": job.get("contact_email", ""),
                "status": "PENDING_OUTREACH",
                "date_applied": today_str,
                "last_action_date": today_str,
                "followup_count": 0,
                "history": [
                    {
                        "date": today_str,
                        "action": f"Lead added for {job['role']} at {job['company']} ({job.get('location', 'Remote')})."
                    }
                ]
            }
            existing_data.append(new_record)
            existing_keys.add(key)
            added_count += 1

    if added_count > 0:
        save_tracker(existing_data)
        logging.info(f"Added {added_count} new targeted PM/APM job lead(s) to tracker.json ledger.")
    else:
        logging.info("No new target job leads to add.")


if __name__ == "__main__":
    sync_target_jobs()
