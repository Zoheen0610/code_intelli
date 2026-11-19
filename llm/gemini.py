"""Talk to Gemini. The ONLY file in the project that imports google.genai."""
from dotenv import load_dotenv
from google import genai
from google.genai import errors

load_dotenv()

MODEL = "gemini-3.5-flash-lite"   # one place to change it


class LLMError(Exception):
    """Any failure talking to the LLM. Callers catch this, never Gemini's own errors."""

class LLMConfigError(LLMError):
    """Bad key, bad model or missing setup: retrying won't help, fix the config."""

class LLMBusyError(LLMError):
    """The server is overloaded or rate-limited: retrying later may work."""


def ask_llm(prompt: str) -> str:
    """Send one prompt, return the reply text. Raises LLMError if anything goes wrong."""
    
    try:
        client = genai.Client()
    except ValueError as e:
        raise LLMConfigError("No Gemini API key: set GEMINI_API_KEY in your .env file") from e

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt
        )
    except errors.ServerError as e:
        raise LLMBusyError(f"Gemini is busy ({e.code}), try again later") from e

    except errors.ClientError as e:
        if e.code == 429:
            raise LLMBusyError("The rate limit has been hit, please try after a while.") from e     
        raise LLMConfigError(f"Gemini rejected the request {e.code}: check the key and model name") from e
    text = response.text
    if not text:                # catches None AND an empty string ""
        raise LLMError("Gemini returned an empty reply")
    return text
