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
import re
import urllib.request
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


def fetch_live_jobs():
    """
    Fetches real-time Product Manager & APM leads from public remote/regional APIs
    (Jobicy, Remotive, Arbeitnow, RemoteOK).
    Returns a list of structured job dictionaries.
    """
    live_jobs = []

    # 1. Jobicy API
    try:
        req = urllib.request.Request(
            "https://jobicy.com/api/v2/remote-jobs?count=50",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for item in data.get("jobs", []):
                role = item.get("jobTitle", "")
                company = item.get("companyName", "")
                location = item.get("jobGeo", "Remote")
                job_url = item.get("url", "")
                explicit_email = item.get("contactEmail") or item.get("email") or ""

                if is_target_role_and_location(role, location):
                    live_jobs.append({
                        "company": company,
                        "role": role,
                        "location": f"{location} (Remote)",
                        "contact_name": "Hiring Manager",
                        "contact_email": explicit_email,
                        "apply_url": job_url
                    })
    except Exception as e:
        logging.warning(f"Could not fetch from Jobicy API: {e}")

    # 2. Remotive API
    try:
        req = urllib.request.Request(
            "https://remotive.com/api/remote-jobs?category=product",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for item in data.get("jobs", []):
                role = item.get("title", "")
                company = item.get("company_name", "")
                location = item.get("candidate_required_location", "Remote")
                job_url = item.get("url", "")
                explicit_email = item.get("contact_email") or ""

                if is_target_role_and_location(role, location):
                    live_jobs.append({
                        "company": company,
                        "role": role,
                        "location": f"{location} (Remote)",
                        "contact_name": "Hiring Manager",
                        "contact_email": explicit_email,
                        "apply_url": job_url
                    })
    except Exception as e:
        logging.warning(f"Could not fetch from Remotive API: {e}")

    # 3. Arbeitnow API (EU / Germany tech roles)
    try:
        req = urllib.request.Request(
            "https://www.arbeitnow.com/api/job-board-api",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for item in data.get("data", []):
                role = item.get("title", "")
                company = item.get("company_name", "")
                location = item.get("location", "EU")
                job_url = item.get("url", "")
                explicit_email = item.get("email") or ""

                if is_target_role_and_location(role, location):
                    live_jobs.append({
                        "company": company,
                        "role": role,
                        "location": location,
                        "contact_name": "Talent Acquisition",
                        "contact_email": explicit_email,
                        "apply_url": job_url
                    })
    except Exception as e:
        logging.warning(f"Could not fetch from Arbeitnow API: {e}")

    # 4. RemoteOK API
    try:
        req = urllib.request.Request(
            "https://remoteok.com/api",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, list) and len(data) > 1:
                for item in data[1:]:
                    if isinstance(item, dict):
                        role = item.get("position", "")
                        company = item.get("company", "")
                        location = item.get("location", "Remote")
                        job_url = item.get("url", "")
                        explicit_email = item.get("email") or ""

                        if is_target_role_and_location(role, location):
                            live_jobs.append({
                                "company": company,
                                "role": role,
                                "location": location or "Remote",
                                "contact_name": "Recruiting Team",
                                "contact_email": explicit_email,
                                "apply_url": job_url
                            })
    except Exception as e:
        logging.warning(f"Could not fetch from RemoteOK API: {e}")

    logging.info(f"Discovered {len(live_jobs)} live target job lead(s) from external APIs.")
    return live_jobs


def is_target_role_and_location(role: str, location: str) -> bool:
    """Checks if role and location match the candidate's preferred criteria."""
    role_lower = role.lower()
    loc_lower = location.lower() if location else ""

    if any(ex in role_lower for ex in ["designer", "marketing", "sales", "account executive", "recruiter", "writer", "copywriter"]):
        return False

    role_keywords = [
        "product manager", "associate product manager", "apm", "ai product manager",
        "product owner", "product lead", "head of product", "lead product manager",
        "technical product manager", "senior product manager"
    ]
    role_match = any(target in role_lower for target in role_keywords)

    loc_keywords = [loc.lower() for loc in config.TARGET_LOCATIONS] + [
        "worldwide", "anywhere", "remote", "europe", "tokyo", "jakarta", "asia", "emea", "global", "india", "usa", "us", "americas"
    ]
    loc_match = not loc_lower or any(loc in loc_lower for loc in loc_keywords)

    return role_match and loc_match


def is_generic_email(addr: str) -> bool:
    """Returns True if the email address is generic (e.g. careers@, jobs@, hr@, info@) or empty."""
    if not addr or "@" not in addr:
        return True
    local_part = addr.split("@")[0].lower()
    generic_prefixes = {"careers", "jobs", "hr", "recruitment", "contact", "info", "support", "hiring", "talent", "help", "admin", "sales"}
    return local_part in generic_prefixes


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
            "contact_email": ""
        },
        {
            "company": "Revolut",
            "role": "Product Manager - AI Platform",
            "location": "Remote / EU",
            "contact_name": "Talent Acquisition",
            "contact_email": ""
        },
        {
            "company": "Mercari",
            "role": "Associate Product Manager",
            "location": "Tokyo, Japan / Remote",
            "contact_name": "Hiring Lead",
            "contact_email": ""
        },
        {
            "company": "Grab",
            "role": "Product Manager - Consumer Experience",
            "location": "Singapore / Remote",
            "contact_name": "Tech Recruiter",
            "contact_email": ""
        },
        {
            "company": "GoTo Group",
            "role": "Product Manager",
            "location": "Jakarta, Indonesia / Remote",
            "contact_name": "Talent Partner",
            "contact_email": ""
        }
    ]

    # Fetch live jobs from remote APIs
    fetched_api_jobs = fetch_live_jobs()

    if new_jobs_list is not None:
        jobs_to_process = new_jobs_list
    else:
        jobs_to_process = sample_jobs + fetched_api_jobs

    added_count = 0

    for job in jobs_to_process:
        key = f"{job['company'].lower()}_{job['role'].lower()}"
        if key not in existing_keys:
            contact_email = job.get("contact_email", "").strip()
            apply_url = job.get("apply_url", "")
            
            # Only set PENDING_OUTREACH if contact_email is explicit and non-generic.
            # If email is generic (careers@, jobs@) or missing, set JOB_LINK_SAVED.
            if contact_email and not is_generic_email(contact_email):
                initial_status = "PENDING_OUTREACH"
            else:
                initial_status = "JOB_LINK_SAVED"

            new_record = {
                "job_id": f"job_{uuid.uuid4().hex[:8]}",
                "company": job["company"],
                "role": job["role"],
                "location": job.get("location", "Remote"),
                "contact_name": job.get("contact_name", "Hiring Team"),
                "contact_email": contact_email,
                "apply_url": apply_url,
                "status": initial_status,
                "date_applied": today_str,
                "last_action_date": today_str,
                "followup_count": 0,
                "history": [
                    {
                        "date": today_str,
                        "action": f"Lead added for {job['role']} at {job['company']} ({job.get('location', 'Remote')}). Initial status: {initial_status}."
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

