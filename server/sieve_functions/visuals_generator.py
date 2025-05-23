import sieve
import os
import json # Added for json.dumps
import re # Added for regex operations
from typing import Dict, List, Literal, Optional # Added Literal and List
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

# MoviePy version-agnostic imports
try:
    # Try MoviePy v2.0+ imports (no .editor)
    from moviepy import VideoFileClip, concatenate_videoclips, ImageClip
except ImportError:
    # Fallback to MoviePy v1.x imports (with .editor)
    from moviepy.editor import VideoFileClip, concatenate_videoclips, ImageClip
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

def _generate_animation_code(description: str, duration: float, llm_provider: str = "claude", llm_model: str = "claude-3-5-sonnet-20241022") -> Optional[str]:
    """
    Generate Matplotlib animation code using LLM based on the description and duration.
    
    Args:
        description: Description of the animation to create
        duration: Target duration in seconds
        llm_provider: LLM provider to use ("anthropic", "gpt", "gemini")
        llm_model: Specific model to use
        
    Returns:
        Generated Python code string or None if generation fails
    """
    print(f"  🤖 Generating animation code with {llm_provider}/{llm_model}...")
    
    system_prompt = """You are an expert in Python programming and Matplotlib animations. You create beautiful, mathematical visualizations in the style of 3Blue1Brown. Your code is always complete, self-contained, and production-ready."""
    
    generation_prompt = f"""
        Create Python code using Matplotlib's animation module to generate a mathematical animation.

        The animation should be approximately {duration} seconds long.

        AVAILABLE LIBRARIES (use ONLY these in addition to the standard libraries):
        - matplotlib.pyplot as plt
        - matplotlib.animation (FuncAnimation, etc.)
        - numpy as np
        - scipy (all submodules: scipy.special, scipy.integrate, scipy.optimize, etc.)
        - sympy (for symbolic math)
        - seaborn as sns (for statistical plots)

        CRITICAL REQUIREMENTS:
        1. Use matplotlib.animation.FuncAnimation for the animation
        2. Include ALL necessary imports from the AVAILABLE LIBRARIES list above
        3. DO NOT import any libraries not listed above
        4. Set the animation to run for exactly {duration} seconds (fps = 30, so frames = {int(duration * 30)})
        5. Use anim.save('animation.mp4', writer='pillow', fps=30) to save the file (NOT ffmpeg - use pillow writer)
        6. IMPORTANT: Add automatic writer detection at the end of your code:
           ```python
           # Try to save with the best available writer
           try:
               anim.save('animation.mp4', writer='ffmpeg', fps=30)
           except:
               try:
                   anim.save('animation.mp4', writer='pillow', fps=30)
               except:
                   anim.save('animation.mp4', writer='imagemagick', fps=30)
           ```
        7. The code MUST be complete and self-contained - no external dependencies beyond the AVAILABLE LIBRARIES
        8. Include clear, descriptive comments explaining the animation logic
        9. Use plt.style.use('dark_background') for a clean dark theme
        10. Make text readable with appropriate font sizes (minimum 14pt)
        11. For mathematical expressions, use LaTeX formatting with plt.text() and r'$...$' syntax
        12. The code should NOT use plt.show() - it MUST save to a file
        13. Avoid deprecated Matplotlib features
        14. Use figsize=(10.8, 10.8) for mobile-friendly square video dimensions (1080x1080)
        15. Set up proper axis limits and remove unnecessary axes/ticks for clean visuals
        16. Use smooth, continuous animations with proper easing
        17. Ensure colors are vibrant and contrasting against the dark background

        ANIMATION CONCEPT:
        {description}

        STYLE GUIDELINES:
        - Minimalist, clean aesthetic similar to 3Blue1Brown
        - Use smooth transitions and transformations
        - Focus on mathematical clarity and visual appeal
        - Use colors that pop against dark background (blues, oranges, whites, greens)
        - Avoid clutter - emphasize the core mathematical concept

        Return ONLY the complete Python code with no markdown formatting or additional explanations.
        """

    try:
        # Generate the code using call_llm
        response_text = call_llm(
            provider=llm_provider,
            model=llm_model,
            system_prompt=system_prompt,
            prompt=generation_prompt
        )
        
        if not response_text:
            print("  ❌ LLM returned empty response")
            return None
        
        # Clean the code (remove markdown code blocks if present)
        cleaned_code = re.sub(r'^```python\s*', '', response_text, flags=re.MULTILINE)
        cleaned_code = re.sub(r'^```\s*$', '', cleaned_code, flags=re.MULTILINE)
        cleaned_code = cleaned_code.strip()
        
        print(f"  ✅ Generated {len(cleaned_code)} characters of animation code")
        return cleaned_code
        
    except Exception as e:
        print(f"  ❌ Error generating animation code: {e}")
        return None

