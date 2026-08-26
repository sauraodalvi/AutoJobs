import json
import logging
from pathlib import Path
from datetime import datetime, timezone
import config
import candidate_profile
import job_fetcher
import contact_finder
import cover_letter_generator
import referral_engine
import auto_applier
import inbox_monitor
import outbound_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def main():
    """Master orchestration workflow for AutoJobs autonomous agent."""
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    logging.info(f"=== AUTOJOBS AUTONOMOUS AGENT STARTING ({now_utc}) ===")
    logging.info(f"Candidate Profile Loaded: {config.CANDIDATE_NAME} ({config.CANDIDATE_EMAIL})")
    logging.info(f"Targeting: {candidate_profile.TARGET_ROLES_STR}")
    logging.info(f"Locations: {candidate_profile.TARGET_LOCATIONS_STR}")

    # Step 1: Sync and discover target job leads for Pune, EU, Japan, Singapore, Indonesia & Remote
    logging.info("\n--- STEP 1: Syncing Targeted Job Leads (PM / APM) ---")
    try:
        job_fetcher.sync_target_jobs()
    except Exception as e:
        logging.error(f"Job fetcher step encountered an error: {e}")

    # Step 2: Run contact_finder to auto-discover & MX-validate recruiter emails
    logging.info("\n--- STEP 2: Running Verified Recruiter Contact Discovery & Enrichment ---")
    try:
        contact_finder.enrich_saved_leads()
    except Exception as e:
        logging.error(f"Contact finder step encountered an error: {e}")

    # Step 3: Pre-generate tailored application kits & referral dossiers
    logging.info("\n--- STEP 3: Synthesizing Tailored Kits, Cover Letters & Referral Dossiers ---")
    try:
        cover_letter_generator.generate_kits_for_all_saved_leads(max_kits=5)
        referral_engine.generate_all_referral_dossiers()
    except Exception as e:
        logging.error(f"Cover letter and referral kit generator encountered an error: {e}")

    # Step 4: Run auto_applier to submit applications for leads with verified hiring endpoints
    logging.info("\n--- STEP 4: Running Autonomous Job Applier (Direct Email & Web Submissions) ---")
    try:
        auto_applier.apply_to_pending_jobs(max_applications=5)
    except Exception as e:
        logging.error(f"Auto applier step encountered an error: {e}")

    # Step 5: Run inbox_monitor to scrub active threads and flag responses / bounces
    logging.info("\n--- STEP 5: Running Inbox Monitor (IMAP Response & Bounce Scrubbing) ---")
    try:
        inbox_monitor.process_incoming_replies()
    except Exception as e:
        logging.error(f"Inbox monitor step encountered an error: {e}")

    # Step 6: Run outbound_engine to fire new verified referral pitches & follow-ups
    logging.info("\n--- STEP 6: Running Outbound Engine (Verified Pitches & Follow-ups) ---")
    try:
        outbound_engine.execute_daily_sequence()
    except Exception as e:
        logging.error(f"Outbound engine step encountered an error: {e}")

    # Step 7: Dispatch 09:00 AM Daily Morning Briefing Digest to Candidate
    logging.info("\n--- STEP 7: Generating 09:00 AM Daily Action Briefing ---")
    try:
        outbound_engine.send_daily_digest()
    except Exception as e:
        logging.error(f"Daily digest dispatch encountered an error: {e}")

    logging.info("\n=== AUTOJOBS AUTONOMOUS AGENT FINISHED ===")


if __name__ == "__main__":
    main()
