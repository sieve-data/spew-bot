import sieve
import os
import json # Added for json.dumps
from typing import Dict, List, Literal # Added Literal and List
from pydantic import BaseModel # Added BaseModel
import dotenv # Added dotenv
import tempfile
import shutil
import requests
import io
import cv2
import numpy as np
from PIL import Image

# Import the utility functions
from utils.llm import call_llm, generate_image
# from moviepy import VideoFileClip, concatenate_videoclips, ImageClip # Commenting out
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

def create_static_image(description: str, duration: float, segment_id: str, output_dir: str) -> str:
    """
    Create a video from generated static images.
    
    Args:
        description: Description of the image to generate
        duration: Duration of the video segment in seconds
        segment_id: Unique identifier for this segment
        output_dir: Directory to save the output video
    
    Returns:
        str: Path to the created video file
    """
    print(f"  🖼️ Creating static image video for: {description[:50]}...")
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    video_path = os.path.join(output_dir, f"{segment_id}.mp4")
    
    try:
        # Generate 3 variations of the image for visual interest
        num_images = 3
        image_arrays = []
        
        for i in range(num_images):
            print(f"    Generating image {i+1}/{num_images}...")
            
            # Add slight variation to prompt for diversity
            varied_prompt = f"{description} (style variation {i+1})"
            image_url = generate_image(varied_prompt)
            
            # Download and process the image
            response = requests.get(image_url)
            response.raise_for_status()
            
            # Convert to PIL Image
            img = Image.open(io.BytesIO(response.content))
            
            # Ensure consistent size (1024x1024)
            img = img.resize((1024, 1024), Image.Resampling.LANCZOS)
            
            # Convert to numpy array and then to BGR for OpenCV
            img_array = np.array(img)
            if len(img_array.shape) == 3 and img_array.shape[2] == 3:
                # RGB to BGR
                img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            elif len(img_array.shape) == 3 and img_array.shape[2] == 4:
                # RGBA to BGR
                img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
            else:
                # Grayscale to BGR
                img_bgr = cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)
            
            image_arrays.append(img_bgr)
        
        # Create video from images
        fps = 30
        total_frames = int(fps * duration)
        frames_per_image = total_frames // num_images
        remainder_frames = total_frames % num_images
        
        # Initialize video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video_writer = cv2.VideoWriter(video_path, fourcc, fps, (1024, 1024))
        
        print(f"    Writing {total_frames} frames ({frames_per_image} per image)...")
        
        # Write frames for each image
        for i, img_bgr in enumerate(image_arrays):
            current_frames = frames_per_image
            if i == num_images - 1:  # Add remainder to last image
                current_frames += remainder_frames
            
            for _ in range(current_frames):
                video_writer.write(img_bgr)
        
        video_writer.release()
        
        print(f"  ✅ Created static image video: {video_path}")
        return video_path
        
    except Exception as e:
        print(f"  ❌ Error creating static image video: {e}")
        return None

def _create_placeholder_video(temp_dir: str, filename: str, duration: float = 3.0, color: tuple = (0, 0, 255)) -> str:
    """
    Create a simple colored video for placeholders or errors.
    
    Args:
        temp_dir: Directory to save the video
        filename: Name of the video file
        duration: Duration in seconds
        color: BGR color tuple
    
    Returns:
        str: Path to the created video
    """
    video_path = os.path.join(temp_dir, filename)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video_writer = cv2.VideoWriter(video_path, fourcc, 30, (1024, 1024))
    
    frame = np.full((1024, 1024, 3), color, dtype=np.uint8)
    total_frames = int(30 * duration)
    
    for _ in range(total_frames):
        video_writer.write(frame)
    
    video_writer.release()
    return video_path

def _create_animation_placeholder(temp_dir: str, segment_id: str, duration: float) -> str:
    """Create a placeholder video for animation segments."""
    print(f"  ⏩ Creating animation placeholder: {segment_id}")
    return _create_placeholder_video(
        temp_dir, 
        f"{segment_id}_placeholder.mp4", 
        duration, 
        (0, 100, 200)  # Orange color
    )

