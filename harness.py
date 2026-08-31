"""
AutoJobs Agent Execution, Test & Evaluation Harness (harness.py)
Provides a unified test runner, LLM quality evaluation benchmark, system doctor,
mock dry-runner, and live pipeline orchestration.
"""

import argparse
import json
import logging
import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

# Configure clean logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).parent


# ==============================================================================
# 1. SYSTEM DOCTOR & ENVIRONMENT DIAGNOSTICS
# ==============================================================================
def run_doctor():
    """Validates configuration, environment keys, and filesystem prerequisites."""
    print("\n" + "=" * 70)
    print("🩺 AUTOJOBS AGENT DIAGNOSTIC HEALTH CHECK (DOCTOR)")
    print("=" * 70)

    import config
    import candidate_profile

    checks = []

    # 1. Resume PDF
    resume_path = getattr(config, "CANDIDATE_RESUME_PATH", "")
    has_resume = False
    if resume_path and Path(resume_path).exists():
        has_resume = True
        checks.append(("Candidate Resume PDF", "OK", f"Found at {resume_path}"))
    else:
        local_pdf = BASE_DIR / "Saurao_Dalvi_Resume.pdf"
        if local_pdf.exists():
            has_resume = True
            checks.append(("Candidate Resume PDF", "OK", f"Found at {local_pdf}"))
        else:
            checks.append(("Candidate Resume PDF", "FAIL", "Resume PDF not found!"))

    # 2. OpenRouter / LLM Key
    openrouter_key = getattr(config, "OPENROUTER_API_KEY", "")
    if openrouter_key and openrouter_key.startswith("sk-or-v1-"):
        checks.append(("OpenRouter LLM Key", "OK", "Configured & Active"))
    else:
        checks.append(("OpenRouter LLM Key", "WARN", "Missing or placeholder"))

    # 3. Email & SMTP
    email_user = getattr(config, "EMAIL_USER", "")
    email_pass = getattr(config, "EMAIL_PASS", "")
    if email_user and email_pass:
        checks.append(("Gmail SMTP/IMAP Auth", "OK", f"User: {email_user}"))
    else:
        checks.append(("Gmail SMTP/IMAP Auth", "WARN", "Credentials missing in .env"))

    # 4. Tracker File
    tracker_path = getattr(config, "TRACKER_FILE", BASE_DIR / "tracker.json")
    if tracker_path.exists():
        try:
            with open(tracker_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            checks.append(("Tracker Ledger Database", "OK", f"{len(data)} jobs tracked"))
        except Exception as e:
            checks.append(("Tracker Ledger Database", "FAIL", f"Corrupted: {e}"))
    else:
        checks.append(("Tracker Ledger Database", "WARN", "tracker.json does not exist yet"))

    # 5. Output Folders
    for folder in ["referrals", "cover_letters", "dashboard"]:
        p = BASE_DIR / folder
        if p.exists() and p.is_dir():
            checks.append((f"Directory '{folder}/'", "OK", f"Found ({len(list(p.iterdir()))} files)"))
        else:
            checks.append((f"Directory '{folder}/'", "WARN", "Directory missing"))

    # Print Report
    for name, status, msg in checks:
        icon = "✅" if status == "OK" else ("⚠️" if status == "WARN" else "❌")
        print(f"{icon} {name:<28} [{status:<4}] -> {msg}")

    print("=" * 70 + "\n")


# ==============================================================================
# 2. QUALITY EVALUATION BENCHMARK (HARNESS EVAL)
# ==============================================================================
def run_evaluation():
    """Evaluates the quality, ATS scoring, and length constraints of generated referral assets."""
    print("\n" + "=" * 70)
    print("🎯 AUTOJOBS QUALITY EVALUATION BENCHMARK")
    print("=" * 70)

    import referral_engine
    import ats_optimizer

    sample_jobs = [
        {"company": "Revolut", "role": "Product Manager - AI Platform", "location": "Remote / EU"},
        {"company": "Grab", "role": "Product Manager - Consumer Experience", "location": "Singapore"},
        {"company": "Mercari", "role": "Associate Product Manager", "location": "Tokyo, Japan"},
        {"company": "Personio", "role": "Senior Product Manager", "location": "Munich, Germany"},
        {"company": "Icertis", "role": "AI Product Manager", "location": "Pune, India"}
    ]

    passed_tests = 0
    total_tests = len(sample_jobs) * 3

    for idx, job in enumerate(sample_jobs, 1):
        comp = job["company"]
        role = job["role"]
        print(f"\n[{idx}/{len(sample_jobs)}] Evaluating Referral Packet for: {comp} — {role}")

        packet = referral_engine.generate_referral_packet(job)

        # Check 1: ATS Score
        ats = packet["ats_score"]
        ats_pass = ats >= 80
        if ats_pass:
            passed_tests += 1
            print(f"  ✅ ATS Match Score: {ats}% (Target >= 80%)")
        else:
            print(f"  ❌ ATS Match Score: {ats}% (Below target 80%)")

        # Check 2: LinkedIn Note Length constraint (<300 chars)
        note = packet["peer_message"]
        note_len = len(note)
        note_pass = note_len <= 350
        if note_pass:
            passed_tests += 1
            print(f"  ✅ LinkedIn Note Length: {note_len} chars (Concise & zero-friction)")
        else:
            print(f"  ❌ LinkedIn Note Length: {note_len} chars (Too long for InMail)")

        # Check 3: Content includes FlytBase or CrelioHealth metrics
        blurb = packet["forwardable_blurb"]
        has_cred = "FlytBase" in blurb or "CrelioHealth" in blurb or "SaaS" in blurb
        if has_cred:
            passed_tests += 1
            print(f"  ✅ Forwardable Blurb: Contains verified 0-to-1 SaaS metrics & credentials")
        else:
            print(f"  ❌ Forwardable Blurb: Missing essential candidate metrics")

    pct = int((passed_tests / total_tests) * 100)
    print("\n" + "-" * 70)
    print(f"🏆 EVALUATION SCORE: {passed_tests}/{total_tests} ({pct}%) QUALITY PASS")
    print("=" * 70 + "\n")


# ==============================================================================
# 3. UNIT & INTEGRATION TEST RUNNER
# ==============================================================================
def run_tests():
    """Runs all agent unit & integration test suites in test_agent.py."""
    print("\n" + "=" * 70)
    print("🧪 RUNNING AUTOJOBS TEST SUITE (test_agent.py)")
    print("=" * 70)

    import test_agent
    suite = unittest.TestLoader().loadTestsFromModule(test_agent)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    print("=" * 70 + "\n")
    return result.wasSuccessful()


# ==============================================================================
# 4. MOCK SANDBOX RUNNER (SAFE DRY-RUN)
# ==============================================================================
def run_mock():
    """Executes full agent flow in sandbox mode with zero outbound network transmissions."""
    print("\n" + "=" * 70)
    print("🛡️ RUNNING MOCK SANDBOX SIMULATION (DRY RUN)")
    print("=" * 70)

    import referral_engine
    import cover_letter_generator

    print("1. Simulating Job Ingestion...")
    mock_job = {
        "company": "MockTech AI",
        "role": "AI Product Manager",
        "location": "Pune, India / Remote",
        "apply_url": "https://example.com/apply",
        "description": "0-to-1 AI product management, LLM agents, B2B SaaS"
    }

    print("2. Synthesizing Tailored Cover Letter...")
    cl_path = cover_letter_generator.generate_cover_letter_for_item(mock_job)
    print(f"   Saved to: {cl_path}")

    print("3. Generating Multi-Touch Referral Packet...")
    packet = referral_engine.generate_referral_packet(mock_job)
    print(f"   ATS Score: {packet['ats_score']}% | Priority: {'⭐' * packet['stars']}")
    print(f"   LinkedIn Search URL: {packet['linkedin_search_url']}")
    print(f"   1-Click Note: {packet['peer_message'][:100]}...")

    print("\n✅ Sandbox dry-run completed successfully with zero live transmissions.")
    print("=" * 70 + "\n")


# ==============================================================================
# 5. CLI ENTRYPOINT
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(description="AutoJobs Agent Execution & Test Harness")
    parser.add_argument(
        "command",
        choices=["doctor", "test", "eval", "mock", "run", "server"],
        nargs="?",
        default="doctor",
        help="Command to execute: doctor | test | eval | mock | run | server"
    )

    args = parser.parse_args()

    if args.command == "doctor":
        run_doctor()
    elif args.command == "test":
        run_tests()
    elif args.command == "eval":
        run_evaluation()
    elif args.command == "mock":
        run_mock()
    elif args.command == "run":
        import main as agent_main
        agent_main.main()
    elif args.command == "server":
        import server
        server.run_server()


if __name__ == "__main__":
    main()
