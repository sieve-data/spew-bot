import sieve
import requests
import os
import tempfile
import json

@sieve.function(
    name="spew_speech_synthesizer",
    python_packages=["requests"],
    environment_variables=[
        sieve.Env(name="PLAYHT_TTS_USER", is_secret=True),
        sieve.Env(name="PLAYHT_TTS_API_KEY", is_secret=True)
    ]
)
def synthesize_and_transcribe(script_text: str, voice_link: str) -> dict:
    """
    Generate speech from script using PlayHT and transcribe it using Sieve
    
    Args:
        script_text: The text to convert to speech
        voice_link: PlayHT voice link for the desired voice
        
    Returns:
        Dictionary with audio_file (sieve.File) and transcription (dict)
    """
    # Get credentials from environment
    user_id = os.environ["PLAYHT_TTS_USER"]
    api_key = os.environ["PLAYHT_TTS_API_KEY"]
    
    # Generate speech using PlayHT API
    audio_file_path = _generate_speech_audio(script_text, voice_link, user_id, api_key)
    
    try:
        # Create Sieve file object
        sieve_audio_file = sieve.File(path=audio_file_path)
        
        # Transcribe the audio using Sieve
        transcription_result = _transcribe_audio(sieve_audio_file)
        
        return {
            "audio_file": sieve_audio_file,
            "transcription": transcription_result
        }
    
    finally:
        # Clean up temporary file
        if os.path.exists(audio_file_path):
            os.remove(audio_file_path)


def _generate_speech_audio(script_text: str, voice_link: str, user_id: str, api_key: str) -> str:
    """Generate speech audio using PlayHT API and save to temporary file"""
    
    # API configuration
    url = "https://api.play.ht/api/v2/tts/stream"
    headers = {
        "X-USER-ID": user_id,
        "Authorization": api_key,
        "accept": "audio/mpeg",
        "content-type": "application/json"
    }
    payload = {
        "text": script_text,
        "voice_engine": "PlayDialog",
        "voice": voice_link,
        "output_format": "mp3"
    }
    
    # Create temporary file for audio
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
        audio_file_path = tmp_file.name
    
    # Call PlayHT API
    response = requests.post(url, headers=headers, json=payload, stream=True)
    response.raise_for_status()
    
    # Write audio data to file
    with open(audio_file_path, "wb") as audio_file:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                audio_file.write(chunk)
    
    return audio_file_path


def _transcribe_audio(sieve_audio_file: sieve.File) -> dict:
    """Transcribe audio using Sieve transcription function"""
    
    # Get the transcription function
    transcriber = sieve.function.get("sieve/transcribe")
    
    # Call transcription with recommended settings
    transcription_job = transcriber.push(
        file=sieve_audio_file,
        backend="stable-ts-whisper-large-v3-turbo",
        word_level_timestamps=False,
        source_language="auto"
    )
    
    # Get the result
    result = transcription_job.result()
    
    # Convert result to serializable format
    if hasattr(result, '__iter__') and not isinstance(result, (dict, str)):
        return list(result)
    
    return result
