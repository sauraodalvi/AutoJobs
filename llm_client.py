import logging
import os
import re
import litellm
import config
import candidate_profile

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
    "openrouter/google/gemma-4-31b-it:free",
    "openrouter/openrouter/free",
    "openrouter/google/gemma-4-26b-a4b-it:free",
    "openrouter/openai/gpt-oss-20b:free"
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


def generate_pitch(contact_name: str, company: str, role: str) -> dict:
    """
    Generates an ultra-short, crisp 3-sentence email pitch asking for a referral,
    tailored to Saurao Dalvi's background as an AI Product Manager / APM.
    """
    candidate_info = candidate_profile.get_context_prompt()

    prompt = f"""{candidate_info}

Task: Write an ultra-short, crisp, high-converting cold email asking for a referral.
Recipient Name: {contact_name}
Target Company: {company}
Target Role: {role}

Rules:
1. Exactly 3 sentences in the email body. Absolutely no generic fluff.
2. Sentence 1: Hook mentioning admiration for {company}'s work and my 3+ years experience as an AI Product Manager / APM building 0-to-1 SaaS products.
3. Sentence 2: Highlight a relevant impact metric (e.g. launching AI SaaS products growing MRR or cutting operational friction by 50%+).
4. Sentence 3: Direct call-to-action asking if they'd be open to referring me or connecting briefly for the {role} position.
5. Output format MUST strictly start with:
Subject: <Catchy Subject Line>

<Email Body>"""

    default_sub = f"Referral Request - {role} at {company} | Saurao Dalvi"

    try:
        content = _call_llm_with_fallbacks(
            system_prompt="You are a top 1% Product Manager writing high-converting, concise referral emails.",
            user_prompt=prompt,
            temperature=0.7,
            max_tokens=250
        )
        return parse_email_response(content, default_sub)
    except Exception as e:
        logging.error(f"Failed to generate pitch via LLM fallback chain: {e}")
        fallback_body = (
            f"Hi {contact_name},\n\n"
            f"I've been following {company}'s recent product developments and would love to bring my 3+ years of AI Product Management experience (0-to-1 SaaS launches, MRR growth) to the {role} position.\n"
            f"Given my background shipping LLM workflows and mobile/web platforms, I'm confident I can make an immediate impact on your team.\n"
            f"Would you be open to referring me or connecting briefly for 5 minutes?\n\n"
            f"Best regards,\nSaurao Dalvi"
        )
        return {"subject": default_sub, "body": fallback_body}


def generate_followup(contact_name: str, company: str, role: str) -> dict:
    """
    Generates a gentle, professional 2-sentence check-in follow-up message.
    """
    prompt = f"""Candidate Name: Saurao Dalvi (AI Product Manager / APM)

Task: Write a gentle, professional 2-sentence follow-up check-in email.
Recipient Name: {contact_name}
Target Company: {company}
Target Role: {role}

Rules:
1. Max 2 sentences in the body.
2. Polite check-in on the previous message regarding the {role} position at {company}.
3. Output format MUST strictly start with:
Subject: Following up: Referral - {role} at {company}

<Email Body>"""

    default_sub = f"Following up: Referral - {role} at {company} | Saurao Dalvi"

    try:
        content = _call_llm_with_fallbacks(
            system_prompt="You are a professional crafting short, polite follow-up emails.",
            user_prompt=prompt,
            temperature=0.7,
            max_tokens=200
        )
        return parse_email_response(content, default_sub)
    except Exception as e:
        logging.error(f"Failed to generate follow-up via LLM fallback chain: {e}")
        fallback_body = (
            f"Hi {contact_name},\n\n"
            f"Following up on my previous message regarding the {role} role at {company}.\n"
            f"I would appreciate any quick advice or referral if your team is still reviewing applications.\n\n"
            f"Best regards,\nSaurao Dalvi"
        )
        return {"subject": default_sub, "body": fallback_body}

