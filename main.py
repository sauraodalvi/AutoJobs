import json
import logging
from pathlib import Path
import config
import candidate_profile
import job_fetcher
import inbox_monitor
import outbound_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def main():
    """Master orchestration workflow for Happpy-Clone autonomous agent."""
    logging.info("=== HAPPPY-CLONE AUTONOMOUS AGENT STARTING ===")
    logging.info(f"Candidate Profile Loaded: {config.CANDIDATE_NAME} ({config.CANDIDATE_EMAIL})")
    logging.info(f"Targeting: {candidate_profile.TARGET_ROLES_STR}")
    logging.info(f"Locations: {candidate_profile.TARGET_LOCATIONS_STR}")

    # Step 1: Sync and discover target job leads for Pune, EU, Japan, Singapore, Indonesia & Remote
    logging.info("\n--- STEP 1: Syncing Targeted Job Leads (PM / APM) ---")
    try:
        job_fetcher.sync_target_jobs()
    except Exception as e:
        logging.error(f"Job fetcher step encountered an error: {e}")

    # Step 1.5: Run contact_finder to auto-discover recruiter emails for saved leads
    logging.info("\n--- STEP 1.5: Running Recruiter Contact Finder & Enrichment ---")
    try:
        import contact_finder
        contact_finder.enrich_saved_leads()
    except Exception as e:
        logging.error(f"Contact finder step encountered an error: {e}")

    # Step 2: Run inbox_monitor to scrub active threads and flag responses
    logging.info("\n--- STEP 2: Running Inbox Monitor (IMAP Response Scrubbing) ---")
    try:
        inbox_monitor.process_incoming_replies()
    except Exception as e:
        logging.error(f"Inbox monitor step encountered an error: {e}")

    # Step 3: Run outbound_engine to fire new pitches & follow-ups
    logging.info("\n--- STEP 3: Running Outbound Engine (Pitches & Follow-ups) ---")
    try:
        outbound_engine.execute_daily_sequence()
    except Exception as e:
        logging.error(f"Outbound engine step encountered an error: {e}")

    logging.info("\n=== HAPPPY-CLONE AUTONOMOUS AGENT FINISHED ===")


if __name__ == "__main__":
    main()
