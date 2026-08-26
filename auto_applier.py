"""
AutoApplier Engine for Autonomous Job Application Processing.
Handles automated direct job applications via verified email endpoints and web submission pipelines.
"""

import json
import logging
import random
import time
from datetime import datetime, timezone
from pathlib import Path
import config
import candidate_profile
import llm_client
import email_validator
import outbound_engine
import cover_letter_generator

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def load_tracker():
    return outbound_engine.load_tracker()


def save_tracker(data):
    outbound_engine.save_tracker(data)


def apply_via_email(job: dict) -> bool:
    """
    Submits a full formal job application via email to the company's verified hiring team.
    Includes tailored cover letter, candidate credentials, and attached resume PDF.
    """
    company = job.get("company", "Company")
    role = job.get("role", "Product Manager")
    contact_email = job.get("contact_email", "").strip()
    contact_name = job.get("contact_name", "Talent Acquisition Team")
    apply_url = job.get("apply_url", "")

    if not contact_email:
        logging.warning(f"No contact email available for {role} at {company}. Cannot submit email application.")
        return False

    is_valid, reason = email_validator.is_valid_recruiter_email(contact_email, verify_mx=True, allow_hiring_channels=False)
    if not is_valid or email_validator.is_hiring_channel_email(contact_email):
        logging.info(f"Staging {role} at {company} as APPLICATION_READY (Direct portal apply & referral only).")
        job["status"] = "APPLICATION_READY"
        job["contact_email"] = ""
        return False

    logging.info(f"🚀 Dispatching Autonomous Job Application for {role} at {company} to <{contact_email}>...")

    # Generate or load tailored cover letter
    kit_path = cover_letter_generator.generate_cover_letter_for_item(job)
    cover_letter_text = ""
    if kit_path and kit_path.exists():
        try:
            with open(kit_path, "r", encoding="utf-8") as f:
                cover_letter_text = f.read()
        except Exception:
            pass

    subject = f"Application: {role} – {config.CANDIDATE_NAME}"

    body_lines = [
        f"Dear {contact_name or 'Hiring Team'},",
        "",
        f"I am writing to formally submit my application for the {role} position at {company}.",
        "",
        "With 3+ years of experience as an AI Product Manager & Forward Deployed Engineer (leading 0-to-1 SaaS products at FlytBase, CrelioHealth, and Sprinto), I specialize in shipping LLM-driven workflows, agentic automations, and customer-facing products that scale MRR.",
        "",
        "---",
        "KEY QUALIFICATIONS & ACHIEVEMENTS:",
        "- Led 0-to-1 roadmap & launch of Prediq (AI drone SaaS) at FlytBase, driving commercial growth.",
        "- Owned Smart Reports at CrelioHealth, increasing lab revenue by ~$2,000 MRR per lab.",
        "- Built automated developer tooling and agentic retrieval workflows cutting operational friction by 50%+.",
        "",
        f"LinkedIn: {candidate_profile.LINKEDIN_URL}",
        f"Portfolio: {candidate_profile.PORTFOLIO_URL}",
    ]

    if apply_url:
        body_lines.append(f"Job Reference: {apply_url}")

    body_lines.extend([
        "",
        "Please find my resume attached in PDF format for your review. I would welcome the opportunity to discuss how my AI product leadership can drive immediate impact for your team.",
        "",
        "Best regards,",
        f"{config.CANDIDATE_NAME}",
        f"Email: {config.CANDIDATE_EMAIL}",
        f"LinkedIn: {candidate_profile.LINKEDIN_URL}",
        f"Portfolio: {candidate_profile.PORTFOLIO_URL}"
    ])

    body = "\n".join(body_lines)

    sent = outbound_engine.send_email(
        to_email=contact_email,
        subject=subject,
        body=body,
        is_digest=False,
        attach_resume=True
    )

    return sent


import browser_applier


def apply_to_pending_jobs(max_applications: int = 5) -> int:
    """
    Scans tracker.json ledger for candidate positions ready for application.
    Executes automated email and browser web submissions.
    """
    data = load_tracker()
    if not data:
        logging.info("No records in tracker ledger to process for applications.")
        return 0

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    applications_submitted = 0
    changes_made = False

    logging.info("Starting Autonomous Dual-Action Job Application Processing Loop...")

    blacklist = getattr(config, "BLACKLIST_COMPANIES", [])

    for item in data:
        if applications_submitted >= max_applications:
            logging.info(f"Reached max batch application limit ({max_applications}). Pausing until next cycle.")
            break

        status = item.get("status")
        contact_email = item.get("contact_email", "").strip()
        apply_url = item.get("apply_url", "").strip()
        company = item.get("company", "Company")
        role = item.get("role", "Product Manager")

        # Skip blacklisted companies
        if any(b.lower() in company.lower() for b in blacklist):
            logging.info(f"Skipping {role} at {company} (Company is blacklisted).")
            continue

        # Route A: Direct Email Application for leads with verified email
        if status in ["PENDING_OUTREACH", "APPLICATION_READY", "JOB_LINK_SAVED"] and contact_email:
            is_valid, _ = email_validator.is_valid_recruiter_email(contact_email, verify_mx=True, allow_hiring_channels=True)
            if is_valid:
                logging.info(f"Processing automated email application for {role} at {company} ({contact_email})...")
                success = apply_via_email(item)
                if success:
                    item["status"] = "APPLIED_EMAIL"
                    item["date_applied"] = today_str
                    item["last_action_date"] = today_str
                    if "history" not in item:
                        item["history"] = []
                    item["history"].append({
                        "date": today_str,
                        "action": f"Automated application & resume PDF submitted to {contact_email}. Status set to APPLIED_EMAIL."
                    })
                    applications_submitted += 1
                    changes_made = True

                    stagger = random.randint(5, 12)
                    logging.info(f"Staggering application rate by {stagger} seconds...")
                    time.sleep(stagger)

        # Route B: Direct Web Application staging with tailored kits
        elif status in ["APPLICATION_READY", "JOB_LINK_SAVED"] and apply_url and not contact_email:
            logging.info(f"Staging 1-click tailored application kit for {role} at {company} ({apply_url})...")
            kit_path = cover_letter_generator.generate_cover_letter_for_item(item)
            if item.get("status") != "APPLICATION_READY":
                item["status"] = "APPLICATION_READY"
                item["last_action_date"] = today_str
                changes_made = True

    if changes_made:
        save_tracker(data)
        logging.info(f"✅ Successfully submitted {applications_submitted} autonomous job application(s).")
    else:
        logging.info("Autonomous application loop completed. No new applications were submitted.")

    return applications_submitted


if __name__ == "__main__":
    apply_to_pending_jobs()
