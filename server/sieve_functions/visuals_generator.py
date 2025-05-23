import sieve
import os
import json
import tempfile
import shutil
import subprocess
from typing import Dict, List, Optional, Tuple
from pathlib import Path

# Import the utility function
from utils.llm import call_llm
from moviepy import VideoFileClip, concatenate_videoclips, ImageClip
from PIL import Image
import numpy as np
import cv2
import requests

@sieve.function(
    name="spew_visuals_generator",
    python_packages=[
        "openai", # Keep for DALL-E if used separately, or if other OpenAI models are used.
        "anthropic",
        "python-dotenv",
        "moviepy",
        "Pillow",
        "numpy",
        "opencv-python",
        "matplotlib",
        "manim",
        "requests"
    ],
    system_packages=[
        "ffmpeg",
        "texlive-latex-base",
        "texlive-latex-extra",
        "texlive-fonts-recommended",
        "texlive-science",
        "dvipng"
    ],
    run_commands=[
        "python -m manim cfg write --level WARNING",
    ],
    environment_variables=[
        sieve.Env(name="OPENAI_API_KEY"),
        sieve.Env(name="ANTHROPIC_API_KEY")
    ]
)
def generate_visuals(transcription: dict) -> sieve.File:
    """
    Generate animated and static visuals based on the transcription
    
    Args:
        transcription: Dictionary containing the transcription data from speech synthesis
        
    Returns:
        sieve.File: The final assembled video with all visuals
    """
    print("🎨 Starting visuals generation...")
    
    # Create temporary directory for all visual outputs
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Step 1: Create visual plan
        print("\n📋 Step 1: Creating visual plan...")
        visual_plan = _create_visual_plan(transcription)
        print(f"✅ Created plan with {len(visual_plan['segments'])} segments")
        
        # Step 2: Generate visuals for each segment
        print("\n🎬 Step 2: Generating visual segments...")
        visual_segments = []
        
        for i, segment in enumerate(visual_plan['segments']):
            print(f"\n  Processing segment {i+1}/{len(visual_plan['segments'])}...")
            
            if segment['type'] == 'animation':
                # Generate Manim animation
                video_path = _create_animation(
                    segment=segment,
                    output_dir=temp_dir,
                    segment_index=i
                )
            else:  # static image
                # Generate DALL-E image and convert to video
                video_path = _create_static_image(
                    segment=segment,
                    output_dir=temp_dir,
                    segment_index=i
                )
            
            if video_path and os.path.exists(video_path):
                visual_segments.append(video_path)
                print(f"    ✅ Generated {segment['type']} segment")
            else:
                print(f"    ⚠️  Failed to generate {segment['type']} segment")
        
        # Step 3: Assemble all visual segments
        print("\n🎞️  Step 3: Assembling final video...")
        final_video_path = _assemble_visuals(
            visual_segments=visual_segments,
            output_dir=temp_dir,
            transcription=transcription
        )
        
        # Create and return Sieve File
        print("\n📦 Creating Sieve file...")
        return sieve.File(path=final_video_path)
        
    finally:
        # Cleanup temporary directory
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print("🧹 Cleaned up temporary files")


def _create_visual_plan(transcription: dict) -> dict:
    """
    Create a plan for what visuals to generate based on the transcription
    """
    print("  🤖 Calling LLM to create visual plan...")
    # TODO: Implement LLM call to analyze transcription and create visual plan
    # Example usage with call_llm:
    # prompt = f"Analyze the following transcription and create a visual plan: {json.dumps(transcription)}"
    # plan_str = call_llm(provider="gpt", prompt=prompt)
    # visual_plan = json.loads(plan_str)
    
    # For now, return a mock plan for testing
    mock_plan = {
        "segments": [
            {
                "type": "animation",
                "start_time": 0,
                "duration": 5,
                "description": "Animated introduction showing the concept",
                "manim_instructions": "Create a simple text animation"
            },
            {
                "type": "static",
                "start_time": 5,
                "duration": 3,
                "description": "Diagram showing the main components",
                "dalle_prompt": "Technical diagram in minimalist style"
            }
        ]
    }
    return mock_plan


def _create_animation(segment: dict, output_dir: str, segment_index: int) -> Optional[str]:
    """
    Generate a Manim animation based on the segment description
    """
    print(f"    🎭 Generating Manim animation...")
    
    try:
        # Generate Manim code using LLM
        manim_code = _generate_manim_code(segment)
        
        # Write Manim code to temporary file
        script_path = os.path.join(output_dir, f"scene_{segment_index}.py")
        with open(script_path, 'w') as f:
            f.write(manim_code)
        
        # Execute Manim
        output_path = _execute_manim(script_path, output_dir, segment_index)
        
        return output_path
        
    except Exception as e:
        print(f"    ❌ Error creating animation: {str(e)}")
        return None


