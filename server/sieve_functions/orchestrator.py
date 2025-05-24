import sieve
import json
import os
from pathlib import Path
from typing import Dict

class SpewOrchestrator:
    """
    Local orchestrator for the Spew video generation pipeline.
    Coordinates all Sieve functions to create educational videos.
    """
    
    def __init__(self, personas_file_path: str = None):
        """
        Initialize the orchestrator with personas data.
        
        Args:
            personas_file_path: Path to personas.json file. If None, uses default path.
        """
        if personas_file_path is None:
            # Default path relative to this file
            current_dir = Path(__file__).parent
            personas_file_path = current_dir.parent / "data" / "personas.json"
        
        self.personas = self._load_personas(personas_file_path)
        
        # Get Sieve functions
        self.script_generator = sieve.function.get("sieve-internal/spew_script_generator")
        self.speech_synthesizer = sieve.function.get("sieve-internal/spew_speech_synthesizer")
        self.visuals_generator = sieve.function.get("sieve-internal/spew_visuals_generator")
        self.lipsync_processor = sieve.function.get("sieve-internal/spew_lipsync_processor")
        self.video_assembler = sieve.function.get("sieve-internal/spew_video_assembler")
        
    def _load_personas(self, personas_path: Path) -> Dict:
        """Load and index personas data for efficient lookup"""
        try:
            with open(personas_path, 'r') as f:
                personas_data = json.load(f)
                return {
                    persona["id"]: persona 
                    for persona in personas_data["personas"]
                }
        except FileNotFoundError:
            raise FileNotFoundError(f"personas.json not found at {personas_path}")
        except json.JSONDecodeError:
            raise ValueError(f"personas.json at {personas_path} is not valid JSON")
    
    def generate_video(self, persona_id: str, query: str) -> sieve.File:
        """
        Generate a complete educational video using the specified persona and query.
        
        Args:
            persona_id: ID of the persona to use (must exist in personas.json)
            query: Educational topic/question to explain
            
        Returns:
            sieve.File: The final assembled video file
        """
        print(f"🚀 Starting video generation for persona '{persona_id}' with query: '{query}'")
        
        # Validate persona exists
        if persona_id not in self.personas:
            raise ValueError(f"Persona '{persona_id}' not found. Available personas: {list(self.personas.keys())}")
        
        persona = self.personas[persona_id]
        
        # Step 1: Generate script
        print("\n📝 Step 1: Generating script...")
        # script_result = self._generate_script(
        #     query=query,
        #     name=persona["name"],
        #     style=persona["style_prompt"]
        # )
        script_result = """
        Hey dolls! Today we're diving deep into blockchain technology, which is like, way more complex than my marriage to Kris Humphries - and that's saying something!

        So technically, a blockchain is a distributed ledger that maintains an ever-growing list of records called blocks, each cryptographically linked to the previous one using a hash function. 
        
        Each block contains three crucial elements: transaction data, a timestamp, and the cryptographic hash of the previous block, creating an immutable chain of information.

        Miners do some complex math to verify the transactions and add them to the blockchain.
        """

        print(f"✅ Script generated ({len(script_result)} characters)")
        
        # Step 2: Generate speech and transcribe
        print("\n🎤 Step 2: Generating speech and transcribing...")
        speech_result = self._synthesize_speech(
            script_text=script_result,
            voice_link=persona["tts_voice_link"]
        )
        print("✅ Speech synthesis and transcription completed")
        
        # Step 3: Parallel processing - visuals and lipsync
        print("\n⚡ Step 3: Starting parallel processing (visuals + lipsync)...")
        
        # Prepare transcription data for visuals
        transcription_data = self._prepare_transcription_for_visuals(speech_result["transcription"])
        
        # Start both processes in parallel using push()
        print("🎨 Starting visuals generation...")
        visuals_future = self.visuals_generator.push(transcription=transcription_data)
        
        print("🎬 Starting lipsync processing...")
        lipsync_future = self._process_lipsync_async(
            persona_id=persona_id,
            audio_file=speech_result["audio_file"]
        )
        
        # Wait for both parallel processes to complete
        print("⏳ Waiting for parallel processes to complete...")
        visuals_result = visuals_future.result()
        lipsync_result = lipsync_future.result()
        print("✅ Parallel processing completed")
        
        # Step 4: Assemble final video
        print("\n🎞️ Step 4: Assembling final video...")
        final_video = self._assemble_final_video(
            celebrity_video=lipsync_result,
            visuals_video=visuals_result
        )
        print("✅ Final video assembly completed")
        
        print("\n🎉 Video generation pipeline completed successfully!")
        print(f"📁 Final video: {final_video}")
        
        return final_video
    
    def _generate_script(self, query: str, name: str, style: str) -> str:
        """Generate script using the script generator function"""
        result = self.script_generator.run(query=query, name=name, style=style)
        
        if not isinstance(result, str) or len(result) < 50:
            raise ValueError("Generated script is invalid or too short")
        
        return result
    
    def _synthesize_speech(self, script_text: str, voice_link: str) -> dict:
        """Generate speech and transcribe using the speech synthesizer function"""
        result = self.speech_synthesizer.run(
            script_text=script_text,
            voice_link=voice_link
        )
        
        # Validate result structure
        if not isinstance(result, dict) or "audio_file" not in result or "transcription" not in result:
            raise ValueError("Speech synthesis returned invalid result")
        
        if not isinstance(result["audio_file"], sieve.File):
            raise ValueError("Speech synthesis did not return a valid audio file")
        
        return result
    
    def _prepare_transcription_for_visuals(self, transcription_data) -> dict:
        """Prepare transcription data in the correct format for visuals generator"""
        if isinstance(transcription_data, list):
            # If it's already a list of segments, use as is
            return {"segments": transcription_data}
        elif isinstance(transcription_data, dict) and "segments" in transcription_data:
            # If it's already in the correct format
            return transcription_data
        else:
            # If it's a simple string or other format, create a single segment
            return {
                "segments": [{
                    "text": str(transcription_data),
                    "start": 0.0,
                    "end": 10.0  # Default duration
                }]
            }
    
    def _process_lipsync_async(self, persona_id: str, audio_file: sieve.File):
        """Start lipsync processing asynchronously using push()"""
        persona = self.personas[persona_id]
        video_path_str = persona.get("video_path")
        
        if not video_path_str:
            raise ValueError(f"No video_path found for persona {persona_id}")
        
        # Construct the absolute path to the video file
        current_dir = Path(__file__).parent
        absolute_video_path = current_dir.parent / video_path_str
        
        if not absolute_video_path.exists():
            raise FileNotFoundError(f"Video file not found: {absolute_video_path}")
        
        # Create a sieve.File object from the local video path
        input_video_file = sieve.File(path=str(absolute_video_path))
        
        # Use push() for async processing
        return self.lipsync_processor.push(
            persona_id=persona_id,
            generated_audio=audio_file,
            base_video_file=input_video_file
        )
    
    def _assemble_final_video(self, celebrity_video: sieve.File, visuals_video: sieve.File) -> sieve.File:
        """Assemble the final video using the video assembler function"""
        result = self.video_assembler.run(
            celebrity_video=celebrity_video,
            visuals_video=visuals_video
        )
        
        if not isinstance(result, sieve.File):
            raise ValueError("Video assembly did not return a valid video file")
        
        return result


def create_video(persona_id: str, query: str, personas_file_path: str = None) -> sieve.File:
    """
    Convenience function to generate a video with the specified persona and query.
    
    Args:
        persona_id: ID of the persona to use
        query: Educational topic/question to explain
        personas_file_path: Optional path to personas.json file
        
    Returns:
        sieve.File: The final assembled video file
    """
    orchestrator = SpewOrchestrator(personas_file_path)
    return orchestrator.generate_video(persona_id, query)


# Example usage
if __name__ == "__main__":
    # Example: Generate a video with Kim Kardashian explaining blockchain
    try:
        final_video = create_video(
            persona_id="kim_kardashian",
            query="What is a blockchain and how does it work?"
        )
        print(f"🎬 Video generated successfully: {final_video.path}")
    except Exception as e:
        print(f"❌ Error generating video: {e}")
