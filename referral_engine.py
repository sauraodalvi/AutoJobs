"""
Referral Engine & Strategic Outreach Toolkit.
Inspired by Career-Ops and top executive recruiting workflows.
Generates structured multi-tier fit evaluations (1-5 Stars), LinkedIn referrer search URLs,
and pre-written zero-friction referral request packets for employee & hiring manager networking.
"""

import json
import logging
import re
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import config
import candidate_profile
import ats_optimizer
import llm_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

REFERRAL_DIR = Path("referrals")
REFERRAL_DIR.mkdir(exist_ok=True)


def calculate_referral_priority(role: str, company: str, location: str = "", description: str = "") -> Tuple[int, str]:
    """
    Computes a 1-5 star priority score and strategic fit summary for the job opening.
    5 Stars: Tier-1 target (AI PM, 0-to-1, high alignment in target geos)
    4 Stars: Strong fit (Senior PM, Enterprise SaaS)
    3 Stars: Good standard fit
    """
    combined = f"{role} {company} {location} {description}".lower()
    score = 3
    reasons = []

    # AI / LLM Domain Alignment
    if any(k in combined for k in ["ai product", "generative ai", "llm", "agentic", "machine learning"]):
        score += 1
        reasons.append("High AI/LLM Domain Alignment")

    # Target Geo Alignment (Pune, EU, Japan, Singapore, Indonesia, Remote)
    if config.is_target_location(location) or any(loc in combined for loc in ["pune", "remote", "singapore", "japan", "tokyo", "germany", "berlin", "eu", "indonesia", "jakarta", "london", "uk", "netherlands"]):
        score += 1
        reasons.append("Target Geographic Alignment (Pune / EU / Japan / Singapore / Indonesia / Remote)")

    # Seniority / Role Fit
    if any(t in role.lower() for t in ["product manager", "associate product manager", "apm", "sr. product manager", "senior product manager"]):
        reasons.append("Core PM Role Match")

    final_stars = min(max(score, 1), 5)
    summary = " | ".join(reasons) if reasons else "General PM Alignment"
    return final_stars, summary


def generate_linkedin_search_url(company: str, role_title: str = "Product Manager", location: str = "") -> str:
    """
    Generates a targeted LinkedIn People Search URL to instantly find PM peers,
    Engineering Leads, and Recruiters at the company in preferred locations.
    """
    clean_company = re.sub(r"[^a-zA-Z0-9\s]", "", company).strip()
    loc_lower = (location or "").lower()
    
    clean_loc = ""
    if "pune" in loc_lower:
        clean_loc = "Pune"
    elif "singapore" in loc_lower:
        clean_loc = "Singapore"
    elif any(k in loc_lower for k in ["japan", "tokyo"]):
        clean_loc = "Japan"
    elif any(k in loc_lower for k in ["indonesia", "jakarta"]):
        clean_loc = "Indonesia"
    elif any(k in loc_lower for k in ["germany", "berlin", "munich"]):
        clean_loc = "Germany"
    elif any(k in loc_lower for k in ["uk", "london", "united kingdom"]):
        clean_loc = "London"
    elif any(k in loc_lower for k in ["netherlands", "amsterdam"]):
        clean_loc = "Netherlands"
    
    query_parts = [clean_company, "Product Manager"]
    if clean_loc:
        query_parts.append(clean_loc)
    
    query = " ".join(query_parts)
    encoded = urllib.parse.quote(query)
    return f"https://www.linkedin.com/search/results/people/?keywords={encoded}&origin=GLOBAL_SEARCH_HEADER"


