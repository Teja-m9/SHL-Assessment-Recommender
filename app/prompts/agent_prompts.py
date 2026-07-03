GROQ_SYSTEM_PROMPT = "You only rewrite grounded SHL catalog answers and never invent details."


def build_groq_rewrite_prompt(
    intent: str,
    user_text: str,
    base_reply: str,
    grounded_matches: str,
) -> str:
    return (
        "Rewrite the answer so it stays concise and recruiter-friendly. "
        "Do not add any assessment, URL, or claim not present below.\n\n"
        f"Intent: {intent}\n"
        f"User request: {user_text}\n"
        f"Base answer: {base_reply}\n"
        f"Grounded matches: {grounded_matches}"
    )