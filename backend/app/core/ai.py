import anthropic

from app.core.config import settings


def get_anthropic_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(
        api_key=settings.ANTHROPIC_API_KEY,
        base_url=settings.ANTHROPIC_BASE_URL,
    )