def _fix_animation_code(original_code: str, error_message: str, original_description: str, duration: float, llm_provider: str = "claude", llm_model: str = "claude-3-5-sonnet-20241022") -> Optional[str]:
    print(f"  🔧 Fixing animation code with {llm_provider}/{llm_model}...")
    
    system_prompt = """You are an expert Python developer and Matplotlib animation specialist. You excel at debugging code, identifying root causes of errors, and creating production-ready fixes. You always provide complete, working solutions."""
    
    comprehensive_fix_prompt = f"""
        You need to analyze and fix a Matplotlib animation that failed to execute.

        ORIGINAL ANIMATION GOAL:
        {original_description}

        TARGET DURATION: {duration} seconds (fps=30, total frames={int(duration * 30)})

        AVAILABLE LIBRARIES (use ONLY these in addition to the standard libraries):
        - matplotlib.pyplot as plt
        - matplotlib.animation (FuncAnimation, etc.)
        - numpy as np
        - scipy (all submodules: scipy.special, scipy.integrate, scipy.optimize, etc.)
        - sympy (for symbolic math)
        - seaborn as sns (for statistical plots)

        FAILED CODE:
        ```python
        {original_code}
        ```

        ERROR MESSAGE:
        ```
        {error_message}
        ```

        TASK:
        1. First, understand what went wrong and identify the root cause
        2. Then, provide a complete, fixed version of the code

        CRITICAL REQUIREMENTS FOR THE FIX:
        - Animation must be exactly {duration} seconds long (fps=30)
        - Use anim.save('animation.mp4', writer='pillow', fps=30) to save
        - Include ALL necessary imports from the AVAILABLE LIBRARIES list above
        - DO NOT import any libraries not listed in AVAILABLE LIBRARIES
        - Use plt.style.use('dark_background') for consistent styling
        - NO plt.show() - only save to file
        - Ensure all mathematical operations are safe (no division by zero, etc.)
        - Handle edge cases and potential runtime errors
        - Use figsize=(10.8, 10.8) for mobile-friendly square video dimensions (1080x1080)
        - Code must be complete and self-contained

        STYLE REQUIREMENTS:
        - Clean, minimalist 3Blue1Brown aesthetic
        - Dark background with contrasting colors
        - Readable text (minimum 14pt)
        - LaTeX formatting for math: r'$...$'
        - Smooth animations with proper easing

        IMPORTANT: If the original approach was fundamentally flawed, completely rewrite the code rather than patching. Focus on creating robust, error-free code that will definitely work.
        IMPORTANT: DO NOT TRY TO INSTALL ANY NEW LIBRARIES, JUST FIX THE CODE USING ONLY THE AVAILABLE LIBRARIES.

        Provide ONLY the complete, fixed Python code with no explanations or markdown formatting.
        """

    try:
        # Generate the fixed code in one call
        fixed_code_response = call_llm(
            provider=llm_provider,
            model=llm_model,
            system_prompt=system_prompt,
            prompt=comprehensive_fix_prompt
        )
        
        if not fixed_code_response:
            print("  ❌ LLM returned empty response for code fix")
            return None
        
        # Clean the fixed code
        cleaned_fixed_code = re.sub(r'^```python\s*', '', fixed_code_response, flags=re.MULTILINE)
        cleaned_fixed_code = re.sub(r'^```\s*$', '', cleaned_fixed_code, flags=re.MULTILINE)
        cleaned_fixed_code = cleaned_fixed_code.strip()
        
        print(f"  ✅ Generated {len(cleaned_fixed_code)} characters of fixed code")
        return cleaned_fixed_code
        
    except Exception as e:
        print(f"  ❌ Error fixing animation code: {e}")
        return None

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

        CRITICAL: Ensure that segments are in chronological order and do not overlap. Each segment should have:
        - start_time that is >= the previous segment's end_time
        - end_time that is > start_time
        - Logical temporal progression that matches the transcript

        It's crucial to remember that a person will already be narrating the content. Your task is to create a secondary, simple presentation next to them. Focus on illustrating on-paper concepts or topics suitable for 2D animations in the style of 3Blue1Brown.
        For example, use static images for straightforward visual references like, "Hey, look at this pool. Let's calculate the area of this pool." These should be simple and direct.
        Use animations specifically for visualizing mathematical concepts, such as illustrating the area under a curve for integration. Keep these animations simple and flat, emphasizing clarity and understanding over complexity.
        Aim for more animations than images.
        Please ensure that your designs are clear, simple, and help convey mathematical ideas without unnecessary complexity. Our goal is to make the concepts accessible and easy to understand.

        The first segment should **always** be an animation.
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

        # Ensure segments are sorted by start_time (defensive programming)
        if visual_plan_response and visual_plan_response.segments:
            visual_plan_response.segments = sorted(
                visual_plan_response.segments, 
                key=lambda x: x.start_time
            )
            
            print(f"  ✅ Visual plan created with {len(visual_plan_response.segments)} segments:")
            for i, segment in enumerate(visual_plan_response.segments):
                print(f"    📍 Segment {i+1}: {segment.start_time:.1f}s-{segment.end_time:.1f}s ({segment.type}) - {segment.description[:50]}...")
        else:
            print(f"  ✅ Visual plan created: {visual_plan_response}")
            
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
            
            # Ensure consistent mobile-friendly size (1080x1080)
            img = img.resize((1080, 1080), Image.Resampling.LANCZOS)
            
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
        video_writer = cv2.VideoWriter(video_path, fourcc, fps, (1080, 1080))
        
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
    video_writer = cv2.VideoWriter(video_path, fourcc, 30, (1080, 1080))
    
    frame = np.full((1080, 1080, 3), color, dtype=np.uint8)
    total_frames = int(30 * duration)
    
    for _ in range(total_frames):
        video_writer.write(frame)
    
    video_writer.release()
    return video_path

