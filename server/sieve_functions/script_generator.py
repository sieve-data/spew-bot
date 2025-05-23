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
    # Construct the enhanced prompt
    prompt_content = f"""
        You are creating an educational video script for {name} that explains: {query}
        
        CRITICAL REQUIREMENTS:
        1. EDUCATIONAL EXCELLENCE: You must be a brilliant teacher who provides concrete, real-world examples and analogies that make complex concepts crystal clear. Don't just define things - show how they work with specific examples that anyone can understand.
        
        2. PERSONALITY & HUMOR: Follow this style guide exactly: {style}
        
        3. STRUCTURE YOUR EXPLANATION:
        - Start with a relatable hook that connects to the persona's background
        - Provide at least one concrete, detailed example (like using a backyard to explain area)
        - Break down the concept step-by-step with clear reasoning
        - Use analogies and references specific to the persona's expertise/experiences
        - Include personality-appropriate humor and cultural references
        
        4. EXAMPLES TO EMULATE:
        - Kim Kardashian explaining area: "So like, imagine my backyard at my Calabasas house. It's rectangular, right? To find the area I multiply the length times the width..."
        - Kobe explaining persistence: "Look, when I was working on my fadeaway shot, I didn't just practice it once. I broke it down - footwork first, then shoulder positioning, then the release. That's exactly how you approach any complex problem..."
        
        5. TONE: Be genuinely educational while staying completely in character. Make learning fun and memorable through the persona's unique perspective.
        
        CONSTRAINTS:
        - 30 seconds speaking time (approximately 75-90 words)
        - Must include at least one specific, detailed example
        - Must sound natural for the persona
        - Must actually teach the concept clearly
        
        Write the script now for {name} explaining: {query}
    """
    
    # Generate the explanation using the call_llm utility
    explanation = call_llm(
        provider="gpt", 
        prompt=prompt_content
    )
    
    # Return the generated explanation
    return explanation
