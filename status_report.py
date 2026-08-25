"""
Status Report CLI Utility for AutoJobs Referral & Application Agent.
Prints a summary breakdown of tracked job applications, application kits, and referral outreach states.
"""

import json
import logging
import sys
import config
import job_fetcher

# Force UTF-8 output encoding if possible
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def print_status_report():
    data = job_fetcher.load_tracker()
    if not data:
        print("\n[!] No records found in tracker.json database.")
        return

    print("\n==========================================================================================")
    print("                 AUTOJOBS AGENT - JOB & REFERRAL LEDGER STATUS                            ")
    print("==========================================================================================\n")

    summary_counts = {
        "PENDING_OUTREACH": 0,
        "OUTREACH_SENT": 0,
        "FOLLOWUP_SENT": 0,
        "APPLICATION_READY": 0,
        "JOB_LINK_SAVED": 0,
        "EMAIL_BOUNCED": 0,
        "REPLIED_STOPPED": 0
    }

    header_fmt = "{:<18} | {:<32} | {:<28} | {:<18} | {:<10}"
    print(header_fmt.format("Company", "Role", "Recruiter Email", "Status", "Last Action"))
    print("-" * 115)

    for item in data:
        status = item.get("status", "UNKNOWN")
        summary_counts[status] = summary_counts.get(status, 0) + 1
        comp = str(item.get("company", "N/A"))[:17]
        role = str(item.get("role", "N/A"))[:31]
        email = (item.get("contact_email") or "(Direct Apply)")[:27]
        last_date = str(item.get("last_action_date", "N/A"))
        print(header_fmt.format(comp, role, email, status, last_date))

    print("\n--- SUMMARY METRICS ---")
    print(f"[*] Pending Referral Outreaches (Ready to Send): {summary_counts['PENDING_OUTREACH']}")
    print(f"[*] Initial Pitches Sent:                     {summary_counts['OUTREACH_SENT']}")
    print(f"[*] Follow-ups Sent:                          {summary_counts['FOLLOWUP_SENT']}")
    print(f"[*] Tailored Application Kits Ready:          {summary_counts['APPLICATION_READY']}")
    print(f"[*] Direct Job Application Links Saved:       {summary_counts['JOB_LINK_SAVED']}")
    print(f"[*] Email Bounces (Halted):                    {summary_counts['EMAIL_BOUNCED']}")
    print(f"[*] Recruiter Replies (Sequence Stopped):     {summary_counts['REPLIED_STOPPED']}")
    print(f"[*] Total Leads Tracked:                      {len(data)}")
    print("==========================================================================================\n")


if __name__ == "__main__":
    print_status_report()