def _create_matplotlib_animation(description: str, duration: float, segment_id: str, output_dir: str) -> Optional[str]:
    """
    Create a matplotlib animation using LLM-generated code with error correction and retry logic.
    
    Args:
        description: Description of the animation to create
        duration: Target duration in seconds
        segment_id: Unique identifier for this animation segment
        output_dir: Directory to save the animation file
        
    Returns:
        Path to the created animation MP4 file or None if creation fails
    """
    print(f"  🎬 Creating animation: {description[:50]}...")
    
    # Configuration
    max_attempts = 3
    llm_provider = "claude"
    llm_model = "claude-3-5-sonnet-20241022"
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Step 1: Generate initial animation code
        print(f"  📝 Generating animation code...")
        animation_code = _generate_animation_code(
            description=description,
            duration=duration,
            llm_provider=llm_provider,
            llm_model=llm_model
        )
        
        if not animation_code:
            print("  ❌ Failed to generate initial animation code")
            return None
        
        # Step 2: Execute with retry and fix loop
        return _execute_with_retry(
            animation_code=animation_code,
            description=description,
            duration=duration,
            segment_id=segment_id,
            output_dir=output_dir,
            max_attempts=max_attempts,
            llm_provider=llm_provider,
            llm_model=llm_model
        )
        
    except Exception as e:
        print(f"  ❌ Unexpected error in animation creation: {e}")
        return None

def _execute_with_retry(animation_code: str, description: str, duration: float, segment_id: str, 
                       output_dir: str, max_attempts: int, llm_provider: str, llm_model: str) -> Optional[str]:
    """
    Execute animation code with retry and fix logic.
    
    Args:
        animation_code: Initial Python code to execute
        description: Original animation description
        duration: Target duration in seconds
        segment_id: Unique identifier for this segment
        output_dir: Output directory
        max_attempts: Maximum number of execution attempts
        llm_provider: LLM provider for code fixing
        llm_model: LLM model for code fixing
        
    Returns:
        Path to successful animation or None if all attempts fail
    """
    current_code = animation_code
    
    for attempt in range(max_attempts):
        print(f"  🔄 Execution attempt {attempt + 1}/{max_attempts}")
        
        # Try to execute the current code
        result = _execute_animation_code(
            animation_code=current_code,
            segment_id=segment_id,
            output_dir=output_dir,
            duration=duration
        )
        
        # Check if execution was successful
        if result["success"]:
            video_path = result["video_path"]
            print(f"  ✅ Animation created successfully: {video_path}")
            return video_path
        
        # Execution failed - log the error
        error_message = result["error_message"]
        print(f"  ❌ Execution failed: {error_message[:100]}...")
        
        # If this was the last attempt, give up
        if attempt == max_attempts - 1:
            print(f"  🛑 Max attempts ({max_attempts}) reached. Animation creation failed.")
            break
        
        # Try to fix the code for the next attempt
        print(f"  🔧 Attempting to fix code...")
        fixed_code = _fix_animation_code(
            original_code=current_code,
            error_message=error_message,
            original_description=description,
            duration=duration,
            llm_provider=llm_provider,
            llm_model=llm_model
        )
        
        if not fixed_code:
            print(f"  ❌ Failed to fix code. Stopping attempts.")
            break
        
        current_code = fixed_code
        print(f"  ✨ Code fixed, trying again...")
    
    return None

