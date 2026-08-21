import unittest
import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

import config
import candidate_profile
import llm_client
import job_fetcher
import inbox_monitor
import outbound_engine

class TestReferralAgent(unittest.TestCase):

    def setUp(self):
        # Create a temporary test tracker file
        self.test_tracker = Path(__file__).parent / "test_tracker.json"
        self.original_tracker = config.TRACKER_FILE
        config.TRACKER_FILE = self.test_tracker
        if self.test_tracker.exists():
            self.test_tracker.unlink()

    def tearDown(self):
        config.TRACKER_FILE = self.original_tracker
        if self.test_tracker.exists():
            self.test_tracker.unlink()

    def test_candidate_profile_context(self):
        context = candidate_profile.get_context_prompt()
        self.assertIn("Saurao Dalvi", context)
        self.assertIn("AI Product Manager", context)
        self.assertIn("FlytBase", context)

    def test_job_fetcher_sync_and_deduplication(self):
        sample_jobs = [
            {
                "company": "TestCorp",
                "role": "Product Manager",
                "location": "Pune, India",
                "contact_name": "Alice Recruiter",
                "contact_email": "alice@testcorp.com"
            }
        ]
        
        # Initial sync
        job_fetcher.sync_target_jobs(new_jobs_list=sample_jobs)
        data = job_fetcher.load_tracker()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["company"], "TestCorp")
        self.assertEqual(data[0]["status"], "PENDING_OUTREACH")

        # Duplicate sync - should NOT add duplicate
        job_fetcher.sync_target_jobs(new_jobs_list=sample_jobs)
        data_after = job_fetcher.load_tracker()
        self.assertEqual(len(data_after), 1)

    @patch("llm_client._call_llm_with_fallbacks")
    def test_llm_pitch_fallback(self, mock_llm):
        mock_llm.return_value = "Subject: Test Subject\n\nThis is line 1. Line 2 impact. Line 3 call to action."
        pitch = llm_client.generate_pitch("John Doe", "Acme AI", "AI Product Manager")
        self.assertEqual(pitch["subject"], "Test Subject")
        self.assertIn("line 1", pitch["body"])

    def test_email_cleaner(self):
        self.assertEqual(inbox_monitor.clean_email_address("Recruiter <recruiter@example.com>"), "recruiter@example.com")
        self.assertEqual(inbox_monitor.clean_email_address("RECRUITER@EXAMPLE.COM "), "recruiter@example.com")

    @patch("time.sleep")
    @patch("outbound_engine.send_email", return_value=True)
    @patch("llm_client.generate_pitch", return_value={"subject": "Pitch", "body": "Pitch body"})
    def test_outbound_engine_state_transitions(self, mock_pitch, mock_send_email, mock_sleep):
        initial_data = [
            {
                "job_id": "test_001",
                "company": "Beta Inc",
                "role": "Associate Product Manager",
                "contact_name": "Bob Hiring",
                "contact_email": "bob@betainc.com",
                "status": "PENDING_OUTREACH",
                "date_applied": "2026-08-20",
                "last_action_date": "2026-08-20",
                "followup_count": 0,
                "history": []
            }
        ]
        with open(self.test_tracker, "w", encoding="utf-8") as f:
            json.dump(initial_data, f)

        # Execute daily sequence
        outbound_engine.execute_daily_sequence()

        data = outbound_engine.load_tracker()
        self.assertEqual(data[0]["status"], "OUTREACH_SENT")
        self.assertEqual(len(data[0]["history"]), 1)
        self.assertIn("Sent initial referral pitch", data[0]["history"][0]["action"])
        mock_send_email.assert_called_once()

if __name__ == "__main__":
    unittest.main()
