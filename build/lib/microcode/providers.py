"""Provider presets and client factory."""

# Edit this dict to add providers / preset models.
PROVIDERS = {
    "anthropic": {"label": "Anthropic", "base_url": None,
                  "models": ["claude-sonnet-5-5", "claude-opus-5-5", "claude-haiku-4-5-20251001"]},
    "openai": {"label": "OpenAI", "base_url": "https://api.openai.com/v1",
               "models": ["gpt-4.1", "gpt-5-mini"]},
    "custom": {"label": "Custom URL (any OpenAI-compatible API)", "base_url": None, "models": []},
}


def make_client(c):
    """Build an SDK client from the saved config. SDKs are imported lazily."""
    if c["provider"] == "anthropic":
        import anthropic
        return anthropic.Anthropic(api_key=c["api_key"])
    import openai
    return openai.OpenAI(api_key=c["api_key"], base_url=c["base_url"] or None)
