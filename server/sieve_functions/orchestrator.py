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
    
    def __init__(self, persona_data: Dict, base_video_file: sieve.File):
        """
        Initialize the orchestrator with persona data and base video file.
        
        Args:
            persona_data: Dictionary containing persona information
            base_video_file: sieve.File object for the base video
        """
        self.persona_data = persona_data
        self.base_video_file = base_video_file
        
        # Get Sieve functions
        self.script_generator = sieve.function.get("sieve-internal/spew_script_generator")
        self.speech_synthesizer = sieve.function.get("sieve-internal/spew_speech_synthesizer")
        self.visuals_generator = sieve.function.get("sieve-internal/spew_visuals_generator")
        self.lipsync_processor = sieve.function.get("sieve-internal/spew_lipsync_processor")
        self.video_assembler = sieve.function.get("sieve-internal/spew_video_assembler")
        
    def generate_video(self, query: str) -> sieve.File:
        """
        Generate a complete educational video using the specified persona and query.
        
        Args:
            query: Educational topic/question to explain
            
        Returns:
            sieve.File: The final assembled video file
        """
        persona = self.persona_data
        print(f"🚀 Starting video generation for persona '{persona['name']}' with query: '{query}'")
        
        # Step 1: Generate script
        print("\n📝 Step 1: Generating script...")
        script_result = self._generate_script(
            query=query,
            name=persona["name"],
            style=persona["style_prompt"]
        )

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
            persona_id=persona["id"],
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
        # Use the base video file that was passed in during initialization
        return self.lipsync_processor.push(
            persona_id=persona_id,
            generated_audio=audio_file,
            base_video_file=self.base_video_file
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


@sieve.function(
    name="spew_complete_video_generator",
)
def create_video(persona_data: dict, base_video_file: sieve.File, query: str) -> sieve.File:
    """
    Convenience function to generate a video with the specified persona and query.
    
    Args:
        persona_data: Dictionary containing persona information (name, style_prompt, tts_voice_link, etc.)
        base_video_file: sieve.File object for the base video to use for lipsync
        query: Educational topic/question to explain
        
    Returns:
        sieve.File: The final assembled video file
    """
    orchestrator = SpewOrchestrator(persona_data, base_video_file)
    return orchestrator.generate_video(query)