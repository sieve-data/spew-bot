import sieve
import os
import json # Added for json.dumps
from typing import Dict, List, Literal # Added Literal and List
from pydantic import BaseModel # Added BaseModel
import dotenv # Added dotenv

# Import the utility function
from utils.llm import call_llm # Corrected import path
# from moviepy import VideoFileClip, concatenate_videoclips, ImageClip # Commenting out
# from PIL import Image # Commenting out
# import numpy as np # Commenting out
# import cv2 # Commenting out
# import requests # Commenting out
# import tempfile # Keep for potential future use if temporary files are needed # Removed
# import shutil # Keep for potential future use if temporary files are needed # Removed

# Define Pydantic models for structured output
class VisualSegment(BaseModel):
    type: Literal["animation", "image"]
    description: str
    start_time: float
    end_time: float

class VisualPlan(BaseModel):
    segments: List[VisualSegment]

# Function to create the visual plan
def _create_visual_plan(transcription: dict) -> VisualPlan:
    """
    Create a plan for what visuals to generate based on the transcription using an LLM.
    """
    print("  🤖 Calling LLM to create visual plan...")
    dotenv.load_dotenv() # Ensure environment variables are loaded for API keys
    
    system_prompt_content = "Analyze this transcript and create a detailed visual plan for a video."
    user_prompt_content = f"""
        {json.dumps(transcription, indent=2)}

        Above, I have a transcript with timestamps. Please analyze it and create a detailed visual plan.

        Break the explanation into logical segments and for each segment, suggest either:
        - An animation (for complex concepts, processes, or math)
        - An image (for simpler illustrations or examples)

        Specify exact start_time and end_time for each visual and provide a clear, detailed description of what to display.

        It's crucial to remember that a person will already be narrating the content. Your task is to create a secondary, simple presentation next to them. Focus on illustrating on-paper concepts or topics suitable for 2D animations in the style of 3Blue1Brown.
        For example, use static images for straightforward visual references like, "Hey, look at this pool. Let's calculate the area of this pool." These should be simple and direct.
        Use animations specifically for visualizing mathematical concepts, such as illustrating the area under a curve for integration. Keep these animations simple and flat, emphasizing clarity and understanding over complexity.
        Aim for more animations than images.
        Please ensure that your designs are clear, simple, and help convey mathematical ideas without unnecessary complexity. Our goal is to make the concepts accessible and easy to understand.
        """

    try:
        # Use the updated call_llm with response_model for structured output
        visual_plan_response = call_llm(
            provider="gpt", # Assuming OpenAI for structured output with Pydantic
            system_prompt=system_prompt_content,
            prompt=user_prompt_content,
            response_model=VisualPlan,
            model="gpt-4o" # Or your preferred model that supports structured output, like o3-mini if it does
        )
            
        return visual_plan_response

    except Exception as e:
        print(f"  ❌ Error creating visual plan: {str(e)}")
        # Fallback: return an empty plan or raise the error
        # For now, let's raise to make the error visible during testing
        raise

@sieve.function(
    name="spew_visuals_generator",
    python_packages=[
        "openai", 
        "anthropic",
        "python-dotenv",
        "pydantic"
    ],
    environment_variables=[
        sieve.Env(name="OPENAI_API_KEY"),
        sieve.Env(name="ANTHROPIC_API_KEY")
    ]
)
def generate_visuals(transcription: dict) -> sieve.File: # Changed return type to dict for now
    """
    Generate animated and static visuals based on the transcription
    
    Args:
        transcription: Dictionary containing the transcription data from speech synthesis
        
    Returns:
        dict: The visual plan
    """
    print("🎨 Starting visuals generation (barebones - plan only)...")
    
    # Step 1: Create visual plan
    print("\n📋 Step 1: Creating visual plan...")
    visual_plan = _create_visual_plan(transcription)
    
    if visual_plan and visual_plan.segments:
        print(f"✅ Created plan with {len(visual_plan.segments)} segments")
    else:
        print("⚠️  Visual plan is empty or invalid.")
        # For testing, we'll return an empty dict or the partial plan
        return {"error": "Visual plan generation failed or resulted in an empty plan."}

    # For now, we are only returning the plan itself, not a Sieve.File
    print("✅ Visual plan generation complete.")
    return visual_plan.dict() # Return the plan as a dictionary

# All helper functions like _create_visual_plan, _create_animation, 
# _generate_manim_code, _execute_manim, _create_static_image, 
# and _assemble_visuals have been removed.
# Re-ensure _create_visual_plan is here, as it's essential.
# If _create_visual_plan was mistakenly indicated as removed by the comment above,
# it should be kept as it's the core of the "plan generation" part.
