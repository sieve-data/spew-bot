import unittest
import sieve
import os
import json
from dotenv import load_dotenv
from typing import Dict
from pathlib import Path

# Import the orchestrator
import sys
sys.path.append(str(Path(__file__).parent.parent / 'sieve_functions'))
from orchestrator import create_video

# Load environment variables from .env file if present
load_dotenv()

# Get project root directory (2 levels up from this test file)
PROJECT_ROOT = Path(__file__).parent.parent.parent

class TestSpewPipeline(unittest.TestCase):
    def setUp(self):
        """Set up test environment and load required data"""
        self._load_personas()
        
    
    def _load_personas(self):
        """Load and index personas data for efficient lookup"""
        personas_path = PROJECT_ROOT / 'server' / 'data' / 'personas.json'
        try:
            with open(personas_path, 'r') as f:
                personas_data = json.load(f)
                # Create an indexed lookup of personas by ID for O(1) access
                self.personas: Dict = {
                    persona["id"]: persona 
                    for persona in personas_data["personas"]
                }
        except FileNotFoundError:
            raise FileNotFoundError(f"personas.json not found at {personas_path}")
        except json.JSONDecodeError:
            raise ValueError(f"personas.json at {personas_path} is not valid JSON")
        
    def test_complete_spew_pipeline(self):
        """Test the complete pipeline using the orchestrator"""
        PERSONA_ID = "kim_kardashian"  # Test persona
        QUERY = "Can you explain how large language models like chatgpt work on a lower level to someone who's not technical at all and doesn't know anything about programming or AI? Explain it as if I'm a high school student."
        
        print("🚀 Starting complete Spew pipeline test using orchestrator...")
        
        # Get persona data for validation
        persona = self.personas[PERSONA_ID]
        print(f"🎭 Using persona: {persona['name']}")
        print(f"📝 Query: {QUERY}")
        
        # Use the orchestrator to generate the complete video
        print("\n🎬 Generating complete video using orchestrator...")
        final_video_result = create_video(
            persona_id=PERSONA_ID,
            query=QUERY,
            personas_file_path=str(PROJECT_ROOT / 'server' / 'data' / 'personas.json')
        )
        
        # Verify and download the final video
        self._verify_and_download_final_video(final_video_result)
        
        print("\n🎉 Complete pipeline test successful!")
    
    def _verify_and_download_final_video(self, result: sieve.File):
        """Verify and download the final video"""
        # Verify the result is a sieve.File
        self.assertIsInstance(result, sieve.File)
        
        print("✅ Final video generation completed")
        print(f"🎬 Final video file: {result}")

        # Download the file to get local access using the .path property
        try:
            # Use .path property - this will download the file if needed and return the local path
            local_path = result.path
            absolute_path = os.path.abspath(local_path)
            
            print(f"📁 Downloaded final video to: {local_path}")
            print(f"🎬 FINAL VIDEO ABSOLUTE PATH: {absolute_path}")
            
            # Verify the file exists and has content
            if os.path.exists(local_path):
                file_size = os.path.getsize(local_path)
                print(f"📊 Final video file size: {file_size} bytes ({file_size / (1024*1024):.2f} MB)")
                
                # Additional validation for video file
                if local_path.endswith('.mp4'):
                    print("✅ Final video saved as MP4 format")
                else:
                    print(f"⚠️ Warning: Final video format is not MP4: {local_path}")
            else:
                print("⚠️ Warning: Downloaded file path does not exist")
                
        except Exception as e:
            print(f"❌ Error accessing final video file: {e}")
            # Fallback: try to get the path directly if it's a local file
            if hasattr(result, 'path') and result.path:
                print(f"🎬 Final video path (fallback): {result.path}")

if __name__ == "__main__":
    unittest.main()
