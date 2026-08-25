import unittest
import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

import config
import candidate_profile
import llm_client
import job_fetcher
import contact_finder
import cover_letter_generator
import inbox_monitor
import outbound_engine
import email_validator


class TestReferralAgent(unittest.TestCase):

    def setUp(self):
        self.test_tracker = Path(__file__).parent / "test_tracker.json"
        self.original_tracker = config.TRACKER_FILE
        config.TRACKER_FILE = self.test_tracker
        if self.test_tracker.exists():
            self.test_tracker.unlink()
        
        # Cleanup test cover letter files if present
        test_kit = cover_letter_generator.OUTPUT_DIR / "Delta_Health_AI_Product_Manager.txt"
        if test_kit.exists():
            test_kit.unlink()

    def tearDown(self):
        config.TRACKER_FILE = self.original_tracker
        if self.test_tracker.exists():
            self.test_tracker.unlink()
            
        test_kit = cover_letter_generator.OUTPUT_DIR / "Delta_Health_AI_Product_Manager.txt"
        if test_kit.exists():
            test_kit.unlink()

    def test_candidate_profile_context(self):
        context = candidate_profile.get_context_prompt()
        self.assertIn("Saurao Dalvi", context)
        self.assertIn("AI Product Manager", context)
        self.assertIn("FlytBase", context)

    def test_email_validator_syntax(self):
        self.assertTrue(email_validator.validate_email_syntax("john.doe@company.com"))
        self.assertTrue(email_validator.validate_email_syntax("sauraodalvi97@gmail.com"))
        self.assertFalse(email_validator.validate_email_syntax("invalid-email"))
        self.assertFalse(email_validator.validate_email_syntax("john@"))
        self.assertFalse(email_validator.validate_email_syntax("@company.com"))

    def test_email_validator_generic_blocking(self):
        self.assertTrue(email_validator.is_generic_or_role_email("noreply@company.com"))
        self.assertTrue(email_validator.is_generic_or_role_email("careers@company.com"))
        self.assertTrue(email_validator.is_generic_or_role_email("jobs@company.com"))
        self.assertTrue(email_validator.is_generic_or_role_email("support@company.com"))
        self.assertFalse(email_validator.is_generic_or_role_email("sarah.connor@company.com"))

    def test_email_validator_domain_cleaning(self):
        self.assertEqual(email_validator.clean_company_domain("jobs - Personio"), "personio.com")
        self.assertEqual(email_validator.clean_company_domain("FlytBase, Inc."), "flytbase.com")
        self.assertEqual(email_validator.clean_company_domain("Acme Corp [Remote]"), "acme.com")
        self.assertEqual(
            email_validator.clean_company_domain("Revolut", "https://jobs.revolut.com/apply/123"),
            "revolut.com"
        )

    @patch("email_validator.has_valid_mx_record", return_value=True)
    def test_job_fetcher_sync_and_deduplication(self, mock_mx):
        sample_jobs = [
            {
                "company": "TestCorp",
                "role": "Product Manager",
                "location": "Pune, India",
                "contact_name": "Alice Recruiter",
                "contact_email": "alice@testcorp.com",
                "apply_url": "https://testcorp.com/jobs/pm"
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
    def test_llm_recruiter_pitch_and_followup(self, mock_llm):
        mock_llm.side_effect = Exception("LLM simulated offline")
        pitch = llm_client.generate_pitch("Priya Chowdhary", "Valiance Solutions", "Product Manager", "https://linkedin.com/jobs/123", style="recruiter")
        self.assertEqual(pitch["subject"], "Note on my Valiance Solutions Product Manager application")
        self.assertIn("Priya Chowdhary", pitch["body"])
        self.assertIn("Valiance Solutions", pitch["body"])
        self.assertIn("https://linkedin.com/jobs/123", pitch["body"])

        followup = llm_client.generate_followup("Priya Chowdhary", "Valiance Solutions", "Product Manager", style="recruiter")
        self.assertEqual(followup["subject"], "Re: Note on my Valiance Solutions Product Manager application")
        self.assertIn("Priya Chowdhary", followup["body"])

    @patch("llm_client._call_llm_with_fallbacks")
    def test_llm_referral_pitch_and_followup(self, mock_llm):
        mock_llm.side_effect = Exception("LLM simulated offline")
        pitch = llm_client.generate_pitch("Nitisha Varun", "UKG", "Sr Product Manager", "https://linkedin.com/jobs/456", style="referral")
        self.assertEqual(pitch["subject"], "Applying for Sr Product Manager at UKG – can you help with referral?")
        self.assertIn("Nitisha", pitch["body"])
        self.assertIn("FlytBase", pitch["body"])
        self.assertIn("https://sauraodalvi.netlify.app/", pitch["body"])
        self.assertIn("https://linkedin.com/jobs/456", pitch["body"])

        followup = llm_client.generate_followup("Nitisha Varun", "UKG", "Sr Product Manager", style="referral")
        self.assertEqual(followup["subject"], "Re: Applying for Sr Product Manager at UKG – can you help with referral?")
        self.assertIn("Nitisha Varun", followup["body"])

    def test_email_cleaner(self):
        self.assertEqual(inbox_monitor.clean_email_address("Recruiter <recruiter@example.com>"), "recruiter@example.com")
        self.assertEqual(inbox_monitor.clean_email_address("RECRUITER@EXAMPLE.COM "), "recruiter@example.com")

    @patch("time.sleep")
    @patch("outbound_engine.send_email", return_value=True)
    @patch("llm_client.generate_pitch", return_value={"subject": "Pitch", "body": "Pitch body"})
    @patch("email_validator.has_valid_mx_record", return_value=True)
    def test_outbound_engine_state_transitions(self, mock_mx, mock_pitch, mock_send_email, mock_sleep):
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
        self.assertIn("Sent initial pitch", data[0]["history"][0]["action"])
        mock_send_email.assert_called_once()

    @patch("outbound_engine.send_email", return_value=True)
    def test_daily_digest_generation(self, mock_send_email):
        initial_data = [
            {
                "job_id": "test_002",
                "company": "Gamma AI",
                "role": "Lead Product Manager",
                "location": "Remote",
                "contact_name": "Carol Manager",
                "contact_email": "",
                "apply_url": "https://gamma.ai/jobs/lead-pm",
                "status": "APPLICATION_READY",
                "date_applied": "2026-08-26",
                "last_action_date": "2026-08-26",
                "followup_count": 0,
                "history": []
            }
        ]
        with open(self.test_tracker, "w", encoding="utf-8") as f:
            json.dump(initial_data, f)

        sent = outbound_engine.send_daily_digest("test@example.com")
        self.assertTrue(sent)
        mock_send_email.assert_called_once()
        args, kwargs = mock_send_email.call_args
        self.assertIn("Morning Briefing", args[1])
        self.assertIn("Gamma AI", args[2])

    @patch("llm_client._call_llm_with_fallbacks", return_value="Tailored Cover Letter Content Here")
    def test_cover_letter_kit_generation(self, mock_llm):
        initial_data = [
            {
                "job_id": "test_003",
                "company": "Delta Health",
                "role": "AI Product Manager",
                "location": "Pune, India",
                "contact_name": "Hiring Team",
                "contact_email": "",
                "apply_url": "https://deltahealth.io/careers/ai-pm",
                "status": "JOB_LINK_SAVED",
                "date_applied": "2026-08-26",
                "last_action_date": "2026-08-26",
                "followup_count": 0,
                "history": []
            }
        ]
        with open(self.test_tracker, "w", encoding="utf-8") as f:
            json.dump(initial_data, f)

        kits = cover_letter_generator.generate_kits_for_all_saved_leads(max_kits=1)
        self.assertEqual(kits, 1)
        data = job_fetcher.load_tracker()
        self.assertEqual(data[0]["status"], "APPLICATION_READY")


if __name__ == "__main__":
    unittest.main()
