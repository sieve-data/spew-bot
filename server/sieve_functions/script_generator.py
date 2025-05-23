import sieve
from utils.llm import call_llm

@sieve.function(
    name="spew_script_generator",
    python_packages=["openai", "anthropic"],
    environment_variables=[
        sieve.Env(name="OPENAI_API_KEY"),
        sieve.Env(name="ANTHROPIC_API_KEY")
    ]
)
def generate_script(query: str, name: str, style: str) -> str:
    # Construct the prompt
    prompt_content = f"""
        I want you to write a speech in the style of {name}. It should be about 30 seconds long, with a hard cap of 40 seconds.
        I want you to explain the following in great detail: {query}
        Speak in the following style: {style}. Overall, it's incredibly important to really dive deep into explaining the concepts at a low level. You are a brilliant teacher, so don't hold back.
        Remember, this script shouldn't be too long, it should be about 30 seconds long, with a hard cap of 40 seconds.
    """
    
    # Generate the explanation using the call_llm utility
    explanation = call_llm(
        provider="gpt", 
        prompt=prompt_content
    )
    
    # Return the generated explanation
    return explanation
