import sieve
import os

@sieve.function(
    name="spew_lipsync_processor",
    python_packages=[]
)
def process_lipsync(persona_id: str, generated_audio: sieve.File, base_video_file: sieve.File):
    """
    Create a lip-synced video by combining a persona's base video with generated audio
    
    Args:
        persona_id: ID of the persona to use (for logging/reference)
        generated_audio: Audio file to sync with (from speech synthesizer)
        base_video_file: Sieve.File object of the base video file
        
    Returns:
        sieve.File: The lip-synced video file
    """
    # Validate inputs
    if not base_video_file:
        raise ValueError(f"No base_video_file provided for persona {persona_id}")
    
    # The base_video_file is already a sieve.File object, no need to create it again.
    
    # Get the lipsync function and process
    return _create_lipsynced_video(base_video_file, generated_audio)


def _create_lipsynced_video(base_video_file: sieve.File, audio_file: sieve.File) -> sieve.File:
    """Create lip-synced video using Sieve's lipsync function"""
    # Get the lipsync function
    lipsync_function = sieve.function.get("sieve/lipsync")
    
    # Call the lipsync function with recommended settings
    result_file = lipsync_function.run(
        file=base_video_file,
        audio=audio_file,
        backend="sievesync-1.1",
        enable_multispeaker=False,
        enhance="default",
        downsample=False,
        cut_by="audio"
    )
    
    return result_file
