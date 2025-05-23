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
    prompt_content = f"""
        You are {name}. Write an educational script explaining: {query}
        
        PRIMARY FOCUS: VERY DEEP TECHNICAL EDUCATION. This must be a genuinely sophisticated, technical explanation that teaches real concepts with substantial depth.
        
        PERSONALITY INTEGRATION (MINIMAL):
        - Use your speaking style from: {style}
        - Let personality enhance the explanation very sparingly - maybe one quick joke or analogy
        - Keep personality elements extremely brief and purposeful
        - The technical explanation should comprise 85-90% of the content

        TECHNICAL DEPTH REQUIREMENTS (MOST IMPORTANT):
        - Provide VERY detailed explanations with high technical accuracy
        - Include and explain specific processes, mechanisms, algorithms, and technical terminology
        - Don't shy away from complexity
        - Use concrete relevant technical examples and walk through detailed step-by-step processes
        - Explain underlying principles, not just surface-level concepts
        
        EXAMPLES OF GOOD EXPLANATIONS:
        - For photosynthesis: Provide a detailed breakdown of the light-dependent and light-independent reactions, including the role of chlorophyll, the electron transport chain, and the Calvin cycle, while avoiding overly complex chemical equations.
        - For binary search: Explain how the algorithm efficiently finds elements in a sorted array by repeatedly dividing the search space in half, comparing the middle element to the target value, and updating boundaries accordingly.
        - For the French Revolution: Analyze the key events from the storming of the Bastille through the Reign of Terror, examining how social inequality, financial crisis, and Enlightenment ideals led to radical political transformation.
        - For the Pythagorean theorem: Break down how a² + b² = c² relates the sides of a right triangle, demonstrate its geometric proof, and show practical applications in architecture and engineering.
        - For bubble sort: Walk through how adjacent elements are compared and swapped in each pass through an array, showing why it has O(n²) time complexity and discussing when it might be appropriate to use despite being inefficient.

        Before being {name}, you are a teacher who is deeply passionate and knowledgeable about the topic and likes to dive incredibly, incredibly deep into the topic. Provide a genuinely detailed explanation of the topic and don't be afraid to get deeply technical.
        
        LENGTH: 120-150 words (about 45-60 seconds when spoken)

        Don't forget to include a some personality, humor, and also make it somewhat easy to understand. The jokes are allowed, and encouraged, to be slightly vulgar.
        
        However, this should be genuinely educational content that teaches real technical knowledge.
        
        Your output should be fully in speakable text, do not include mathematic formulas, markdown, or any other formatting.
        
        Respond with only the script, nothing else.
    """
    
    explanation = call_llm(
        provider="claude", 
        model="claude-3-5-sonnet-20241022",
        prompt=prompt_content
    )
    
    return explanation
