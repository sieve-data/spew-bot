import logging
import os
import sys
import time
import json
from typing import Optional
from pathlib import Path
import sieve

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import our modules - since we're in twitter_bot directory, import directly
import twitter_client
import request_parser

# Configure logging
logger = logging.getLogger(__name__)

# Global variables for job tracking and personas data
pending_jobs: dict = {}  # tweet_id -> job_data
personas_data: Optional[dict] = None
create_video_function = None

# Job timeout settings
MAX_JOB_TIME_SECONDS = 1800  # 30 minutes timeout

def init_action_handler(personas_file_path: str = None):
    """
    Initialize the action handler with Sieve functions and personas data.
    This should be called once by bot_core.py during startup.
    """
    global personas_data, create_video_function
    
    try:
        # Load personas data directly
        personas_data = _load_personas_data(personas_file_path)
        
        # Get the Sieve function for video generation
        create_video_function = sieve.function.get("sieve-internal/spew_complete_video_generator")
        
        persona_names = [p.get('name', 'Unknown') for p in personas_data.values()]
        logger.info(f"Action handler initialized with {len(personas_data)} personas: {persona_names}")
        
    except Exception as e:
        logger.error(f"Failed to initialize action handler: {e}")
        raise

def _load_personas_data(personas_file_path: str = None) -> dict:
    """Load personas data from JSON file and index by persona ID."""
    if personas_file_path:
        file_path = personas_file_path
    else:
        # Default path relative to this file
        current_dir = os.path.dirname(__file__)
        file_path = os.path.join(current_dir, '..', 'data', 'personas.json')
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Index personas by ID for efficient lookup
        personas_dict = {}
        for persona in data.get('personas', []):
            persona_id = persona.get('id')
            if persona_id:
                personas_dict[persona_id] = persona
        
        logger.info(f"Loaded {len(personas_dict)} personas from {file_path}")
        return personas_dict
        
    except Exception as e:
        logger.error(f"Failed to load personas from {file_path}: {e}")
        raise

def _create_celebrity_list_error_message() -> str:
    """Create a standardized error message for unsupported celebrities."""
    return (
        f"Sorry, I don't recognize that celebrity. Please check the spelling and try again.\n\n"
        f"Format: @celebxplain explain [topic] by [celebrity]"
    )

def handle_mention(tweet):
    """
    Main entry point for processing Twitter mentions.
    Called by twitter_client.listen_for_mentions() for each new mention.
    
    Args:
        tweet: Tweepy Tweet object from Twitter API v2
    """
    if not personas_data:
        logger.error("Action handler not initialized. Cannot process mention.")
        return
    
    tweet_id = str(tweet.id)
    tweet_text = tweet.text
    author_id = str(tweet.author_id)
    
    logger.info(f"Processing mention: Tweet ID {tweet_id}, Author {author_id}, Text: '{tweet_text}'")
    
    try:
        # Parse the tweet to extract topic and persona
        topic, persona_id, error_message = request_parser.parse_tweet(tweet_text, {"personas": list(personas_data.values())})
        
        # If parsing failed or no celebrity was identified, show celebrity list
        if error_message or not persona_id:
            logger.warning(f"Tweet parsing error or no celebrity identified for {tweet_id}: error='{error_message}', persona_id='{persona_id}'")
            celebrity_list_error = _create_celebrity_list_error_message()
            handle_request_error(tweet_id, celebrity_list_error)
            return
            
        if not topic:
            logger.warning(f"No topic identified for {tweet_id}: topic='{topic}'")
            handle_request_error(tweet_id, "I couldn't identify a topic from your request. Please mention me with: explain [topic] by [celebrity name]")
            return
        
        # Validate persona exists in our supported list
        if persona_id not in personas_data:
            logger.warning(f"Unsupported persona for {tweet_id}: persona_id='{persona_id}'")
            celebrity_list_error = _create_celebrity_list_error_message()
            handle_request_error(tweet_id, celebrity_list_error)
            return
        
        # Process the valid video request
        persona_name = personas_data[persona_id].get('name', 'the selected celebrity')
        logger.info(f"Valid request for Tweet {tweet_id}: Topic='{topic}', Persona='{persona_name}' ({persona_id})")
        
        process_video_request(tweet_id, author_id, topic, persona_id, persona_name)
        
    except Exception as e:
        logger.error(f"Unexpected error processing mention {tweet_id}: {e}", exc_info=True)
        handle_request_error(tweet_id, "Sorry, I encountered an unexpected error. Please try again later.")