def _execute_animation_code(animation_code: str, segment_id: str, output_dir: str, duration: float) -> dict:
    """
    Execute matplotlib animation code and return the result.
    
    Args:
        animation_code: Python code string to execute
        segment_id: Unique identifier for this segment
        output_dir: Directory to save the animation
        duration: Expected duration in seconds
        
    Returns:
        dict: {"success": bool, "video_path": str|None, "error_message": str|None}
    """
    import subprocess
    import tempfile
    
    print(f"  🔄 Executing animation code for segment {segment_id}...")
    
    # Define the output path
    output_path = os.path.join(output_dir, f"{segment_id}.mp4")
    
    try:
        # Modify the code to ensure it saves to the correct path
        # Replace any existing 'animation.mp4' with our target path
        modified_code = re.sub(
            r"anim\.save\(['\"]animation\.mp4['\"]",
            f"anim.save('{output_path}'",
            animation_code
        )
        
        # If no anim.save found, append one
        if "anim.save(" not in modified_code:
            modified_code += f"\nanim.save('{output_path}', writer='pillow', fps=30)\n"
        
        # Create a temporary script file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as script_file:
            script_file.write(modified_code)
            script_path = script_file.name
        
        print(f"  📜 Executing script: {script_path}")
        
        # Execute the script
        result = subprocess.run(
            ["python", script_path],
            capture_output=True,
            text=True,
            timeout=120  # Increase timeout to 2 minutes for complex animations
        )
        
        # Clean up the temporary script
        try:
            os.unlink(script_path)
        except:
            pass
        
        # Check if execution was successful
        if result.returncode == 0:
            # Check if the output file was created
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                print(f"  ✅ Animation saved successfully: {output_path}")
                return {
                    "success": True,
                    "video_path": output_path,
                    "error_message": None
                }
            else:
                error_msg = f"Script ran but no output file created at {output_path}"
                print(f"  ❌ {error_msg}")
                return {
                    "success": False,
                    "video_path": None,
                    "error_message": error_msg
                }
        else:
            # Script execution failed - provide detailed error info
            stdout_preview = result.stdout
            stderr_preview = result.stderr
            
            error_msg = f"Script execution failed with return code {result.returncode}:\nSTDOUT: {stdout_preview}\nSTDERR: {stderr_preview}"
            
            # Log more details for debugging
            print(f"  ❌ Execution failed with return code: {result.returncode}")
            print(f"  📄 STDOUT: {stdout_preview}")
            print(f"  🚨 STDERR: {stderr_preview}")
            
            return {
                "success": False,
                "video_path": None,
                "error_message": error_msg
            }
            
    except subprocess.TimeoutExpired:
        error_msg = f"Script execution timed out after 120 seconds"
        print(f"  ⏱️ {error_msg}")
        return {
            "success": False,
            "video_path": None,
            "error_message": error_msg
        }
        
    except Exception as e:
        error_msg = f"Unexpected error during script execution: {str(e)}"
        print(f"  ❌ {error_msg}")
        return {
            "success": False,
            "video_path": None,
            "error_message": error_msg
        }

