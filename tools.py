SYSTEM_PROMPT = """
You are VaultAI. A secure vault assistant.

Rules:
- User secrets (passwords, usernames, IDs) NEVER appear in your output.
- If the user is not UNLOCKED ({UNLOCKED}) or video_verified ({VERIFIED}) == False:
    → Ask them to complete verification.
- You MUST use tools when the user asks to save, retrieve, update, list, or delete.
- You can explain what you're doing in natural language, but do not leak secrets.
"""

# Tool definitions (schemas)
VAULT_FUNCTIONS = [
    {
        "name": "save_secret",
        "description": "Save a login/password/ID/note into the user's encrypted vault.",
        "parameters": {
            "type": "object",
            "properties": {
                "secret_type": {"type": "string"},
                "service": {"type": "string"},
                "fields": {"type": "object"},
            },
            "required": ["secret_type", "service", "fields"],
        },
    },
    {
        "name": "retrieve_secret",
        "description": "Retrieve a user record by service name.",
        "parameters": {
            "type": "object",
            "properties": {"service": {"type": "string"}},
            "required": ["service"],
        },
    },
    {
        "name": "list_secrets",
        "description": "List all stored services/logins/IDs for this user.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "generate_password",
        "description": "Generate a strong password.",
        "parameters": {
            "type": "object",
            "properties": {"length": {"type": "number", "default": 16}},
        },
    }
]
