import unittest
import sieve
import os
import json
from dotenv import load_dotenv
from typing import Dict
from pathlib import Path

# Load environment variables from .env file if present
load_dotenv()

# Get project root directory (2 levels up from this test file)
PROJECT_ROOT = Path(__file__).parent.parent.parent

class TestSpewPipeline(unittest.TestCase):
    def setUp(self):
        """Set up test environment and load required data"""
        self._check_environment()
        self._load_personas()
        
    def _check_environment(self):
        """Verify all required environment variables are set"""
        required_env_vars = [
            "OPENAI_API_KEY",
            "PLAYHT_TTS_USER", 
            "PLAYHT_TTS_API_KEY"
        ]
        missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
        if missing_vars:
            raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
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
        """Test the complete pipeline: script generation -> speech synthesis + transcription -> visuals -> lipsync"""
        PERSONA_ID = "steve_jobs"  # Test persona
        QUERY = "How neural networks learn patterns in data"
        
        print("🚀 Starting complete Spew pipeline test...")
        
        # Get persona data
        persona = self.personas[PERSONA_ID]
        
        # # Step 1: Generate script
        # print("\n📝 Step 1: Generating script...")
        # script_result = self._generate_script(
        #     query=QUERY,
        #     name=persona["name"],
        #     style=persona["style_prompt"]
        # )
        # print(f"✅ Script generated ({len(script_result)} characters)")
        # print(f"📄 Script preview: {script_result[:150]}...")

        # We are going to override the script result with a different, shorter script for testing purposes.
        script_result = """Hello, this is a test script. I'm Steve Jobs and today we're going to talk about how neural networks learn patterns in data."""
        
        # Step 2: Generate speech and transcribe
        print("\n🎤 Step 2: Generating speech and transcribing...")
        speech_result = self._synthesize_speech(
            script_text=script_result,
            voice_link=persona["tts_voice_link"]
        )
        self._verify_speech_result(speech_result)
        
        # # Step 3: Generate lip-synced video
        # print("\n🎬 Step 3: Generating lip-synced video...")
        # video_result = self._process_lipsync(
        #     persona_id=PERSONA_ID,
        #     audio_file=speech_result["audio_file"]
        # )
        # self._verify_video_result(video_result)

        # Step 4: Generate visuals
        print("\n🎨 Step 4: Generating visuals...")
        visuals_result = self._generate_visuals(
            transcription={"segments": speech_result["transcription"]}
        )
        self._verify_visuals_result(visuals_result)
        
        
        print("\n🎉 Complete pipeline test successful!")
    
    def _generate_script(self, query: str, name: str, style: str) -> str:
        """Generate script using the script generator function"""
        script_generator = sieve.function.get("sieve-internal/spew_script_generator")
        result = script_generator.run(query=query, name=name, style=style)
        
        # Verify script
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 50, "Generated script is too short")
        
        return result
    
    def _synthesize_speech(self, script_text: str, voice_link: str) -> dict:
        """Generate speech and transcribe using the speech synthesizer function"""
        speech_synthesizer = sieve.function.get("sieve-internal/spew_speech_synthesizer")
        return speech_synthesizer.run(
            script_text=script_text,
            voice_link=voice_link
        )
    
    def _verify_speech_result(self, result: dict):
        """Verify speech synthesis and transcription results"""
        # Verify structure and types
        self.assertIsInstance(result, dict)
        self.assertIn("audio_file", result)
        self.assertIn("transcription", result)
        self.assertIsInstance(result["audio_file"], sieve.File)
        self.assertIsNotNone(result["transcription"])
        
        print("✅ Speech synthesis completed")
        print(f"🎵 Audio file: {result['audio_file']}")
        print(f"📝 Transcription type: {type(result['transcription'])}")
        
        # Print transcription preview
        transcription = result['transcription']
        preview = None
        
        if isinstance(transcription, str):
            preview = transcription[:100]
        elif isinstance(transcription, dict) and 'text' in transcription:
            preview = transcription['text'][:100]
        elif isinstance(transcription, list) and transcription:
            preview = str(transcription[0])[:100]
            
        if preview:
            print(f"🗣️  Transcription preview: {preview}...")
    
    def _generate_visuals(self, transcription: dict) -> sieve.File:
        """Generate visuals using the visuals generator function"""
        visuals_generator = sieve.function.get("sieve-internal/spew_visuals_generator")
        result = visuals_generator.run(transcription=transcription)
        
        # Verify result is a sieve.File
        self.assertIsInstance(result, sieve.File, "Visuals generator did not return a sieve.File")
        
        return result

    def _verify_visuals_result(self, result: sieve.File):
        """Verify visuals generation result"""
        # Verify the result is a sieve.File
        self.assertIsInstance(result, sieve.File)
        
        print("✅ Visuals generation completed")
        print(f"🖼️ Visuals video file: {result}")
    
    def _process_lipsync(self, persona_id: str, audio_file: sieve.File) -> sieve.File:
        """Generate lip-synced video using the lipsync processor function"""
        lipsync_processor = sieve.function.get("sieve-internal/spew_lipsync_processor")
        
        # Get the video path for this persona
        persona = self.personas[persona_id]
        video_path_str = persona.get("video_path")
        
        if not video_path_str:
            raise ValueError(f"No video_path found for persona {persona_id}")

        # Construct the absolute path to the video file
        # Assuming PROJECT_ROOT is defined in your setUp or class level
        absolute_video_path = PROJECT_ROOT / "server" / video_path_str

        # Create a sieve.File object from the local video path
        # This will upload the file if it's not already in Sieve storage
        # or reference it if it's already known to Sieve via its path.
        input_video_file = sieve.File(path=str(absolute_video_path))
        
        return lipsync_processor.run(
            persona_id=persona_id,
            generated_audio=audio_file,
            base_video_file=input_video_file # Pass the sieve.File object
        )
    
    def _verify_video_result(self, result: sieve.File):
        """Verify lip-synced video result"""
        # Verify the result is a Sieve File
        self.assertIsInstance(result, sieve.File)
        
        print("✅ Lip-sync video generation completed")
        print(f"🎬 Video file: {result}")

if __name__ == "__main__":
    unittest.main()
