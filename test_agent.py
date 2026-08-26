import unittest
import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

import config
import candidate_profile
import llm_client
import job_fetcher
import contact_finder
import cover_letter_generator
import inbox_monitor
import auto_applier
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

    def test_job_freshness_filter(self):
        now = datetime.now(timezone.utc)
        # Recent jobs (within 7 days)
        self.assertTrue(job_fetcher.is_recent_job(now - timedelta(days=2), max_days=7))
        self.assertTrue(job_fetcher.is_recent_job((now - timedelta(days=4)).isoformat(), max_days=7))
        self.assertTrue(job_fetcher.is_recent_job((now - timedelta(days=1)).timestamp(), max_days=7))

        # Stale jobs (> 7 days)
        self.assertFalse(job_fetcher.is_recent_job(now - timedelta(days=10), max_days=7))
        self.assertFalse(job_fetcher.is_recent_job((now - timedelta(days=15)).isoformat(), max_days=7))
        self.assertFalse(job_fetcher.is_recent_job((now - timedelta(days=30)).timestamp(), max_days=7))

    def test_email_validator_syntax(self):
        self.assertTrue(email_validator.validate_email_syntax("john.doe@company.com"))
        self.assertTrue(email_validator.validate_email_syntax("sauraodalvi97@gmail.com"))
        self.assertFalse(email_validator.validate_email_syntax("invalid-email"))
        self.assertFalse(email_validator.validate_email_syntax("john@"))
        self.assertFalse(email_validator.validate_email_syntax("@company.com"))

    def test_email_validator_generic_blocking_and_hiring_channels(self):
        # Dead/bounce prefixes are blocked
        self.assertTrue(email_validator.is_generic_or_role_email("noreply@company.com"))
        self.assertTrue(email_validator.is_generic_or_role_email("postmaster@company.com"))
        self.assertTrue(email_validator.is_generic_or_role_email("billing@company.com"))
        self.assertTrue(email_validator.is_generic_or_role_email("support@company.com"))
        
        # Hiring channels are recognized
        self.assertTrue(email_validator.is_hiring_channel_email("careers@company.com"))
        self.assertTrue(email_validator.is_hiring_channel_email("jobs@company.com"))
        self.assertTrue(email_validator.is_hiring_channel_email("talent@company.com"))
        self.assertTrue(email_validator.is_hiring_channel_email("recruiting@company.com"))
        self.assertFalse(email_validator.is_hiring_channel_email("john.doe@company.com"))

    def test_email_validator_domain_cleaning(self):
        self.assertEqual(email_validator.clean_company_domain("jobs - Personio"), "personio.com")
        self.assertEqual(email_validator.clean_company_domain("FlytBase, Inc."), "flytbase.com")
        self.assertEqual(email_validator.clean_company_domain("Acme Corp [Remote]"), "acme.com")
        self.assertEqual(
            email_validator.clean_company_domain("Revolut", "https://jobs.revolut.com/apply/123"),
            "revolut.com"
        )

    @patch("config.HUNTER_API_KEY", "test_hunter_key")
    @patch("contact_finder.find_recruiter_via_hunter", return_value={"name": "Sarah Recruiter", "email": "sarah@personio.de", "title": "Lead Recruiter"})
    def test_contact_finder_discovery(self, mock_hunter):
        contact = contact_finder.discover_contact("Personio", "https://personio.de/jobs/123")
        self.assertTrue(bool(contact))
        self.assertEqual(contact["email"], "sarah@personio.de")
        self.assertEqual(contact["name"], "Sarah Recruiter")

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

    @patch("time.sleep")
    @patch("outbound_engine.send_email", return_value=True)
    @patch("email_validator.has_valid_mx_record", return_value=True)
    def test_auto_applier_submission(self, mock_mx, mock_send_email, mock_sleep):
        initial_data = [
            {
                "job_id": "test_app_01",
                "company": "Personio",
                "role": "Senior Product Manager",
                "contact_name": "Sarah Recruiter",
                "contact_email": "sarah.recruiter@personio.de",
                "status": "PENDING_OUTREACH",
                "apply_url": "https://personio.de/jobs/spm",
                "date_applied": "2026-08-26",
                "last_action_date": "2026-08-26",
                "followup_count": 0,
                "history": []
            }
        ]
        with open(self.test_tracker, "w", encoding="utf-8") as f:
            json.dump(initial_data, f)

        applied = auto_applier.apply_to_pending_jobs(max_applications=1)
        self.assertEqual(applied, 1)
        data = auto_applier.load_tracker()
        self.assertEqual(data[0]["status"], "APPLIED_EMAIL")
        self.assertIn("Automated application", data[0]["history"][-1]["action"])
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
                "contact_email": "careers@gamma.ai",
                "apply_url": "https://gamma.ai/jobs/lead-pm",
                "status": "APPLIED_EMAIL",
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
        self.assertIn("AUTONOMOUS APPLICATIONS SUBMITTED", args[2])
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

    def test_ats_optimizer(self):
        import ats_optimizer
        keywords = ats_optimizer.extract_keywords_from_text("Looking for an AI Product Manager with LLM and Prompt Engineering experience")
        self.assertIn("llm", keywords)
        self.assertIn("prompt engineering", keywords)
        self.assertIn("ai product manager", keywords)

        score, matched = ats_optimizer.calculate_match_score("AI Product Manager", "LLM SaaS platform", "Acme")
        self.assertGreaterEqual(score, 80)
        self.assertTrue(len(matched) > 0)

        summary = ats_optimizer.generate_ats_tailored_summary("AI Product Manager", "Acme", matched)
        self.assertIn("AI Product Manager", summary)
        self.assertIn("FlytBase", summary)

    def test_screener_engine(self):
        import screener_engine
        self.assertIn("linkedin.com", screener_engine.answer_question("What is your LinkedIn URL?"))
        self.assertIn("9172671040", screener_engine.answer_question("Please provide your phone number"))
        self.assertEqual(screener_engine.answer_question("Are you willing to relocate?"), "Yes")
        self.assertIn("30", screener_engine.answer_question("What is your notice period?"))
        self.assertEqual(screener_engine.answer_question("How many years of PM experience do you have?"), "3+")

    @patch("urllib.request.urlopen")
    def test_browser_applier(self, mock_urlopen):
        import browser_applier
        self.assertEqual(browser_applier.identify_ats_platform("https://jobs.lever.co/company/123"), "LEVER")
        self.assertEqual(browser_applier.identify_ats_platform("https://boards.greenhouse.io/company/jobs/456"), "GREENHOUSE")

        sample_job = {
            "company": "Personio",
            "role": "Product Manager",
            "apply_url": "https://jobs.lever.co/personio/pm-role"
        }
        payload = browser_applier.build_application_payload(sample_job)
        self.assertEqual(payload["candidate"]["full_name"], "Saurao Dalvi")
        self.assertEqual(payload["application"]["platform"], "LEVER")
        self.assertGreaterEqual(payload["application"]["ats_match_score"], 70)

        mock_resp = MagicMock()
        mock_resp.getcode.return_value = 200
        mock_urlopen.return_value.__enter__.return_value = mock_resp
        
        success, msg = browser_applier.submit_web_application(sample_job)
        self.assertTrue(success)
        self.assertIn("LEVER", msg)

    def test_blacklist_companies(self):
        self.assertIn("FlytBase", config.BLACKLIST_COMPANIES)
        initial_data = [
            {
                "job_id": "test_bl_01",
                "company": "FlytBase",
                "role": "AI Product Manager",
                "contact_email": "talent@flytbase.com",
                "status": "PENDING_OUTREACH",
                "date_applied": "2026-08-26",
                "last_action_date": "2026-08-26",
                "followup_count": 0,
                "history": []
            }
        ]
        with open(self.test_tracker, "w", encoding="utf-8") as f:
            json.dump(initial_data, f)

        applied = auto_applier.apply_to_pending_jobs(max_applications=5)
        self.assertEqual(applied, 0)
        data = auto_applier.load_tracker()
        self.assertEqual(data[0]["status"], "PENDING_OUTREACH")

    def test_referral_engine(self):
        import referral_engine
        stars, fit_reason = referral_engine.calculate_referral_priority("AI Product Manager", "Simpplr", "Bengaluru", "Building LLM platform")
        self.assertGreaterEqual(stars, 4)
        self.assertIn("AI/LLM", fit_reason)

        url = referral_engine.generate_linkedin_search_url("Google", "Product Manager", "Pune")
        self.assertIn("linkedin.com", url)
        self.assertIn("Google", url)

        packet = referral_engine.generate_referral_packet({
            "company": "Simpplr",
            "role": "Senior Product Manager - AI Products",
            "location": "Bengaluru",
            "apply_url": "https://linkedin.com/jobs/view/123",
            "description": "Looking for PM with LLM experience"
        })
        self.assertEqual(packet["company"], "Simpplr")
        self.assertIn("Saurao Dalvi", packet["forwardable_blurb"])
        self.assertIn("Simpplr", packet["peer_message"])


if __name__ == "__main__":
    unittest.main()
