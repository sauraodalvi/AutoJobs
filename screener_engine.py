"""
Intelligent Screener Q&A Engine.
Automatically resolves application screener questions using candidate knowledge base
with LLM synthesis for custom behavioral or technical questions.
"""

import json
import logging
import re
from pathlib import Path
from typing import Optional
import candidate_profile
import llm_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

KNOWLEDGE_BASE_PATH = Path(__file__).parent / "screener_answers.json"


def load_knowledge_base() -> dict:
    """Loads screener_answers.json safely."""
    if not KNOWLEDGE_BASE_PATH.exists():
        return {}
    try:
        with open(KNOWLEDGE_BASE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading screener_answers.json: {e}")
        return {}


def answer_question(question_text: str, company: str = "", role: str = "") -> str:
    """
    Answers an application screener question based on candidate profile.
    Uses pattern matching for standard fields and LLM for complex prompts.
    """
    if not question_text:
        return ""

    q_lower = question_text.lower().strip()
    kb = load_knowledge_base()
    personal = kb.get("personal", {})
    employment = kb.get("employment", {})
    auth = kb.get("work_authorization", {})
    edu = kb.get("education", {})
    behavioral = kb.get("behavioral_highlights", {})

    # 1. Contact & Social Links
    if any(k in q_lower for k in ["linkedin", "linked in"]):
        return personal.get("linkedin", "https://www.linkedin.com/in/saurao-dalvi/")
    if any(k in q_lower for k in ["portfolio", "website", "personal site", "github"]):
        if "github" in q_lower:
            return personal.get("github", "https://github.com/sauraodalvi")
        return personal.get("portfolio", "https://sauraodalvi.netlify.app/")
    if "phone" in q_lower or "mobile" in q_lower or "contact number" in q_lower:
        return personal.get("phone", "+91 9876543210")
    if "city" in q_lower or "location" in q_lower or "current address" in q_lower:
        return personal.get("location", "Pune, Maharashtra, India")

    # 2. Work Authorization & Sponsorship
    if "legally authorized" in q_lower or "authorized to work" in q_lower:
        return "Yes"
    if "sponsorship" in q_lower or "visa" in q_lower:
        return "No"  # Default for remote / India positions to avoid auto-rejection

    # 3. Experience & Timeline
    if "notice period" in q_lower or "notice" in q_lower:
        return employment.get("notice_period", "30 days (Flexible)")
    if "start date" in q_lower or "earliest start" in q_lower or "how soon" in q_lower:
        return employment.get("earliest_start_date", "Within 2-4 weeks")
    if "years of experience" in q_lower or "how many years" in q_lower:
        return "3+"

    # 4. Education
    if "degree" in q_lower or "education" in q_lower or "university" in q_lower:
        return f"{edu.get('degree', 'Bachelor of Engineering')} in {edu.get('field_of_study', 'Engineering')}"

    # 5. Compensation / Salary
    if "salary" in q_lower or "compensation" in q_lower or "expected ctc" in q_lower or "rate" in q_lower:
        return "Negotiable / Competitive market rate"

    # 6. Relocation / Remote
    if "relocate" in q_lower or "willing to relocate" in q_lower:
        return "Yes"
    if "remote" in q_lower or "work arrangement" in q_lower:
        return "Open to Remote, Hybrid, or On-site"

    # 7. AI & PM Technical Experience
    if any(k in q_lower for k in ["llm", "ai experience", "prompt engineering", "artificial intelligence"]):
        return behavioral.get("ai_experience", (
            "3+ years of experience leading 0-to-1 AI product delivery at FlytBase and CrelioHealth, "
            "building LLM prompt pipelines, agentic workflows, and automated developer tooling."
        ))

    # 8. Open-ended / Custom Company Questions (LLM Fallback)
    prompt = f"""Candidate: Saurao Dalvi
Candidate Summary: {candidate_profile.SUMMARY}
Target Company: {company}
Target Role: {role}

Application Screener Question: "{question_text}"

Task: Provide a concise, highly professional 2-sentence direct answer to this job application question.
Tone: Confident, specific, zero corporate buzzwords."""

    try:
        ans = llm_client._call_llm_with_fallbacks(
            system_prompt="You are an expert career assistant providing concise, high-converting answers to job application screener questions.",
            user_prompt=prompt,
            temperature=0.3,
            max_tokens=150
        )
        return ans.strip().strip('"')
    except Exception:
        return (
            f"With 3+ years of 0-to-1 AI Product Management experience at FlytBase and CrelioHealth, "
            f"I have a proven record of shipping LLM-powered products and scalable SaaS solutions."
        )
