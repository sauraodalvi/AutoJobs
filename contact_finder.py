"""
Contact Finder & Recruiter Email Enrichment Module
Automates the discovery of verified recruiter/hiring manager names and direct emails for target companies.
Uses email_validator to guarantee RFC compliance and active DNS MX records.
"""

import json
import logging
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import config
import email_validator
import job_fetcher

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def clean_company_domain(company_name: str, apply_url: str = "") -> str:
    """Extracts or infers company root domain using email_validator."""
    return email_validator.clean_company_domain(company_name, apply_url)


def find_recruiter_via_hunter(domain: str, api_key: str = "") -> dict:
    """Queries Hunter.io API for HR / Talent Acquisition contacts at the target domain."""
    if not api_key:
        return {}
    
    try:
        url = f"https://api.hunter.io/v2/domain-search?domain={domain}&department=hr&api_key={api_key}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            emails = data.get("data", {}).get("emails", [])
            for item in emails:
                email_addr = item.get("value", "").strip()
                first_name = item.get("first_name", "")
                last_name = item.get("last_name", "")
                position = item.get("position", "")
                
                is_valid, _ = email_validator.is_valid_recruiter_email(email_addr, verify_mx=True)
                if is_valid:
                    contact_name = f"{first_name} {last_name}".strip() or "Hiring Manager"
                    return {
                        "name": contact_name,
                        "email": email_addr,
                        "title": position or "Talent Acquisition"
                    }
    except Exception as e:
        logging.warning(f"Hunter.io search failed for {domain}: {e}")
    
    return {}


def find_recruiter_via_web_search(company: str, domain: str) -> dict:
    """
    Performs search discovery to find recruiter emails associated with the domain.
    """
    try:
        query = f'"{company}" (recruiter OR "talent acquisition") "@{domain}"'
        encoded_query = urllib.parse.quote(query)
        search_url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        
        req = urllib.request.Request(search_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        with urllib.request.urlopen(req, timeout=4) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            
            # Match email pattern for domain
            email_pattern = r'[a-zA-Z0-9._%+-]+@' + re.escape(domain)
            found_emails = re.findall(email_pattern, html, re.IGNORECASE)
            
            for email in found_emails:
                is_valid, _ = email_validator.is_valid_recruiter_email(email, verify_mx=True)
                if is_valid:
                    # Infer name from email local part (e.g. john.doe@ -> John Doe)
                    local = email.split("@")[0]
                    name_parts = [p.capitalize() for p in local.split(".") if len(p) > 1]
                    name = " ".join(name_parts) if name_parts else "Hiring Manager"
                    return {"name": name, "email": email, "title": "Recruiter"}
    except Exception as e:
        logging.debug(f"Web search recruiter discovery notice for {company}: {e}")

    return {}


def find_probed_talent_channel(company: str, domain: str) -> dict:
    """
    Probes standard talent acquisition channels using zero-send SMTP verification.
    Only returns a contact if the target mail server explicitly confirms with SMTP 250 OK.
    """
    if not domain:
        return {}
    
    candidate_prefixes = ["careers", "jobs", "hiring", "talent", "join", "recruiting"]
    for prefix in candidate_prefixes:
        email_addr = f"{prefix}@{domain}"
        is_deliv, reason = email_validator.verify_smtp_mailbox_deliverable(email_addr, timeout=4)
        if is_deliv and "250" in reason:
            logging.info(f"Verified live recipient mailbox: {email_addr} ({reason})")
            return {
                "name": f"{company} Talent Acquisition Team",
                "email": email_addr,
                "title": "Hiring Team"
            }
    return {}


def discover_contact(company: str, apply_url: str = "") -> dict:
    """
    Attempts multi-source discovery for recruiter or talent acquisition contact info.
    Returns dict with 'name' and 'email' ONLY if a confirmed verified email is found.
    NEVER generates speculative/guessed emails to prevent bounces.
    """
    domain = clean_company_domain(company, apply_url)
    if not domain:
        return {}

    # 1. Try Hunter.io API if key configured
    hunter_key = getattr(config, "HUNTER_API_KEY", "") or getattr(config, "HUNTER_KEY", "")
    if hunter_key:
        contact = find_recruiter_via_hunter(domain, hunter_key)
        if contact and contact.get("email"):
            return contact

    # 2. Try Web search pattern matching for explicitly published recruiter emails
    contact = find_recruiter_via_web_search(company, domain)
    if contact and contact.get("email"):
        return contact

    # 3. Try Live Zero-Send SMTP Probe for standard talent acquisition channels
    contact = find_probed_talent_channel(company, domain)
    if contact and contact.get("email"):
        return contact

    return {}


def enrich_saved_leads() -> int:
    """
    Scans tracker.json ledger for JOB_LINK_SAVED leads,
    attempts automatic recruiter discovery, and promotes them to PENDING_OUTREACH.
    """
    data = job_fetcher.load_tracker()
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    enriched_count = 0

    for record in data:
        if record.get("status") == "JOB_LINK_SAVED" or not record.get("contact_email"):
            company = record.get("company", "")
            apply_url = record.get("apply_url", "")
            
            logging.info(f"Checking verified recruiter contact discovery for: {company}...")
            try:
                discovered = discover_contact(company, apply_url)
            except Exception as e:
                logging.warning(f"Error discovering contact for {company}: {e}")
                discovered = {}

            if discovered and discovered.get("email"):
                rec_name = discovered.get("name", "Hiring Manager")
                rec_email = discovered.get("email", "")
                
                record["contact_name"] = rec_name
                record["contact_email"] = rec_email
                record["status"] = "PENDING_OUTREACH"
                record["last_action_date"] = today_str
                record["history"].append({
                    "date": today_str,
                    "action": f"Discovered verified recruiter contact {rec_name} ({rec_email}). Promoted to PENDING_OUTREACH."
                })
                enriched_count += 1
                logging.info(f"✨ Discovered verified recruiter for {company}: {rec_name} <{rec_email}> -> Promoted to PENDING_OUTREACH")

    if enriched_count > 0:
        job_fetcher.save_tracker(data)
        logging.info(f"Successfully enriched {enriched_count} saved lead(s) with verified recruiter contact details.")
    else:
        logging.info("Recruiter discovery pass complete. (No unverified emails added)")

    return enriched_count


if __name__ == "__main__":
    logging.info("Running manual recruiter contact enrichment pass...")
    enrich_saved_leads()