def _create_visual_segments(visual_plan: VisualPlan, temp_dir: str) -> list:
    """
    Create visual segments based on the visual plan.
    
    Args:
        visual_plan: The plan containing segment descriptions and timings
        temp_dir: Temporary directory for output files
    
    Returns:
        list: Paths to successfully created video segments
    """
    print("\n🎬 Creating visual segments...")
    segment_paths = []
    
    for i, segment in enumerate(visual_plan.segments):
        segment_id = f"segment_{i:03d}"
        duration = segment.end_time - segment.start_time
        
        print(f"\n  Creating {segment.type} {i+1}/{len(visual_plan.segments)}: {segment.description[:50]}...")
        
        try:
            if segment.type == "image":
                video_path = create_static_image(
                    description=segment.description,
                    duration=duration,
                    segment_id=segment_id,
                    output_dir=temp_dir
                )
                
                if video_path and os.path.exists(video_path):
                    segment_paths.append(video_path)
                    print(f"  ✅ Successfully created image segment: {segment_id}")
                else:
                    print(f"  ❌ Failed to create image segment: {segment_id}")
            
            else:  # animation - placeholder for now
                video_path = _create_animation_placeholder(temp_dir, segment_id, duration)
                segment_paths.append(video_path)
                
        except Exception as e:
            print(f"  ❌ Error creating segment {segment_id}: {e}")
            continue
    
    return segment_paths

@sieve.function(
    name="spew_visuals_generator",
    python_packages=[
        "openai", 
        "anthropic",
        "python-dotenv",
        "pydantic",
        "requests",
        "opencv-python-headless",
        "numpy",
        "Pillow"
    ],
    environment_variables=[
        sieve.Env(name="OPENAI_API_KEY"),
        sieve.Env(name="ANTHROPIC_API_KEY")
    ]
)
def generate_visuals(transcription: dict) -> sieve.File:
    """
    Generate animated and static visuals based on the transcription.
    
    Args:
        transcription: Dictionary containing the transcription data from speech synthesis
        
    Returns:
        sieve.File: Video file with generated visuals
    """
    print("🎨 Starting visuals generation...")
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Step 1: Create visual plan
        print("\n📋 Creating visual plan...")
        visual_plan = _create_visual_plan(transcription)
        
        if not visual_plan or not visual_plan.segments:
            print("⚠️  Visual plan is empty or invalid.")
            video_path = _create_placeholder_video(temp_dir, "empty_plan.mp4", 3.0, (0, 0, 0))  # Black
            return sieve.File(path=video_path)

        print(f"✅ Created plan with {len(visual_plan.segments)} segments")
        
        # Step 2: Create visual segments
        segment_paths = _create_visual_segments(visual_plan, temp_dir)
        
        # Step 3: Return result
        if segment_paths:
            print(f"\n✅ Visual generation complete. Created {len(segment_paths)} segments.")
            return sieve.File(path=segment_paths[0])  # Return first segment for now
        else:
            print("\n⚠️  No segments were created successfully.")
            video_path = _create_placeholder_video(temp_dir, "failed_segments.mp4", 3.0, (0, 0, 255))  # Red
            return sieve.File(path=video_path)
            
    except Exception as e:
        print(f"❌ Error in visual generation: {e}")
        video_path = _create_placeholder_video(temp_dir, "error.mp4", 3.0, (0, 0, 255))  # Red
        return sieve.File(path=video_path)

# All helper functions like _create_visual_plan, _create_animation, 
# _generate_manim_code, _execute_manim, _create_static_image, 
# and _assemble_visuals have been removed.
# Re-ensure _create_visual_plan is here, as it's essential.
# If _create_visual_plan was mistakenly indicated as removed by the comment above,
# it should be kept as it's the core of the "plan generation" part.