def process_video_request(tweet_id: str, author_id: str, topic: str, persona_id: str, persona_name: str):
    """
    Start async video generation for a valid request.
    
    Args:
        tweet_id: Original tweet ID to reply to
        author_id: ID of the user who made the request  
        topic: Topic to explain
        persona_id: ID of the persona to use
        persona_name: Display name of the persona
    """
    try:
        # Start async video generation using Sieve
        logger.info(f"Starting async video generation for Tweet {tweet_id}: topic='{topic}', persona='{persona_name}'")
        
        try:
            # Get persona data and base video file
            persona_data = personas_data[persona_id]
            base_video_path = Path(__file__).parent.parent / persona_data['video_path']
            base_video_file = sieve.File(path=str(base_video_path))
            
            # Push video generation job to Sieve (non-blocking)
            video_future = create_video_function.push(
                persona_data=persona_data,
                base_video_file=base_video_file,
                query=topic
            )
            
            # Store job info for tracking
            pending_jobs[tweet_id] = {
                'future': video_future,
                'tweet_id': tweet_id,
                'topic': topic,
                'persona_name': persona_name,
                'start_time': time.time(),
                'author_id': author_id
            }
            
            logger.info(f"Successfully queued video generation job for Tweet {tweet_id}")
            
        except Exception as e:
            logger.error(f"Failed to start video generation for Tweet {tweet_id}: {e}", exc_info=True)
            error_msg = f"Sorry, I encountered an error starting the video generation about '{topic}'. Please try again later."
            response = twitter_client.post_reply(tweet_id, error_msg)
            if not response:
                logger.error(f"❌ Also failed to post error message to Twitter for Tweet {tweet_id}")
            return
            
    except Exception as e:
        logger.error(f"Unexpected error in process_video_request for Tweet {tweet_id}: {e}", exc_info=True)
        error_msg = "Sorry, I encountered an unexpected error while processing your request."
        response = twitter_client.post_reply(tweet_id, error_msg)
        if not response:
            logger.error(f"❌ Also failed to post error message to Twitter for Tweet {tweet_id}")

def check_completed_jobs():
    """Check for completed video generation jobs and post results."""
    logger.info(f"📊 Currently tracking {len(pending_jobs)} pending video jobs")
    
    if not pending_jobs:
        logger.info("📝 No pending jobs to check")
        return
    
    completed_jobs = []
    current_time = time.time()
    
    for tweet_id, job_data in pending_jobs.items():
        future = job_data['future']
        start_time = job_data['start_time']
        elapsed_time = current_time - start_time
        
        logger.info(f"🔍 Job {tweet_id}: {elapsed_time:.1f}s elapsed, done={future.done()}")
        
        # Check for timeout
        if current_time - start_time > MAX_JOB_TIME_SECONDS:
            completed_jobs.append(tweet_id)
            logger.warning(f"Job for Tweet {tweet_id} timed out after {MAX_JOB_TIME_SECONDS} seconds - staying silent")
            continue
        
        # Check if job is done
        if future.done():
            completed_jobs.append(tweet_id)
            
            try:
                # Get the result
                video_file = future.result()
                logger.info(f"🎉 Video generation completed for Tweet {tweet_id}")
                _post_completed_video(tweet_id, video_file, job_data)
                
            except Exception as e:
                logger.error(f"Video generation failed for Tweet {tweet_id}: {e} - staying silent", exc_info=True)
    
    # Clean up completed jobs
    for tweet_id in completed_jobs:
        del pending_jobs[tweet_id]
    
    if completed_jobs:
        logger.info(f"✅ Processed {len(completed_jobs)} completed jobs. {len(pending_jobs)} jobs still pending.")
    else:
        logger.info(f"⏳ No completed jobs found. {len(pending_jobs)} jobs still pending.")