def generate_referral_packet(job: dict) -> Dict[str, str]:
    """
    Generates a complete multi-touch referral request kit for a target company:
    1. LinkedIn Peer / Alumni Connection Message (<300 chars for InMail/Connect note)
    2. Forwardable Employee-to-HR Referrer Blurb (Zero effort for the referrer)
    3. Direct Hiring Manager Pitch (Direct value proposition)
    """
    company = job.get("company", "Company")
    role = job.get("role", "Product Manager")
    loc = job.get("location", "Remote")
    apply_url = job.get("apply_url", "")
    stars, fit_reason = calculate_referral_priority(role, company, loc, job.get("description", ""))

    ats_score, keywords = ats_optimizer.calculate_match_score(role, job.get("description", ""), company)
    kw_str = ", ".join(keywords[:3]) if keywords else "AI Product Management, 0-to-1 SaaS"

    # 1. Peer / Alumni Referral Request (Strictly < 300 chars for LinkedIn Connect Note)
    # LinkedIn Connect notes max out at 300 characters, so we trim verbose role titles
    # (location codes, parenthetical asides, long suffixes) to guarantee the note fits.
    MAX_CONNECT_NOTE = 300

    def _shorten_role(label: str, budget: int = 45) -> str:
        label = re.sub(r"[\(\[].*?[\)\]]", "", label)
        label = re.sub(r"\s+", " ", label).strip(" -–,;")
        return label[:budget].rstrip(" -–,;") if len(label) > budget else label

    short_role = _shorten_role(role)
    peer_message = (
        f"Hi [Name], saw your work at {company}! Applying for {short_role}. "
        f"With 3+ yrs scaling 0-to-1 AI SaaS at FlytBase & CrelioHealth, my background maps closely. "
        f"Open to passing my profile along for an internal referral? I have a 2-line blurb ready to make it zero-effort."
    )
    # In case an extremely long company name still pushes us over the limit,
    # drop to the role title alone as a final safety net (still human-readable).
    if len(peer_message) > MAX_CONNECT_NOTE:
        peer_message = (
            f"Hi [Name], saw your work at {company}! I'm applying for a Product Manager role "
            f"at {company} and my background (3+ yrs scaling 0-to-1 AI SaaS at FlytBase & CrelioHealth) "
            f"maps closely. Open to passing my profile along as an internal referral? A 2-line blurb is ready."
        )

    # 2. Forwardable Referrer Blurb (What the employee pastes to their HR portal)
    forwardable_blurb = (
        f"Candidate: {config.CANDIDATE_NAME}\n"
        f"Role Applied: {role}\n"
        f"Job Link: {apply_url}\n"
        f"Overview: AI Product Manager with 3+ years experience scaling 0-to-1 SaaS products at FlytBase & CrelioHealth. "
        f"Track record increasing MRR, launching LLM-driven features, and leading cross-functional teams.\n"
        f"Contact: {config.CANDIDATE_EMAIL} | Phone: {candidate_profile.PHONE}\n"
        f"LinkedIn: {candidate_profile.LINKEDIN_URL}\n"
        f"Portfolio: {candidate_profile.PORTFOLIO_URL}"
    )

    # 3. Direct Hiring Manager Pitch
    hm_pitch = (
        f"Subject: Note regarding {role} opening – {config.CANDIDATE_NAME}\n\n"
        f"Dear Hiring Team,\n\n"
        f"I noticed {company} is looking for a {role}. As an AI Product Manager with 3+ years experience driving 0-to-1 "
        f"B2B SaaS products at FlytBase and CrelioHealth, I specialize in shipping LLM workflows, customer-centric features, and MRR growth.\n\n"
        f"Key Highlights:\n"
        f"• Shipped 0-to-1 AI SaaS platform (Prediq) scaling commercial adoption.\n"
        f"• Scaled SaaS features increasing lab revenue by ~$2k MRR per account.\n"
        f"• Deep technical grounding in LLM architectures, analytics, and agile execution.\n\n"
        f"I would love to learn more about your team's roadmap and share how my experience can accelerate your goals.\n\n"
        f"Best regards,\n{config.CANDIDATE_NAME}\n{candidate_profile.LINKEDIN_URL}"
    )

    linkedin_search = generate_linkedin_search_url(company, role, loc)

    return {
        "company": company,
        "role": role,
        "stars": stars,
        "fit_reason": fit_reason,
        "ats_score": ats_score,
        "linkedin_search_url": linkedin_search,
        "peer_message": peer_message,
        "forwardable_blurb": forwardable_blurb,
        "hiring_manager_pitch": hm_pitch
    }


def save_referral_dossier(job: dict) -> Path:
    """Saves formatted referral toolkit to referrals/<Company>_<Role>.txt."""
    packet = generate_referral_packet(job)
    comp_clean = re.sub(r"[^\w\-_\. ]", "_", packet["company"]).strip().replace(" ", "_")
    role_clean = re.sub(r"[^\w\-_\. ]", "_", packet["role"]).strip().replace(" ", "_")
    filename = f"{comp_clean}_{role_clean}.txt"
    filepath = REFERRAL_DIR / filename

    content = f"""================================================================================
⭐ REFERRAL & NETWORKING DOSSIER: {packet['company']} – {packet['role']}
Priority Fit: {'⭐' * packet['stars']} ({packet['stars']}/5) | ATS Match: {packet['ats_score']}%
Fit Highlights: {packet['fit_reason']}
================================================================================

🔍 STEP 1: FIND EMPLOYEES & REFERRERS ON LINKEDIN
1-Click LinkedIn Search:
{packet['linkedin_search_url']}

--------------------------------------------------------------------------------
💬 STEP 2: SEND LOW-FRICTION REFERRAL REQUEST (LinkedIn / InMail)
--------------------------------------------------------------------------------
{packet['peer_message']}

--------------------------------------------------------------------------------
📋 STEP 3: ZERO-EFFORT FORWARDABLE BLURB (For employee to paste to HR)
--------------------------------------------------------------------------------
{packet['forwardable_blurb']}

--------------------------------------------------------------------------------
✉️ STEP 4: DIRECT HIRING MANAGER / FOUNDER PITCH
--------------------------------------------------------------------------------
{packet['hiring_manager_pitch']}
================================================================================
"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return filepath


def generate_all_referral_dossiers() -> int:
    """Scans tracker.json and generates referral dossiers for all target roles."""
    tracker_file = Path("tracker.json")
    if not tracker_file.exists():
        return 0

    with open(tracker_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    blacklist = getattr(config, "BLACKLIST_COMPANIES", [])
    count = 0
    for item in data:
        company = item.get("company", "")
        if any(b.lower() in company.lower() for b in blacklist):
            continue
        try:
            save_referral_dossier(item)
            count += 1
        except Exception as e:
            logging.error(f"Error generating referral dossier for {company}: {e}")

    logging.info(f"✅ Generated {count} comprehensive referral & networking dossiers in {REFERRAL_DIR}")
    return count


if __name__ == "__main__":
    generate_all_referral_dossiers()
