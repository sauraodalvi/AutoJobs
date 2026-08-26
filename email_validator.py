"""
Email Validator & Domain Sanitizer Module.
Provides RFC syntax validation, generic role-account filtering,
and DNS MX record deliverability checking to eliminate bouncing or fake email targets.
"""

import logging
import os
import re
import socket
import subprocess
import urllib.parse
from functools import lru_cache

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Known job boards, aggregators, and ATS hosting platforms that should not be used as company root domains
ATS_AND_JOB_BOARD_HOSTS = {
    "linkedin.com", "indeed.com", "glassdoor.com", "ziprecruiter.com",
    "jobicy.com", "remotive.com", "arbeitnow.com", "remoteok.com", "himalayas.app",
    "greenhouse.io", "lever.co", "workday.com", "myworkdayjobs.com",
    "smartrecruiters.com", "ashbyhq.com", "bamboohr.com", "breezy.hr",
    "recruitee.com", "pinpointhq.com", "join.com", "wellfound.com", "angel.co",
    "otta.com", "workable.com", "ycombinator.com", "polywork.com"
}

# Generic unmonitored / bounce-prone prefixes that should NEVER be emailed cold
DEAD_OR_BOUNCE_PREFIXES = {
    "noreply", "no-reply", "donotreply", "do-not-reply", "postmaster",
    "mailer-daemon", "bounce", "unsubscribe", "admin", "administrator",
    "support", "help", "billing", "info", "sales", "inquiries", "contact",
    "general", "office", "security", "privacy", "legal"
}

# Legitimate company talent acquisition and recruiting inboxes for applications
VALID_HIRING_PREFIXES = {
    "jobs", "careers", "apply", "recruiting", "recruitment", "talent",
    "hiring", "hr", "people", "join", "team"
}

GENERIC_ROLE_PREFIXES = DEAD_OR_BOUNCE_PREFIXES

# Permanently blacklisted email addresses confirmed bounced from Gmail delivery reports
PERMANENTLY_BLACKLISTED_EMAILS = {
    "hiring@hitachienergy.com",   # Microsoft 365 group - sender not allowed
    "careers@motive.com",          # Confirmed delivery failure via messagelabs
}

# Regex for standard RFC 5322 email syntax
EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$"
)


def validate_email_syntax(email: str) -> bool:
    """Checks if the email string adheres to RFC 5322 format."""
    if not email or not isinstance(email, str):
        return False
    email = email.strip()
    if len(email) > 254 or len(email) < 6 or "@" not in email:
        return False
    return bool(EMAIL_REGEX.match(email))


def is_generic_or_role_email(email: str) -> bool:
    """Returns True if the email is an unmonitored dead/bounce address."""
    if not email or "@" not in email:
        return True
    local_part = email.split("@")[0].lower().strip()
    if local_part in DEAD_OR_BOUNCE_PREFIXES:
        return True
    for prefix in DEAD_OR_BOUNCE_PREFIXES:
        if local_part.startswith(f"{prefix}-") or local_part.startswith(f"{prefix}."):
            return True
    return False


def is_hiring_channel_email(email: str) -> bool:
    """Returns True if the email belongs to a recognized company hiring/recruiting inbox."""
    if not email or "@" not in email:
        return False
    local_part = email.split("@")[0].lower().strip()
    if local_part in VALID_HIRING_PREFIXES:
        return True
    for prefix in VALID_HIRING_PREFIXES:
        if local_part.startswith(f"{prefix}-") or local_part.startswith(f"{prefix}."):
            return True
    return False


@lru_cache(maxsize=256)
def has_valid_mx_record(domain: str) -> bool:
    """
    Verifies that the target domain has active Mail Exchange (MX) or DNS host records.
    Uses nslookup / dig or socket fallback. Cached to avoid repeat DNS lookups.
    """
    if not domain or "." not in domain or len(domain) < 4:
        return False

    domain = domain.lower().strip()
    
    # Check if dnspython is installed
    try:
        import dns.resolver
        try:
            records = dns.resolver.resolve(domain, 'MX', lifetime=4)
            if records and len(records) > 0:
                return True
        except Exception:
            pass
    except ImportError:
        pass

    # Standard tool: nslookup (Windows and POSIX)
    try:
        cmd = ["nslookup", "-type=mx", domain]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=4)
        output = (res.stdout or "").lower()
        err_output = (res.stderr or "").lower()
        
        # If error indicates non-existent domain
        if "non-existent domain" in err_output or "can't find" in err_output or "server failed" in err_output:
            return False

        if "mail exchanger" in output or "mx preference" in output:
            return True
    except Exception:
        pass

    # Socket host resolution fallback (A / AAAA record check)
    try:
        socket.gethostbyname(domain)
        return True
    except (socket.gaierror, socket.herror, socket.timeout):
        return False


