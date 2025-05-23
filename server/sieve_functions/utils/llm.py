import os
import json
from openai import OpenAI
from anthropic import Anthropic
from pydantic import BaseModel, ValidationError
from typing import Type, Optional, Union

# Default models
DEFAULT_GPT_MODEL = "gpt-4o"
DEFAULT_CLAUDE_MODEL = "claude-3-opus-20240229"

def _call_gpt(
    prompt: str,
    model: str = None,
    max_tokens: int = 1024,
    system_prompt: Optional[str] = None,
    response_model: Optional[Type[BaseModel]] = None
) -> Union[str, BaseModel]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set.")
    
    client = OpenAI(api_key=api_key)
    current_model = model if model else DEFAULT_GPT_MODEL

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        if response_model:
            # Use client.beta.chat.completions.parse for structured output
            completion = client.beta.chat.completions.parse(
                model=current_model,
                messages=messages,
                max_tokens=max_tokens, # Max tokens might still be relevant
                response_format=response_model # Pass the Pydantic model directly
            )
            # The .parse() method should directly return the parsed Pydantic model instance
            # from the first choice's message.
            if completion.choices and completion.choices[0].message and hasattr(completion.choices[0].message, 'parsed'):
                 return completion.choices[0].message.parsed
            else:
                # This case should ideally not be hit if parse works as expected
                print("Error: LLM response via .parse() did not yield expected parsed message structure.")
                raise ValueError("Failed to get parsed message from LLM response using .parse().")
        else:
            # Standard call for non-structured response
            response = client.chat.completions.create(
                model=current_model,
                messages=messages,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
    except AttributeError as e:
        if "'OpenAI' object has no attribute 'beta'" in str(e) or "'Completions' object has no attribute 'parse'" in str(e):
            print(f"AttributeError: {e}. This likely means the OpenAI client is not patched by a library like 'instructor', or the SDK version doesn't support .beta.chat.completions.parse. Make sure 'instructor' is installed and the client is patched if necessary.")
            raise
        raise
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        raise

def _call_claude(
    prompt: str,
    model: str = None,
    max_tokens: int = 1024,
    system_prompt: Optional[str] = None,
) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set.")
    client = Anthropic(api_key=api_key)
    current_model = model if model else DEFAULT_CLAUDE_MODEL

    # messages_claude = []
    # main_prompt_claude = prompt
    # if system_prompt:
    #      messages_claude.append({"role": "user", "content": system_prompt})
    #      messages_claude.append({"role": "assistant", "content": "Understood."})
    # messages_claude.append({"role": "user", "content": main_prompt_claude})

    try:
        response = client.messages.create(
            model=current_model,
            max_tokens=max_tokens,
            system=system_prompt if system_prompt else None,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        print(f"Error calling Anthropic API: {e}")
        raise

def call_llm(
    provider: str, 
    prompt: str, 
    model: str = None, 
    max_tokens: int = 1024, 
    system_prompt: Optional[str] = None,
    response_model: Optional[Type[BaseModel]] = None
) -> Union[str, BaseModel]:
    if provider.lower() == "gpt":
        return _call_gpt(prompt, model, max_tokens, system_prompt, response_model)
    elif provider.lower() == "claude":
        if response_model:
            print("Warning: 'response_model' is provided but not natively supported for Claude in this utility. Returning raw text.")
        return _call_claude(prompt, model, max_tokens, system_prompt)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}. Supported providers are 'gpt' and 'claude'.")
