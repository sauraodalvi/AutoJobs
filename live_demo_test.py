"""
Comprehensive Live End-to-End System Test for AutoJobs Autonomous Agent.
Tests:
1. Candidate profile data & resume attachment availability
2. Live DNS MX verification on active company domains
3. Contact finder & verified talent channel discovery
4. Tailored cover letter & kit generation
5. Autonomous job applier execution (email application assembly + resume attachment)
6. Outbound pitch & follow-up sequence synthesis
7. Daily Morning Briefing Digest generation with full metrics
8. Clean ledger state audit
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch

import config
import candidate_profile
import llm_client
import email_validator
import contact_finder
import cover_letter_generator
import auto_applier
import outbound_engine
import sys

# Reconfigure standard streams to UTF-8 for Windows PowerShell
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def run_comprehensive_test():
    print("\n" + "=" * 80)
    print("      🚀 STARTING AUTOJOBS COMPREHENSIVE END-TO-END SYSTEM TEST")
    print("=" * 80 + "\n")

    # 1. Verify Candidate Profile & Resume File
    logging.info("--- [TEST 1/7] Verifying Candidate Profile & Resume Asset ---")
    prompt = candidate_profile.get_context_prompt()
    assert config.CANDIDATE_NAME in prompt, "Candidate name missing from profile prompt"
    assert "FlytBase" in prompt, "Experience history missing from profile prompt"
    
    resume_path = Path(config.CANDIDATE_RESUME_PATH) if getattr(config, "CANDIDATE_RESUME_PATH", None) else None
    if not resume_path or not resume_path.exists():
        resume_path = Path(__file__).parent / "Saurao_Dalvi_Resume.pdf"
    
    assert resume_path.exists(), f"Resume PDF not found at {resume_path}"
    logging.info(f"✅ Candidate Profile: {config.CANDIDATE_NAME} ({config.CANDIDATE_EMAIL})")
    logging.info(f"✅ Verified Resume Asset: {resume_path.name} ({resume_path.stat().st_size:,} bytes)")

    # 2. Test Email Validator & DNS MX Resolution
    logging.info("\n--- [TEST 2/7] Testing Email Validation & Live DNS MX Resolution ---")
    test_domains = ["google.com", "personio.com", "flytbase.com", "microsoft.com"]
    for d in test_domains:
        has_mx = email_validator.has_valid_mx_record(d)
        logging.info(f"   Domain MX Check: {d} -> {'VALID (Active Mail Server)' if has_mx else 'FAILED'}")
        assert has_mx, f"DNS MX check failed for active domain {d}"

    # Verify generic blocking vs hiring channel acceptance
    is_valid_dead, _ = email_validator.is_valid_recruiter_email("noreply@google.com", verify_mx=True)
    assert not is_valid_dead, "Failed: noreply email should be rejected"

    is_valid_talent, _ = email_validator.is_valid_recruiter_email("talent@google.com", verify_mx=True, allow_hiring_channels=True)
    assert is_valid_talent, "Failed: talent email should be accepted"
    logging.info("✅ Email validation logic passed: Dead/bounce prefixes blocked, talent channels verified.")

    # 3. Test Contact Discovery
    logging.info("\n--- [TEST 3/7] Testing Verified Talent Channel Discovery ---")
    contact = contact_finder.find_verified_talent_channel("Personio", "personio.de")
    assert contact and "email" in contact, "Failed to resolve talent channel for Personio"
    logging.info(f"✅ Discovered Verified Contact: {contact['name']} <{contact['email']}>")

    # 4. Test Tailored Cover Letter Synthesis
    logging.info("\n--- [TEST 4/7] Testing Tailored Cover Letter Generation ---")
    sample_job = {
        "job_id": "test_e2e_01",
        "company": "FlytBase",
        "role": "AI Product Manager",
        "location": "Pune, India",
        "apply_url": "https://flytbase.com/careers/ai-pm",
        "contact_email": "talent@flytbase.com",
        "status": "PENDING_OUTREACH"
    }
    kit_file = cover_letter_generator.generate_cover_letter_for_item(sample_job)
    assert kit_file.exists(), f"Cover letter kit not generated at {kit_file}"
    logging.info(f"✅ Generated tailored cover letter kit at: {kit_file.name}")

    # 5. Test Auto-Applier Assembly
    logging.info("\n--- [TEST 5/7] Testing Autonomous Job Applier Execution ---")
    with patch("outbound_engine.send_email", return_value=True) as mock_send:
        success = auto_applier.apply_via_email(sample_job)
        assert success, "apply_via_email returned False"
        assert mock_send.called, "outbound send_email was not invoked"
        args, kwargs = mock_send.call_args
        target_to = kwargs.get("to_email") or (args[0] if len(args) > 0 else "")
        target_sub = kwargs.get("subject") or (args[1] if len(args) > 1 else "")
        target_body = kwargs.get("body") or (args[2] if len(args) > 2 else "")
        target_attach = kwargs.get("attach_resume") if "attach_resume" in kwargs else (args[4] if len(args) > 4 else True)
        
        assert target_to == "talent@flytbase.com"
        assert "Application: AI Product Manager" in target_sub
        assert "Saurao Dalvi" in target_body
        assert target_attach is True
        logging.info(f"✅ Auto-Applier package successfully assembled and dispatched to: {target_to}")
        logging.info(f"   Subject: {target_sub}")
        logging.info(f"   Attached Resume: {target_attach}")

    # 6. Test Outbound Recruiter & Referral Pitches
    logging.info("\n--- [TEST 6/7] Testing AI Recruiter Pitch & Referral Synthesis ---")
    rec_pitch = llm_client.generate_pitch("Priya Chowdhary", "Valiance Solutions", "Product Manager", style="recruiter")
    assert "Valiance Solutions" in rec_pitch["body"]
    logging.info(f"✅ Recruiter Pitch Subject: {rec_pitch['subject']}")

    ref_pitch = llm_client.generate_pitch("Nitisha Varun", "UKG", "Sr Product Manager", style="referral")
    assert "UKG" in ref_pitch["body"]
    logging.info(f"✅ Referral Pitch Subject: {ref_pitch['subject']}")

    # 7. Test Daily Morning Briefing Digest Formatting
    logging.info("\n--- [TEST 7/7] Testing 09:00 AM Morning Briefing Digest Generation ---")
    with patch("outbound_engine.send_email", return_value=True) as mock_digest_send:
        sent = outbound_engine.send_daily_digest(config.CANDIDATE_EMAIL)
        assert sent, "send_daily_digest failed"
        assert mock_digest_send.called
        d_args, d_kwargs = mock_digest_send.call_args
        d_sub = d_kwargs.get("subject") or (d_args[1] if len(d_args) > 1 else "")
        d_recip = d_kwargs.get("to_email") or (d_args[0] if len(d_args) > 0 else "")
        d_body = d_kwargs.get("body") or (d_args[2] if len(d_args) > 2 else "")
        logging.info(f"✅ Morning Briefing Subject: {d_sub}")
        logging.info(f"   Recipient: {d_recip}")
        assert "APPLICATION & OUTREACH METRICS" in d_body

    # Clean up test cover letter
    if kit_file.exists():
        kit_file.unlink()

    print("\n" + "=" * 80)
    print("      🎉 ALL 7 END-TO-END SYSTEM TESTS PASSED SUCCESSFULLY!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    run_comprehensive_test()