def clean_company_domain(company_name: str, apply_url: str = "") -> str:
    """
    Extracts or infers a clean, legitimate company root domain.
    Strips noise like 'jobs - ', ', Inc.', ATS subdomains, etc.
    """
    # 1. First attempt from apply_url if not an aggregator / ATS
    if apply_url:
        try:
            parsed = urllib.parse.urlparse(apply_url)
            netloc = parsed.netloc.lower().split(":")[0]
            # Strip subdomains like www, jobs, careers, apply, portal, boards
            parts = netloc.split(".")
            if len(parts) >= 2:
                root_domain = ".".join(parts[-2:])
                full_host = ".".join(parts)
                if not any(ats in full_host for ats in ATS_AND_JOB_BOARD_HOSTS):
                    # Clean out subdomains
                    cleaned_host = re.sub(r"^(www|jobs|careers|apply|portal|boards|app)\.", "", full_host)
                    if "." in cleaned_host:
                        return cleaned_host
        except Exception:
            pass

    # 2. Extract from company name
    if not company_name:
        return ""

    comp = company_name.strip()
    # Strip common prefixes like 'jobs - ', 'careers - '
    comp = re.sub(r"^(jobs\s*-\s*|careers\s*-\s*|hiring\s*-\s*)", "", comp, flags=re.IGNORECASE)
    # Strip bracketed locations or notes like [España] or (Remote)
    comp = re.sub(r"\[.*?\]|\(.*?\)", "", comp)
    # Strip corporate legal suffixes
    comp = re.sub(
        r"\b(inc|incorporated|llc|ltd|limited|gmbh|co|corp|corporation|technologies|technology|group|holdings|services|solutions|pvt|private)\b\.?",
        "", comp, flags=re.IGNORECASE
    )
    # Clean non-alphanumeric
    cleaned_name = re.sub(r"[^a-zA-Z0-9]", "", comp.lower())
    if cleaned_name and len(cleaned_name) > 1:
        return f"{cleaned_name}.com"

    return ""


def is_valid_recruiter_email(email: str, verify_mx: bool = True, allow_hiring_channels: bool = True) -> tuple[bool, str]:
    """
    Comprehensive validation for recruiter and hiring emails.
    Returns (is_valid: bool, reason: str).
    """
    if not email or not isinstance(email, str):
        return False, "Empty or non-string email"

    email = email.strip().lower()

    # Check against permanently blacklisted emails (confirmed bounced from delivery reports)
    if email in PERMANENTLY_BLACKLISTED_EMAILS:
        return False, f"Permanently blacklisted email address (confirmed bounce): {email}"

    if not validate_email_syntax(email):
        return False, "Invalid email syntax"

    if is_generic_or_role_email(email):
        return False, f"Dead/unmonitored or bounce-prone role prefix ({email.split('@')[0]})"

    if not allow_hiring_channels and is_hiring_channel_email(email):
        return False, f"Role-based hiring channel not allowed for direct personal pitch ({email.split('@')[0]})"

    domain = email.split("@")[1]
    if domain in ATS_AND_JOB_BOARD_HOSTS:
        return False, f"ATS or job aggregator domain ({domain})"

    if verify_mx and not has_valid_mx_record(domain):
        return False, f"Domain {domain} has no valid MX or DNS records"

    return True, "Valid"


def verify_smtp_mailbox_deliverable(email: str, timeout: int = 5) -> tuple[bool, str]:
    """
    Performs a live zero-send SMTP RCPT TO probe against the destination MX server.
    Returns (is_deliverable: bool, reason: str).
    Guarantees that a mailbox exists on the remote mail server before sending any email.
    """
    is_syntax_valid, reason = is_valid_recruiter_email(email, verify_mx=True)
    if not is_syntax_valid:
        return False, reason

    domain = email.split("@")[1].lower()
    try:
        import dns.resolver
        import smtplib
        records = dns.resolver.resolve(domain, 'MX', lifetime=timeout)
        if not records or len(records) == 0:
            return False, f"No MX records found for {domain}"
        
        mx_host = sorted(records, key=lambda r: r.preference)[0].exchange.to_text().rstrip('.')
        
        s = smtplib.SMTP(timeout=timeout)
        s.connect(mx_host, 25)
        s.helo("gmail.com")
        s.mail("sauraodalvi97@gmail.com")
        code, msg = s.rcpt(email)
        s.quit()
        
        msg_str = msg.decode(errors="ignore") if isinstance(msg, bytes) else str(msg)
        if code == 250:
            return True, f"Mailbox verified (SMTP 250: {msg_str[:60]})"
        elif code in [550, 551, 553, 554]:
            return False, f"Mailbox rejected (SMTP {code}: {msg_str[:60]})"
        else:
            return False, f"Mailbox unconfirmed (SMTP status {code})"
    except Exception as e:
        # If port 25 is firewalled/restricted, NEVER assume speculative emails are valid
        return False, f"SMTP probe unavailable/unconfirmed ({e})"

