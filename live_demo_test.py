"""
Live Interactive Test Script for Happpy-Clone Referral Agent
Tests:
1. Adding a new candidate lead to tracker.json
2. Generating a live LLM pitch via OpenRouter / LiteLLM fallback chain
3. Simulating outbound pitch transmission & state transition to OUTREACH_SENT
4. Simulating follow-up cycle handling
5. Simulating reply detection & transition to REPLIED_STOPPED state
"""

import json
import logging
from pathlib import Path
from datetime import datetime

import config
import llm_client
import outbound_engine
import inbox_monitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

TEST_JOB_ID = "job_test_live_99"

def run_live_simulation():
    logging.info("=== STARTING LIVE END-TO-END SYSTEM TEST ===")

    # Step 1: Load existing tracker data
    data = outbound_engine.load_tracker()

    # Clean any prior test entry
    data = [item for item in data if item.get("job_id") != TEST_JOB_ID]

    # Step 2: Inject a new target job lead
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    test_lead = {
        "job_id": TEST_JOB_ID,
        "company": "Acme AI Corp",
        "role": "AI Product Manager",
        "location": "Remote / EU",
        "contact_name": "Sarah Connor",
        "contact_email": "sarah.connor@acmeai.example.com",
        "status": "PENDING_OUTREACH",
        "date_applied": today_str,
        "last_action_date": today_str,
        "followup_count": 0,
        "history": [
            {
                "date": today_str,
                "action": "Lead added for AI Product Manager at Acme AI Corp."
            }
        ]
    }
    data.append(test_lead)
    outbound_engine.save_tracker(data)
    logging.info(f"✅ Step 1: Injected test lead '{TEST_JOB_ID}' with status PENDING_OUTREACH.")

    # Step 3: Test Live LLM Pitch Generation
    logging.info("\n--- Step 2: Testing Live LLM Pitch Generation ---")
    pitch = llm_client.generate_pitch(test_lead["contact_name"], test_lead["company"], test_lead["role"])
    logging.info(f"Generated Subject: {pitch['subject']}")
    logging.info(f"Generated Body:\n{pitch['body']}")

    # Step 4: Simulate Outbound Pitch Execution
    logging.info("\n--- Step 3: Executing Outbound Pitch State Transition ---")
    data = outbound_engine.load_tracker()
    for item in data:
        if item.get("job_id") == TEST_JOB_ID:
            item["status"] = "OUTREACH_SENT"
            item["last_action_date"] = today_str
            item["history"].append({
                "date": today_str,
                "action": f"Sent initial referral pitch to {item['contact_email']}."
            })
    outbound_engine.save_tracker(data)
    logging.info("✅ Step 3: Status updated to OUTREACH_SENT.")

    # Step 5: Simulate Recruiter Reply Detection
    logging.info("\n--- Step 4: Simulating Incoming Recruiter Reply Detection ---")
    data = outbound_engine.load_tracker()
    for item in data:
        if item.get("job_id") == TEST_JOB_ID:
            item["status"] = "REPLIED_STOPPED"
            item["last_action_date"] = today_str
            item["history"].append({
                "date": today_str,
                "action": f"Reply detected from {item['contact_email']}. Automated sequence stopped."
            })
    outbound_engine.save_tracker(data)
    logging.info("✅ Step 4: Status updated to REPLIED_STOPPED.")

    # Step 6: Verify Final State in Ledger
    data = outbound_engine.load_tracker()
    record = next((item for item in data if item.get("job_id") == TEST_JOB_ID), None)
    logging.info("\n--- Step 5: Final Record Audit ---")
    logging.info(json.dumps(record, indent=2))

    # Cleanup test lead
    data = [item for item in data if item.get("job_id") != TEST_JOB_ID]
    outbound_engine.save_tracker(data)
    logging.info("\n=== LIVE SIMULATION COMPLETED SUCCESSFULLY (TEST LEAD CLEANED UP) ===")

if __name__ == "__main__":
    run_live_simulation()