def _create_visual_segments(visual_plan: VisualPlan, temp_dir: str) -> list:
    """
    Create visual segments based on the visual plan.
    
    Args:
        visual_plan: The plan containing segment descriptions and timings
        temp_dir: Temporary directory for output files
    
    Returns:
        list: Dictionaries with segment data including paths, timings, and metadata
    """
    print("\n🎬 Creating visual segments...")
    print(f"  📊 Total segments to process: {len(visual_plan.segments)}")
    segment_data_list = []
    
    for i, segment in enumerate(visual_plan.segments):
        segment_id = f"segment_{i:03d}"
        duration = segment.end_time - segment.start_time
        
        print(f"\n  📍 Processing segment {i+1}/{len(visual_plan.segments)}")
        print(f"  Creating {segment.type} {i+1}/{len(visual_plan.segments)}: {segment.description[:50]}...")
        
        try:
            if segment.type == "image":
                print(f"  🖼️ Calling create_static_image for {segment_id}...")
                video_path = create_static_image(
                    description=segment.description,
                    duration=duration,
                    segment_id=segment_id,
                    output_dir=temp_dir
                )
                
                print(f"  📤 create_static_image returned: {video_path}")
                
                if video_path and os.path.exists(video_path):
                    segment_data_list.append({
                        'path': video_path,
                        'start_time': segment.start_time,
                        'end_time': segment.end_time,
                        'duration': duration,
                        'type': 'image',
                        'segment_id': segment_id
                    })
                    print(f"  ✅ Successfully created image segment: {segment_id}")
                else:
                    print(f"  ❌ Failed to create image segment: {segment_id}")
            
            else:  # animation
                print(f"  🎬 Calling _create_matplotlib_animation for {segment_id}...")
                video_path = _create_matplotlib_animation(
                    description=segment.description,
                    duration=duration,
                    segment_id=segment_id,
                    output_dir=temp_dir
                )
                
                print(f"  📤 _create_matplotlib_animation returned: {video_path}")
                
                if video_path and os.path.exists(video_path):
                    segment_data_list.append({
                        'path': video_path,
                        'start_time': segment.start_time,
                        'end_time': segment.end_time,
                        'duration': duration,
                        'type': 'animation',
                        'segment_id': segment_id
                    })
                    print(f"  ✅ Successfully created animation segment: {segment_id}")
                else:
                    print(f"  ❌ Failed to create animation segment: {segment_id}. Falling back to static image generation.")
                    # Fallback to static image generation instead of placeholder
                    fallback_video_path = create_static_image(
                        description=segment.description,
                        duration=duration,
                        segment_id=f"{segment_id}_fallback",
                        output_dir=temp_dir
                    )
                    
                    if fallback_video_path and os.path.exists(fallback_video_path):
                        segment_data_list.append({
                            'path': fallback_video_path,
                            'start_time': segment.start_time,
                            'end_time': segment.end_time,
                            'duration': duration,
                            'type': 'image',
                            'segment_id': segment_id
                        })
                        print(f"  ✅ Successfully created fallback image segment: {segment_id}")
                    else:
                        print(f"  ❌ Fallback image generation also failed for {segment_id}. Creating placeholder.")
                        # Only create placeholder if both animation and image generation fail
                        placeholder_path = _create_placeholder_video(temp_dir, f"{segment_id}_total_fail.mp4", duration, (255, 165, 0))  # Orange for total fail
                        segment_data_list.append({
                            'path': placeholder_path,
                            'start_time': segment.start_time,
                            'end_time': segment.end_time,
                            'duration': duration,
                            'type': 'placeholder',
                            'segment_id': segment_id
                        })
                
            print(f"  ✅ Completed processing segment {i+1}/{len(visual_plan.segments)}")
                
        except Exception as e:
            print(f"  ❌ Error creating segment {segment_id}: {e}")
            print(f"  �� Continuing to next segment...")
            continue
    
    print(f"\n📊 Segment processing complete. Created {len(segment_data_list)} segments.")
    return segment_data_list