def _generate_manim_code(segment: dict) -> str:
    """Generate Manim code using LLM based on segment requirements"""
    print("  🤖 Calling LLM to generate Manim code...")
    # TODO: Implement LLM call to generate Manim code
    # Example usage with call_llm:
    # manim_prompt = f"Generate Manim code for the following segment: {segment['description']}. Instructions: {segment.get('manim_instructions', '')}"
    # manim_code = call_llm(provider="gpt", prompt=manim_prompt)
    # return manim_code
    
    # For testing, return a simple Manim scene
    return """
from manim import *

class TestScene(Scene):
    def construct(self):
        text = Text("Test Animation", font_size=48)
        self.play(Write(text))
        self.wait(2)
        self.play(FadeOut(text))
"""


def _execute_manim(script_path: str, output_dir: str, segment_index: int) -> Optional[str]:
    """Execute Manim script and return path to output video"""
    try:
        # Prepare Manim command
        output_file = os.path.join(output_dir, f"animation_{segment_index}.mp4")
        
        # Run Manim
        cmd = [
            "manim",
            "-ql",  # Low quality for faster rendering during testing
            "-o", f"animation_{segment_index}.mp4",
            "--media_dir", output_dir,
            script_path,
            "TestScene"  # Scene class name
        ]
        
        print(f"    📹 Running Manim: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"    ❌ Manim error: {result.stderr}")
            return None
        
        # Find the output file (Manim creates it in a subdirectory structure)
        # This is a simplified version - may need adjustment based on Manim version
        possible_paths = [
            output_file,
            os.path.join(output_dir, "videos", "scene_*", "480p15", f"animation_{segment_index}.mp4"),
            os.path.join(output_dir, "videos", f"animation_{segment_index}.mp4")
        ]
        
        for path in possible_paths:
            if "*" in path:
                # Handle glob patterns
                from glob import glob
                matches = glob(path)
                if matches:
                    return matches[0]
            elif os.path.exists(path):
                return path
                
        print(f"    ⚠️  Could not find Manim output file")
        return None
        
    except Exception as e:
        print(f"    ❌ Error executing Manim: {str(e)}")
        return None


def _create_static_image(segment: dict, output_dir: str, segment_index: int) -> Optional[str]:
    """
    Generate a static image using DALL-E and convert to video
    """
    print(f"    🖼️  Generating static image...")
    
    try:
        # TODO: Implement DALL-E image generation
        # Note: call_llm currently supports text-based LLMs. For DALL-E (image generation),
        # you would typically use a different OpenAI API endpoint or extend call_llm.
        # For example, if using OpenAI's image generation:
        # from openai import OpenAI
        # client = OpenAI() # Ensure OPENAI_API_KEY is set
        # response = client.images.generate(
        #    model="dall-e-3",
        #    prompt=segment.get('dalle_prompt', 'A beautiful abstract image'),
        #    n=1,
        #    size="1024x1024"
        # )
        # image_url = response.data[0].url
        # # Then download the image from image_url and save it.

        # For now, create a simple test image using PIL
        img = Image.new('RGB', (1920, 1080), color='navy')
        image_path = os.path.join(output_dir, f"image_{segment_index}.png")
        img.save(image_path)
        
        # Convert image to video using MoviePy
        video_path = os.path.join(output_dir, f"static_{segment_index}.mp4")
        clip = ImageClip(image_path, duration=segment.get('duration', 3))
        clip.write_videofile(video_path, fps=24, verbose=False, logger=None)
        
        return video_path
        
    except Exception as e:
        print(f"    ❌ Error creating static image: {str(e)}")
        return None


def _assemble_visuals(visual_segments: List[str], output_dir: str, transcription: dict) -> str:
    """
    Assemble all visual segments into a final video using MoviePy
    """
    print("  🎬 Loading video segments...")
    
    # Load all video clips
    clips = []
    for segment_path in visual_segments:
        try:
            clip = VideoFileClip(segment_path)
            clips.append(clip)
            print(f"    ✅ Loaded: {os.path.basename(segment_path)}")
        except Exception as e:
            print(f"    ❌ Failed to load {segment_path}: {str(e)}")
    
    if not clips:
        raise ValueError("No video segments were successfully loaded")
    
    # Concatenate all clips
    print("  🔗 Concatenating clips...")
    final_video = concatenate_videoclips(clips, method="compose")
    
    # Write final video
    final_path = os.path.join(output_dir, "final_visuals.mp4")
    print("  💾 Writing final video...")
    final_video.write_videofile(
        final_path,
        fps=24,
        codec='libx264',
        audio_codec='aac',
        verbose=False,
        logger=None
    )
    
    # Clean up MoviePy resources
    final_video.close()
    for clip in clips:
        clip.close()
    
    print(f"  ✅ Final video saved: {final_path}")
    return final_path
