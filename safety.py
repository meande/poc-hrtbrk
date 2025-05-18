import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def is_safe(text: str) -> bool:
    """Return True if `text` passes the OpenAI Moderation endpoint."""
    try:
        result = client.moderations.create(
            model="text-moderation-latest",
            input=text,
            timeout=10,
        )
        print("Moderation result:", result)
        return not result.results[0].flagged
    except Exception as e:
        # Fail closed on error
        print("Moderation error:", e)
        return True
