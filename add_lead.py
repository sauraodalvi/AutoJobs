"""
Helper Utility to Add Target Job Leads with Verified Recruiter Contacts.
Allows adding direct recruiter emails into tracker.json ledger to trigger AI referral outreach.
"""

import argparse
import json
import logging
import sys
import uuid
from datetime import datetime, timezone
import config
import job_fetcher
import email_validator

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def add_job_lead(company: str, role: str, location: str, contact_name: str, contact_email: str, apply_url: str = ""):
    data = job_fetcher.load_tracker()
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    contact_email = contact_email.strip()
    
    is_valid, reason = email_validator.is_valid_recruiter_email(contact_email, verify_mx=True) if contact_email else (False, "No email provided")
    
    if is_valid:
        initial_status = "PENDING_OUTREACH"
        status_msg = "PENDING_OUTREACH (Verified email - Ready for automated AI pitch)"
    else:
        initial_status = "JOB_LINK_SAVED"
        status_msg = f"JOB_LINK_SAVED ({reason})"
        if contact_email:
            logging.warning(f"Email '{contact_email}' rejected: {reason}. Setting status to JOB_LINK_SAVED.")
            contact_email = ""

    new_record = {
        "job_id": f"job_{uuid.uuid4().hex[:8]}",
        "company": company.strip(),
        "role": role.strip(),
        "location": location.strip() or "Remote",
        "contact_name": contact_name.strip() or "Hiring Team",
        "contact_email": contact_email,
        "apply_url": apply_url.strip(),
        "status": initial_status,
        "date_applied": today_str,
        "last_action_date": today_str,
        "followup_count": 0,
        "history": [
            {
                "date": today_str,
                "action": f"Manual lead added for {role} at {company}. Initial status set to: {initial_status}."
            }
        ]
    }

    data.append(new_record)
    job_fetcher.save_tracker(data)
    logging.info(f"✅ Successfully added lead: {role} at {company}")
    logging.info(f"   Contact: {contact_name} ({contact_email or 'Direct Application Link'})")
    logging.info(f"   Status: {status_msg}")


def main():
    parser = argparse.ArgumentParser(description="Add a new target job lead to AutoJobs tracker ledger.")
    parser.add_argument("--company", required=True, help="Target company name (e.g. Google)")
    parser.add_argument("--role", required=True, help="Job title (e.g. AI Product Manager)")
    parser.add_argument("--location", default="Remote", help="Location (e.g. Pune, EU, Remote)")
    parser.add_argument("--name", default="Hiring Manager", help="Recruiter / Contact Person Name")
    parser.add_argument("--email", default="", help="Direct Recruiter Email Address (e.g. john@company.com)")
    parser.add_argument("--url", default="", help="Direct Job Application URL")

    args = parser.parse_args()
    add_job_lead(args.company, args.role, args.location, args.name, args.email, args.url)


if __name__ == "__main__":
    main()
