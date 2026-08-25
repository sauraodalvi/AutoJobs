"""
Tailored Cover Letter & Application Answer Generator for Saved Job Leads.
Synthesizes customized cover letters and application answers based on Saurao Dalvi's resume profile.
"""

import json
import logging
import re
from pathlib import Path
from datetime import datetime, timezone
import config
import candidate_profile
import llm_client
import job_fetcher

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

OUTPUT_DIR = Path(__file__).parent / "cover_letters"


def sanitize_filename(name: str) -> str:
    """Sanitizes company/role strings for safe filenames."""
    clean = re.sub(r"[^\w\-_]", "_", name)
    return re.sub(r"_+", "_", clean).strip("_")


def generate_cover_letter_for_item(target_job: dict) -> Path:
    """Generates and writes a tailored cover letter file for a specific job dictionary."""
    comp_name = target_job.get("company", "Target Company")
    role_title = target_job.get("role", "Product Manager")
    loc = target_job.get("location", "Remote")
    apply_url = target_job.get("apply_url", "N/A")

    logging.info(f"Generating tailored Cover Letter for {role_title} at {comp_name} ({loc})...")

    candidate_context = candidate_profile.get_context_prompt()

    prompt = f"""{candidate_context}

Task: Write a highly compelling, crisp 3-paragraph Cover Letter tailored for the application form of:
Company: {comp_name}
Role: {role_title}
Location: {loc}

Structure:
- Paragraph 1: High-energy introduction highlighting passion for {comp_name}'s mission and positioning Saurao Dalvi as a candidate with 3+ years of 0-to-1 AI Product Management experience.
- Paragraph 2: Specific impact highlights (0-to-1 SaaS products shipped at FlytBase/CrelioHealth/Sprinto, growing MRR, building LLM & automated workflows, cutting operational friction by 50%+).
- Paragraph 3: Closing call-to-action expressing enthusiasm to discuss how my AI product leadership will drive growth for {comp_name}.

Tone: Professional, confident, concise, zero corporate buzzword fluff."""

    try:
        letter_content = llm_client._call_llm_with_fallbacks(
            system_prompt="You are an elite executive career advisor writing top 1% tailored tech cover letters.",
            user_prompt=prompt,
            temperature=0.7,
            max_tokens=450
        )
    except Exception as e:
        logging.warning(f"LLM Cover Letter generation failed: {e}. Using structured high-impact template.")
        letter_content = (
            f"Dear Hiring Team at {comp_name},\n\n"
            f"I am writing to express my strong interest in the {role_title} position. With over 3 years of experience as an AI Product Manager, I specialize in taking 0-to-1 SaaS products from initial concept to commercial scale.\n\n"
            f"In my previous roles at FlytBase, CrelioHealth, and Sprinto, I led cross-functional teams to build LLM-powered workflows, mobile/web platforms, and enterprise solutions that accelerated MRR growth and reduced operational friction by over 50%. My background directly aligns with {comp_name}'s product ambitions.\n\n"
            f"I would welcome the opportunity to discuss how my AI product management background can add immediate value to {comp_name}.\n\n"
            f"Sincerely,\nSaurao Dalvi"
        )

    OUTPUT_DIR.mkdir(exist_ok=True)
    filename = f"{sanitize_filename(comp_name)}_{sanitize_filename(role_title)}.txt"
    filepath = OUTPUT_DIR / filename

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write(f"COVER LETTER & APPLICATION KIT\n")
        f.write(f"Target: {role_title} at {comp_name}\n")
        f.write(f"Apply Link: {apply_url}\n")
        f.write(f"Date Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n")
        f.write("=" * 60 + "\n\n")
        f.write(letter_content)
        f.write("\n\n" + "=" * 60 + "\n")
        f.write("CANDIDATE CONTACT SUMMARY:\n")
        f.write(f"Name: {config.CANDIDATE_NAME}\n")
        f.write(f"Email: {config.CANDIDATE_EMAIL}\n")
        f.write(f"Resume: {config.CANDIDATE_RESUME_PATH}\n")

    logging.info(f"✅ Cover Letter successfully saved to: {filepath}")
    return filepath


def generate_cover_letter_for_job(job_id: str = None, company: str = None, role: str = None):
    data = job_fetcher.load_tracker()
    if not data:
        logging.error("No tracker data available.")
        return None

    target_job = None
    if job_id:
        for item in data:
            if item.get("job_id") == job_id:
                target_job = item
                break
    elif company and role:
        for item in data:
            if company.lower() in item.get("company", "").lower() and role.lower() in item.get("role", "").lower():
                target_job = item
                break

    if not target_job:
        for item in data:
            if item.get("status") in ["JOB_LINK_SAVED", "APPLICATION_READY"]:
                target_job = item
                break

    if not target_job:
        logging.warning("No suitable target job found in tracker.json.")
        return None

    return generate_cover_letter_for_item(target_job)


def generate_kits_for_all_saved_leads(max_kits: int = 5) -> int:
    """
    Scans tracker for leads with apply_url that need application kits,
    generates tailored cover letters, and updates tracker status.
    """
    data = job_fetcher.load_tracker()
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    kits_generated = 0

    OUTPUT_DIR.mkdir(exist_ok=True)

    for item in data:
        if kits_generated >= max_kits:
            break

        if item.get("status") == "JOB_LINK_SAVED" and item.get("apply_url"):
            comp = item.get("company", "")
            role = item.get("role", "")
            filename = f"{sanitize_filename(comp)}_{sanitize_filename(role)}.txt"
            filepath = OUTPUT_DIR / filename

            if not filepath.exists():
                try:
                    generate_cover_letter_for_item(item)
                except Exception as e:
                    logging.error(f"Error generating kit for {comp}: {e}")
                    continue

            item["status"] = "APPLICATION_READY"
            item["last_action_date"] = today_str
            item["history"].append({
                "date": today_str,
                "action": f"Generated tailored application kit & cover letter ({filename}). Status updated to APPLICATION_READY."
            })
            kits_generated += 1

    if kits_generated > 0:
        job_fetcher.save_tracker(data)
        logging.info(f"Generated {kits_generated} application kit(s) in {OUTPUT_DIR}")

    return kits_generated


if __name__ == "__main__":
    generate_kits_for_all_saved_leads()
