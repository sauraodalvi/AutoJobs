"""
Candidate Profile module storing resume and background context for Saurao Dalvi.
Used by llm_client to craft personalized, high-converting referral and recruiter outreach messages.
"""

SUMMARY = (
    "AI Product Manager & AI Engineer (Forward Deployed Engineer) at FlytBase with 3+ years of hands-on "
    "experience shaping product roadmaps, leading cross-functional teams, and delivering customer-facing AI/automation solutions "
    "across drone autonomy (FlytBase), healthcare SaaS (CrelioHealth), and enterprise security SaaS (Sprinto). "
    "Proven 0-to-1 builder of AI-native products, developer CLIs, LLM-powered workflows, and agentic systems."
)

KEY_ACHIEVEMENTS = [
    "Owned 0-to-1 roadmap & launch of Prediq (AI drone SaaS) growing to ~$6K MRR at FlytBase.",
    "Owned roadmap of Smart Reports at CrelioHealth, increasing lab revenue by ~$2,000 MRR per lab.",
    "Cut patient registration time by ~58% and sample turnaround by 18% using custom AI prompt pipelines.",
    "Built internal developer CLIs and automated complex cross-app processes with Zapier, Make, and Python.",
    "Built and launched AI products like Hidden Jobs (50K+ live ATS jobs indexed) and Stare V2.",
    "Co-founded Elite PM platform in partnership with a Microsoft Product Manager."
]

TARGET_ROLES_STR = "Product Manager / Associate Product Manager (APM) / AI Product Manager"
TARGET_LOCATIONS_STR = "Pune, European Union, Japan, Singapore, Indonesia, and Remote"

LINKEDIN_URL = "https://www.linkedin.com/in/saurao-dalvi/"
PORTFOLIO_URL = "https://sauraodalvi.netlify.app/"


def get_context_prompt() -> str:
    """Returns a structured prompt snippet of candidate qualifications."""
    achievements_formatted = "\n- ".join(KEY_ACHIEVEMENTS)
    return (
        f"Candidate Name: Saurao Dalvi\n"
        f"Target Roles: {TARGET_ROLES_STR}\n"
        f"Target Locations: {TARGET_LOCATIONS_STR}\n"
        f"Summary: {SUMMARY}\n"
        f"Portfolio: {PORTFOLIO_URL}\n"
        f"LinkedIn: {LINKEDIN_URL}\n"
        f"Key Highlights:\n- {achievements_formatted}\n"
    )
