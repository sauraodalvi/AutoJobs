"""
Contact Finder & Recruiter Email Enrichment Module
Automates the discovery of verified recruiter/hiring manager names and direct emails for target companies.
"""

import json
import logging
import re
import urllib.parse
import urllib.request
from pathlib import Path
from datetime import datetime
import config
import job_fetcher

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def clean_company_domain(company_name: str, apply_url: str = "") -> str:
    """Extracts or infers company root domain (e.g., 'FlytBase' -> 'flytbase.com')."""
    if apply_url:
        parsed = urllib.parse.urlparse(apply_url)
        domain = parsed.netloc.replace("www.", "").replace("jobs.", "").replace("careers.", "").split(":")[0]
        if domain and "." in domain and not any(host in domain for host in ["linkedin.com", "indeed.com", "glassdoor.com", "ziprecruiter.com", "jobicy.com", "remotive.com", "arbeitnow.com", "remoteok.com", "himalayas.app"]):
            return domain

    # Fallback: sanitize company name to domain
    cleaned = re.sub(r"[^a-zA-Z0-9]", "", company_name.lower())
    if cleaned:
        return f"{cleaned}.com"
    return ""


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
                email_addr = item.get("value", "")
                first_name = item.get("first_name", "")
                last_name = item.get("last_name", "")
                position = item.get("position", "")
                
                if email_addr and not job_fetcher.is_generic_email(email_addr):
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
    Performs lightweight web search scraping (DuckDuckGo HTML API) to discover recruiter emails / LinkedIn profiles.
    """
    try:
        query = f'"{company}" recruiter OR "talent acquisition" "@ {domain}"'
        encoded_query = urllib.parse.quote(query)
        search_url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        
        req = urllib.request.Request(search_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        with urllib.request.urlopen(req, timeout=3) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            
            # Match email pattern for domain
            email_pattern = r'[a-zA-Z0-9._%+-]+@' + re.escape(domain)
            found_emails = re.findall(email_pattern, html, re.IGNORECASE)
            
            non_generic = [e for e in found_emails if not job_fetcher.is_generic_email(e)]
            if non_generic:
                email = non_generic[0]
                # Infer name from email local part (e.g. john.doe@ -> John Doe)
                local = email.split("@")[0]
                name_parts = [p.capitalize() for p in local.split(".") if len(p) > 1]
                name = " ".join(name_parts) if name_parts else "Hiring Manager"
                return {"name": name, "email": email, "title": "Recruiter"}
    except Exception as e:
        logging.warning(f"Web search recruiter discovery failed for {company}: {e}")

    return {}


def discover_contact(company: str, apply_url: str = "") -> dict:
    """
    Attempts multi-source discovery for recruiter contact info.
    Returns dict with 'name' and 'email' if found.
    """
    domain = clean_company_domain(company, apply_url)
    if not domain:
        return {}

    # 1. Try Hunter.io API if key configured
    hunter_key = getattr(config, "HUNTER_API_KEY", "")
    if hunter_key:
        contact = find_recruiter_via_hunter(domain, hunter_key)
        if contact and contact.get("email"):
            return contact

    # 2. Try DuckDuckGo / Web search pattern matching
    contact = find_recruiter_via_web_search(company, domain)
    if contact and contact.get("email"):
        return contact

    return {}


def enrich_saved_leads() -> int:
    """
    Scans tracker.json ledger for JOB_LINK_SAVED leads,
    attempts automatic recruiter discovery, and promotes them to PENDING_OUTREACH.
    """
    data = job_fetcher.load_tracker()
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    enriched_count = 0
    consecutive_errors = 0

    for record in data:
        if record.get("status") == "JOB_LINK_SAVED":
            if consecutive_errors >= 3:
                logging.info("Web search rate limited or unreachable. Halting enrichment pass for remaining saved leads.")
                break

            company = record.get("company", "")
            apply_url = record.get("apply_url", "")
            
            logging.info(f"Attempting automatic recruiter contact discovery for: {company}...")
            discovered = discover_contact(company, apply_url)
            
            if discovered and discovered.get("email"):
                consecutive_errors = 0
                rec_name = discovered.get("name", "Hiring Manager")
                rec_email = discovered.get("email", "")
                
                record["contact_name"] = rec_name
                record["contact_email"] = rec_email
                record["status"] = "PENDING_OUTREACH"
                record["last_action_date"] = today_str
                record["history"].append({
                    "date": today_str,
                    "action": f"Auto-discovered recruiter contact {rec_name} ({rec_email}). Promoted to PENDING_OUTREACH."
                })
                enriched_count += 1
                logging.info(f"✨ Discovered recruiter for {company}: {rec_name} <{rec_email}> -> Status set to PENDING_OUTREACH")
            else:
                consecutive_errors += 1

    if enriched_count > 0:
        job_fetcher.save_tracker(data)
        logging.info(f"Successfully enriched {enriched_count} saved lead(s) with recruiter contact details.")
    else:
        logging.info("No new recruiter contacts automatically discovered in this pass.")

    return enriched_count


if __name__ == "__main__":
    logging.info("Running manual recruiter contact enrichment pass...")
    enrich_saved_leads()