def _assemble_visual_segments(segments_data: list, output_dir: str, final_filename: str = "final_visuals.mp4") -> Optional[str]:
    """
    Assembles individual video segments into a final video using MoviePy.
    
    Args:
        segments_data: List of dictionaries with segment info, sorted by start_time.
                      Each dict contains: {'path': str, 'start_time': float, 'end_time': float, 'duration': float}
        output_dir: Directory to save the final assembled video
        final_filename: Name for the output file (default: "final_visuals.mp4")
        
    Returns:
        str: Path to the final assembled video or None if assembly failed
    """
    print("\n🎬 Assembling visual segments into final video...")
    print(f"  📊 Processing {len(segments_data)} segments")
    
    try:
        # Initialize clips list and timeline tracking
        clips = []
        current_timeline_end = 0.0
        
        # Ensure segments are sorted by start_time (should already be sorted from visual plan)
        segments_data_sorted = sorted(segments_data, key=lambda x: x['start_time'])
        
        print(f"  🔄 Segment order verification:")
        for i, segment_info in enumerate(segments_data_sorted):
            print(f"    📍 Segment {i+1}: {segment_info['start_time']:.1f}s-{segment_info['end_time']:.1f}s ({segment_info['segment_id']})")
        
        # Iterate through each segment
        for i, segment_info in enumerate(segments_data_sorted):
            segment_path = segment_info['path']
            expected_duration = segment_info['duration']
            segment_id = segment_info.get('segment_id', f'segment_{i}')
            
            print(f"  📹 Loading segment {i+1}/{len(segments_data_sorted)}: {os.path.basename(segment_path)}")
            print(f"    ⏱️  Expected timing: {segment_info['start_time']:.1f}s-{segment_info['end_time']:.1f}s")
            
            # Check if segment file exists
            if not os.path.exists(segment_path):
                print(f"  ⚠️  Warning: Segment file not found: {segment_path}")
                continue
            
            try:
                # Load the segment video clip (no audio for visuals)
                clip = VideoFileClip(segment_path, audio=False)
                
                # Validate the clip
                if clip.duration <= 0:
                    print(f"  ⚠️  Warning: Segment {i+1} has zero or negative duration ({clip.duration}s)")
                    clip.close()
                    continue
                
                # Log clip information
                print(f"    ✅ Loaded: {clip.duration:.2f}s (expected: {expected_duration:.2f}s)")
                print(f"    📐 Dimensions: {clip.w}x{clip.h}")
                
                # Add to clips list
                clips.append(clip)
                current_timeline_end += clip.duration
                
            except Exception as e:
                print(f"  ❌ Error loading segment {i+1}: {e}")
                continue
        
        # Check if we have any valid clips to assemble
        if not clips:
            print("  ❌ No valid clips to assemble")
            return None
        
        print(f"  🔗 Concatenating {len(clips)} clips (total duration: {current_timeline_end:.2f}s)...")
        print(f"  📋 Assembly order: {' → '.join([f'Segment{i+1}' for i in range(len(clips))])}")
        
        # Concatenate all clips using compose method
        final_clip = concatenate_videoclips(clips, method="compose")
        
        # Define output path
        final_video_output_path = os.path.join(output_dir, final_filename)
        
        # Write the final video file
        print(f"  💾 Writing final video to: {final_video_output_path}")
        print(f"    📊 Final video duration: {final_clip.duration:.2f}s")
        
        final_clip.write_videofile(
            final_video_output_path,
            codec='libx264',
            audio_codec='aac',  # Include for compatibility, though visuals typically have no audio
            fps=30,  # Standard fps
            preset='medium',  # Good balance of speed and compression
            bitrate='5000k',  # Quality setting - adjust as needed
            threads=4,  # Parallel processing
            ffmpeg_params=["-pix_fmt", "yuv420p"],  # Ensures broad compatibility
            logger=None  # Suppress MoviePy progress bars for cleaner logs
        )
        
        print(f"  ✅ Successfully wrote final video: {final_video_output_path}")
        
        # Clean up resources - close all clips
        print(f"  🧹 Cleaning up {len(clips)} clips...")
        final_clip.close()
        for clip in clips:
            try:
                clip.close()
            except:
                pass  # Some clips might already be closed
        
        print(f"✅ Video assembly complete: {final_video_output_path}")
        return final_video_output_path
        
    except Exception as e:
        print(f"❌ Error assembling visual segments: {e}")
        import traceback
        traceback.print_exc()
        
        # Clean up any clips that were created before the error
        try:
            if 'clips' in locals():
                for clip in clips:
                    try:
                        clip.close()
                    except:
                        pass
            if 'final_clip' in locals():
                try:
                    final_clip.close()
                except:
                    pass
        except:
            pass
        
        return None

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
        "Pillow",
        "matplotlib",
        "moviepy",
        "scipy",
        "sympy",
        "seaborn"
    ],
    system_packages=["ffmpeg"],
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
        segment_data_list = _create_visual_segments(visual_plan, temp_dir)
        
        # Step 3: Assemble visual segments
        final_video_path = _assemble_visual_segments(segment_data_list, temp_dir)
        
        # Step 4: Return result
        if final_video_path:
            print(f"\n✅ Visual generation complete. Final video created: {final_video_path}")
            return sieve.File(path=final_video_path)
        else:
            print("\n⚠️  No segments were created successfully.")
            video_path = _create_placeholder_video(temp_dir, "failed_segments.mp4", 3.0, (0, 0, 255))  # Red
            return sieve.File(path=video_path)
            
    except Exception as e:
        print(f"❌ Error in visual generation: {e}")
        video_path = _create_placeholder_video(temp_dir, "error.mp4", 3.0, (0, 0, 255))  # Red
        return sieve.File(path=video_path)