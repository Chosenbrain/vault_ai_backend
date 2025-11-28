import re

def extract_credentials(text: str):
    """
    Extracts username & password from message safely.
    Example: "user=john pass=12345"
    """
    username = None
    password = None

    u = re.search(r"user\s*=\s*([^\s]+)", text, re.IGNORECASE)
    p = re.search(r"pass\s*=\s*([^\s]+)", text, re.IGNORECASE)

    if u:
        username = u.group(1)
    if p:
        password = p.group(1)

    return {"username": username, "password": password}


def redact_message(text: str):
    """
    Hide sensitive values before sending to OpenAI.
    """
    text = re.sub(r"user\s*=\s*[^\s]+", "user=***", text, flags=re.IGNORECASE)
    text = re.sub(r"pass\s*=\s*[^\s]+", "pass=***", text, flags=re.IGNORECASE)

    # mask long digit strings (like credit cards)
    text = re.sub(r"\b\d{12,19}\b", "****", text)

    return text
