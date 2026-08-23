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


def _call_llm_with_fallbacks(system_prompt: str, user_prompt: str, temperature: float = 0.7, max_tokens: int = 250) -> str:
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


def generate_pitch(contact_name: str, company: str, role: str, apply_url: str = "") -> dict:
    """
    Generates a personalized recruiter email following Saurao Dalvi's proven past outreach style.
    """
    first_name = contact_name.split()[0] if contact_name else "Hiring Manager"
    url_text = f" Here is the job posting: {apply_url}." if apply_url else ""

    prompt = f"""Task: Write a concise, polite recruiter outreach email following this EXACT structure:

Recipient Name: {contact_name}
Target Company: {company}
Target Role: {role}
Job URL: {apply_url}

Style Template:
Subject: Note on my {company} {role} application

Hi {first_name},

I recently applied for the {role} role at {company} and remain very interested.{url_text}

Could you share whether applications are currently under review and expected timelines? Also, are you the right person to speak with for this role; if not, would you point me to the appropriate contact?

Thank you for your time. I look forward to next steps.

Saurao Dalvi

Output format MUST strictly start with:
Subject: Note on my {company} {role} application

<Email Body>"""

    default_sub = f"Note on my {company} {role} application"
    fallback_body = (
        f"Hi {first_name},\n\n"
        f"I recently applied for the {role} role at {company} and remain very interested.{url_text}\n\n"
        f"Could you share whether applications are currently under review and expected timelines?\n\n"
        f"Are you the right person managing hiring for this role? If not, I would appreciate guidance on whom I should connect with.\n\n"
        f"Thank you for your time. I look forward to next steps.\n\n"
        f"Saurao Dalvi"
    )

    try:
        content = _call_llm_with_fallbacks(
            system_prompt="You are an assistant writing crisp, polite job application follow-up emails matching Saurao Dalvi's personal style.",
            user_prompt=prompt,
            temperature=0.3,
            max_tokens=250
        )
        return parse_email_response(content, default_sub)
    except Exception as e:
        logging.error(f"Failed to generate pitch via LLM fallback chain: {e}")
        return {"subject": default_sub, "body": fallback_body}


def generate_followup(contact_name: str, company: str, role: str, apply_url: str = "") -> dict:
    """
    Generates a gentle check-in follow-up following Saurao's proven past outreach style.
    """
    first_name = contact_name.split()[0] if contact_name else "Hiring Manager"

    prompt = f"""Task: Write a gentle check-in follow-up email following this EXACT structure:

Recipient Name: {contact_name}
Target Company: {company}
Target Role: {role}

Style Template:
Subject: Re: Note on my {company} {role} application

Hi {first_name},

I wanted to check in and see if you had any updates after my last email regarding Note on my {role} application at {company}.

Thanks in advance!

Saurao Dalvi

Output format MUST strictly start with:
Subject: Re: Note on my {company} {role} application

<Email Body>"""

    default_sub = f"Re: Note on my {company} {role} application"
    fallback_body = (
        f"Hi {first_name},\n\n"
        f"I wanted to check in and see if you had any updates after my last email regarding Note on my {role} application at {company}. Thanks in advance!\n\n"
        f"Saurao Dalvi"
    )

    try:
        content = _call_llm_with_fallbacks(
            system_prompt="You are an assistant writing brief, polite follow-up emails matching Saurao Dalvi's style.",
            user_prompt=prompt,
            temperature=0.3,
            max_tokens=150
        )
        return parse_email_response(content, default_sub)
    except Exception as e:
        logging.error(f"Failed to generate follow-up via LLM fallback chain: {e}")
        return {"subject": default_sub, "body": fallback_body}