def _post_completed_video(tweet_id: str, video_file: sieve.File, job_data: dict):
    """Upload video and post final reply."""
    topic = job_data['topic']
    persona_name = job_data['persona_name']
    
    try:
        # Download video file locally using .path
        local_video_path = video_file.path
        logger.info(f"Downloaded video for Tweet {tweet_id} to: {local_video_path}")
        
        if not os.path.exists(local_video_path):
            logger.error(f"Video file not found at {local_video_path} for Tweet {tweet_id} - staying silent")
            return
        
        # Upload video to Twitter
        logger.info(f"Uploading video to Twitter for Tweet {tweet_id}")
        media_id = twitter_client.upload_video(local_video_path)
        
        if not media_id:
            logger.error(f"Failed to upload video to Twitter for Tweet {tweet_id} - staying silent")
            return
        
        # Post final reply with video
        final_message = f"Here's {persona_name} explaining '{topic}'! 🎥✨"
        logger.info(f"Posting final video reply for Tweet {tweet_id}: {final_message}")
        
        final_response = twitter_client.post_reply(tweet_id, final_message, media_id)
        if final_response:
            logger.info(f"Successfully posted video reply for Tweet {tweet_id}")
        else:
            logger.error(f"❌ Failed to post final video reply for Tweet {tweet_id}")
            
    except Exception as e:
        logger.error(f"Error posting completed video for Tweet {tweet_id}: {e} - staying silent", exc_info=True)

def handle_request_error(tweet_id: str, error_message: str):
    """
    Post a user-friendly error message in reply to a tweet.
    
    Args:
        tweet_id: Tweet ID to reply to
        error_message: Error message to post
    """
    try:
        # Make error message more helpful
        if "couldn't identify" in error_message.lower() or "couldn't understand" in error_message.lower():
            helpful_msg = f"{error_message} Try format: @YourBotHandle explain [topic] by [celebrity name]"
        else:
            helpful_msg = error_message
            
        logger.info(f"Posting error reply for Tweet {tweet_id}: {helpful_msg}")
        response = twitter_client.post_reply(tweet_id, helpful_msg)
        
        if response:
            logger.info(f"Successfully posted error reply for Tweet {tweet_id}")
        else:
            logger.error(f"❌ Twitter API returned None when posting reply for Tweet {tweet_id}")
            
    except Exception as e:
        logger.error(f"❌ TWITTER API ERROR for Tweet {tweet_id}: {e}", exc_info=True)

def get_available_personas() -> list:
    """
    Get list of available persona names for error messages.
    
    Returns:
        List of persona names
    """
    if not personas_data:
        return []
    return [p.get('name', 'Unknown') for p in personas_data.values()]

def get_pending_jobs_count() -> int:
    """Get count of pending jobs for monitoring."""
    return len(pending_jobs)

def get_pending_jobs_info() -> list:
    """Get detailed info about pending jobs for monitoring."""
    current_time = time.time()
    jobs_info = []
    
    for tweet_id, job_data in pending_jobs.items():
        elapsed_time = current_time - job_data['start_time']
        jobs_info.append({
            'tweet_id': tweet_id,
            'topic': job_data['topic'],
            'persona_name': job_data['persona_name'],
            'elapsed_seconds': int(elapsed_time),
            'is_done': job_data['future'].done()
        })
    
    return jobs_info
