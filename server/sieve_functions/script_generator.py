import sieve
from openai import OpenAI

@sieve.function(
    name="spew_script_generator",
    python_packages=["openai"],
    environment_variables=[
        sieve.Env(name="OPENAI_API_KEY")
    ]
)
def generate_script(query: str, name: str, style: str) -> str:
    # Initialize OpenAI client (API key loaded automatically from env)
    client = OpenAI()
    
    # Generate the explanation
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a brilliant writer who is capable of writing in the style of any person or celebrity. You are given a query and a style prompt. You need to write an explanation of the query in the style of the celebrity."},
            {"role": "user", "content": f"""
                I want you to write a speech in the style of {name}. It should be about 30 seconds long, with a hard cap of 40 seconds.
                I want you to explain the following in great detail: {query}
                Speak in the following style: {style}. Overall, it's incredibly important to really dive deep into explaining the concepts at a low level. You are a brilliant teacher, so don't hold back.
                Remember, this script shouldn't be too long, it should be about 30 seconds long, with a hard cap of 40 seconds.
            """}
        ]
    )
    
    # Return the generated explanation
    return response.choices[0].message.content
