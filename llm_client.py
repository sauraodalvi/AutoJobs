import logging
import os
import re
import litellm
import config
import candidate_profile

litellm.suppress_debug_info = True

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Ensure API Key is passed to environment for LiteLLM
if config.OPENROUTER_API_KEY:
    os.environ["OPENROUTER_API_KEY"] = config.OPENROUTER_API_KEY
if config.GROQ_API_KEY:
    os.environ["GROQ_API_KEY"] = config.GROQ_API_KEY


def sanitize_text(text: str) -> str:
    """Sanitizes generated text to strip unexpected formatting anomalies or null bytes."""
    if not text:
        return ""
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    return text.strip()


def parse_email_response(raw_text: str, default_subject: str) -> dict:
    """
    Parses LLM output into subject and body dictionary.
    Looks for standard Subject: header or falls back cleanly.
    """
    raw_text = sanitize_text(raw_text)
    subject = default_subject
    body = raw_text

    if "Subject:" in raw_text:
        lines = raw_text.splitlines()
        body_lines = []
        in_body = False
        for line in lines:
            if line.startswith("Subject:") and not in_body:
                subject = line.replace("Subject:", "").strip()
            elif line.strip() == "" and not in_body:
                in_body = True
            else:
                body_lines.append(line)
        if body_lines:
            body = "\n".join(body_lines).strip()

    return {
        "subject": sanitize_text(subject),
        "body": sanitize_text(body)
    }


FALLBACK_MODELS = [
    "openrouter/openrouter/free",
    "openrouter/meta-llama/llama-3.3-70b-instruct:free",
    "openrouter/qwen/qwen-2.5-coder-32b-instruct:free",
    "openrouter/google/gemini-2.0-flash-lite-preview-02-05:free",
    "openrouter/google/gemma-4-31b-it:free"
]


def _call_llm_with_fallbacks(system_prompt: str, user_prompt: str, temperature: float = 0.7, max_tokens: int = 350) -> str:
    """Attempts LLM call with primary model, then cycles through free fallback models."""
    models_to_try = [config.LLM_MODEL] + [m for m in FALLBACK_MODELS if m != config.LLM_MODEL]
    
    last_exception = None
    for model in models_to_try:
        try:
            logging.info(f"Attempting LLM call with model: {model}")
            response = litellm.completion(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            logging.warning(f"LLM model {model} failed: {e}. Trying next fallback...")
            last_exception = e

    raise last_exception or Exception("All LLM models failed.")


def generate_pitch(contact_name: str, company: str, role: str, apply_url: str = "", style: str = "recruiter") -> dict:
    """
    Generates a personalized email matching Saurao Dalvi's proven outreach style.
    
    Styles:
    - 'recruiter' (default): Concise application note / status check-in.
    - 'referral': Rich pitch for referral requests highlighting 0-to-1 AI product & engineering background.
    """
    first_name = contact_name.split()[0] if contact_name else "Hiring Manager"
    url_text = f" Here is the posting: {apply_url}." if apply_url else ""
    job_link_line = f"\n\nHere is the link to the job: {apply_url}" if apply_url else ""

    if style == "referral":
        default_sub = f"Applying for {role} at {company} – can you help with referral?"
        fallback_body = (
            f"Hi {first_name},\n\n"
            f"I’m Saurao Dalvi, currently an AI Engineer (Forward Deployed Engineer) at FlytBase with about 3 years of hands-on experience delivering customer-facing solutions. I’m reaching out because the {role} role at {company} lines up closely with the way I work: ship fast, learn even faster, and solve real user problems with pragmatic AI and automation.\n\n"
            f"What I bring: emerging talent with rapid learning potential, plus deep, practical expertise in AI workflows, automation, and 0-to-1 product delivery. I’ve built internal tools and CLIs that streamline developer workflows, automated complex cross-app processes with Zapier and Make, and used Grok, Claude, and LLMs to power robust agentic and retrieval-driven features. In a forward-deployed capacity, I translate ambiguous requirements into shipped solutions—exactly the kind of bias to action and systems thinking a strong {role} at {company} needs.\n\n"
            f"I’m particularly excited about {company} because of its bar for execution and learning culture. I thrive in environments where customer impact, thoughtful tooling, and reliable automation matter.\n\n"
            f"Would you be open to referring me? If helpful, you can skim my background here as well: {candidate_profile.LINKEDIN_URL}{job_link_line}\n\n"
            f"Best regards,\nSaurao Dalvi\n"
            f"Portfolio: {candidate_profile.PORTFOLIO_URL}\n"
            f"LinkedIn: {candidate_profile.LINKEDIN_URL}"
        )
    else:
        # Recruiter Application Follow-up style
        default_sub = f"Note on my {company} {role} application"
        fallback_body = (
            f"Hi {contact_name or first_name},\n\n"
            f"I recently applied for the {role} role at {company} and remain very interested.{url_text}\n\n"
            f"Could you share whether applications are currently under review and the anticipated timeline?\n\n"
            f"Are you the right person managing hiring for this role? If not, I would appreciate guidance on whom I should connect with.\n\n"
            f"Thank you for your time. I look forward to next steps.\n\n"
            f"Saurao Dalvi"
        )

    prompt = f"""Task: Write an outreach email for Saurao Dalvi following this exact structure:

Recipient: {contact_name}
Company: {company}
Role: {role}
Job URL: {apply_url}

Style Template:
Subject: {default_sub}

{fallback_body}

Output format MUST start with:
Subject: {default_sub}

<Email Body>"""

    try:
        content = _call_llm_with_fallbacks(
            system_prompt="You are an assistant writing crisp, polite job outreach emails matching Saurao Dalvi's exact personal tone and formatting.",
            user_prompt=prompt,
            temperature=0.2,
            max_tokens=350
        )
        return parse_email_response(content, default_sub)
    except Exception as e:
        logging.debug(f"Using default outreach template ({e})")
        return {"subject": default_sub, "body": fallback_body}


def generate_followup(contact_name: str, company: str, role: str, apply_url: str = "", style: str = "recruiter") -> dict:
    """
    Generates a gentle check-in follow-up following Saurao's proven past outreach style.
    """
    first_name = contact_name.split()[0] if contact_name else "Hiring Manager"

    if style == "referral":
        default_sub = f"Re: Applying for {role} at {company} – can you help with referral?"
        fallback_body = (
            f"Hello {contact_name or first_name}, I wanted to follow up on my last email regarding Applying for {role} at {company} – can you help with referral?. Please let me know your thoughts whenever convenient.\n\n"
            f"Best regards,\nSaurao Dalvi"
        )
    else:
        default_sub = f"Re: Note on my {company} {role} application"
        fallback_body = (
            f"Hi {contact_name or first_name}, I wanted to check in and see if you had any updates after my last email regarding Note on my {role} application at {company}. Thanks in advance!\n\n"
            f"Saurao Dalvi"
        )

    prompt = f"""Task: Write a gentle check-in follow-up email following this exact format:

Recipient: {contact_name}
Company: {company}
Role: {role}

Style Template:
Subject: {default_sub}

{fallback_body}

Output format MUST start with:
Subject: {default_sub}

<Email Body>"""

    try:
        content = _call_llm_with_fallbacks(
            system_prompt="You are an assistant writing brief, polite follow-up emails matching Saurao Dalvi's exact style.",
            user_prompt=prompt,
            temperature=0.2,
            max_tokens=150
        )
        return parse_email_response(content, default_sub)
    except Exception as e:
        logging.debug(f"Using default follow-up template ({e})")
        return {"subject": default_sub, "body": fallback_body}
