import os
from openai import OpenAI
from anthropic import Anthropic

# Default models
DEFAULT_GPT_MODEL = "gpt-4o"
DEFAULT_CLAUDE_MODEL = "claude-3-opus-20240229"

def call_llm(provider: str, prompt: str, model: str = None, max_tokens: int = 1024) -> str:
    if provider.lower() == "gpt":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set.")
        client = OpenAI(api_key=api_key)
        current_model = model if model else DEFAULT_GPT_MODEL
        try:
            response = client.chat.completions.create(
                model=current_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            raise
    elif provider.lower() == "claude":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set.")
        client = Anthropic(api_key=api_key)
        current_model = model if model else DEFAULT_CLAUDE_MODEL
        try:
            response = client.messages.create(
                model=current_model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception as e:
            print(f"Error calling Anthropic API: {e}")
            raise
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}. Supported providers are 'gpt' and 'claude'.")
