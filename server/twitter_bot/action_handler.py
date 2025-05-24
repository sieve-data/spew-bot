import logging
import os
import sys
from typing import Optional

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import our modules - since we're in twitter_bot directory, import directly
import twitter_client
import request_parser
from sieve_functions.orchestrator import SpewOrchestrator

# Configure logging
logger = logging.getLogger(__name__)

# Global orchestrator instance (initialized by bot_core)
orchestrator: Optional[SpewOrchestrator] = None
personas_data: Optional[dict] = None

def init_action_handler(personas_file_path: str = None):
    """
    Initialize the action handler with Sieve orchestrator and personas data.
    This should be called once by bot_core.py during startup.
    """
    global orchestrator, personas_data
    
    try:
        # Initialize SpewOrchestrator
        orchestrator = SpewOrchestrator(personas_file_path)
        personas_data = orchestrator.personas  # Access loaded personas
        
        persona_names = [p.get('name', 'Unknown') for p in personas_data.values()]
        logger.info(f"Action handler initialized with {len(personas_data)} personas: {persona_names}")
        
    except Exception as e:
        logger.error(f"Failed to initialize action handler: {e}")
        raise

def handle_mention(tweet):
    """
    Main entry point for processing Twitter mentions.
    Called by twitter_client.listen_for_mentions() for each new mention.
    
    Args:
        tweet: Tweepy Tweet object from Twitter API v2
    """
    if not orchestrator or not personas_data:
        logger.error("Action handler not initialized. Cannot process mention.")
        return
    
    tweet_id = str(tweet.id)
    tweet_text = tweet.text
    author_id = str(tweet.author_id)
    
    logger.info(f"Processing mention: Tweet ID {tweet_id}, Author {author_id}, Text: '{tweet_text}'")
    
    try:
        # Parse the tweet to extract topic and persona
        topic, persona_id, error_message = request_parser.parse_tweet(tweet_text, {"personas": list(personas_data.values())})
        
        if error_message:
            logger.warning(f"Tweet parsing error for {tweet_id}: {error_message}")
            handle_request_error(tweet_id, error_message)
            return
            
        if not topic or not persona_id:
            logger.warning(f"Tweet parsing incomplete for {tweet_id}: topic='{topic}', persona_id='{persona_id}'")
            handle_request_error(tweet_id, "I couldn't identify both a topic and celebrity from your request.")
            return
        
        # Validate persona exists
        if persona_id not in personas_data:
            available_personas = [p.get('name', 'Unknown') for p in personas_data.values()]
            error_msg = f"I don't know how to impersonate that celebrity. Available: {', '.join(available_personas[:5])}"
            handle_request_error(tweet_id, error_msg)
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
    Generate a video for a valid request and post it to Twitter.
    
    Args:
        tweet_id: Original tweet ID to reply to
        author_id: ID of the user who made the request  
        topic: Topic to explain
        persona_id: ID of the persona to use
        persona_name: Display name of the persona
    """
    try:
        # Step 1: Post immediate acknowledgment
        ack_message = f"Working on your video about '{topic}' by {persona_name}! This will take a couple minutes... 🎬"
        logger.info(f"Posting acknowledgment for Tweet {tweet_id}: {ack_message}")
        
        ack_response = twitter_client.post_reply(tweet_id, ack_message)
        if not ack_response:
            logger.warning(f"Failed to post acknowledgment for Tweet {tweet_id}, but continuing with video generation")
        
        # Step 2: Generate video using Sieve orchestrator  
        logger.info(f"Starting video generation for Tweet {tweet_id}: topic='{topic}', persona='{persona_name}'")
        
        try:
            sieve_video_file = orchestrator.generate_video(persona_id, topic)
            logger.info(f"Video generation completed for Tweet {tweet_id}. Sieve file: {sieve_video_file}")
            
        except Exception as e:
            logger.error(f"Video generation failed for Tweet {tweet_id}: {e}", exc_info=True)
            error_msg = f"Sorry, I encountered an error generating the video about '{topic}'. Please try again later."
            twitter_client.post_reply(tweet_id, error_msg)
            return
        
        # Step 3: Convert sieve.File to local path and upload to Twitter
        try:
            local_video_path = sieve_video_file.path
            logger.info(f"Got local video path for Tweet {tweet_id}: {local_video_path}")
            
            if not os.path.exists(local_video_path):
                logger.error(f"Video file not found at {local_video_path} for Tweet {tweet_id}")
                error_msg = f"Sorry, the generated video file wasn't found. Please try again."
                twitter_client.post_reply(tweet_id, error_msg)
                return
            
            # Upload video to Twitter
            logger.info(f"Uploading video to Twitter for Tweet {tweet_id}")
            media_id = twitter_client.upload_video(local_video_path)
            
            if not media_id:
                logger.error(f"Failed to upload video to Twitter for Tweet {tweet_id}")
                error_msg = f"Sorry, I couldn't upload the video to Twitter. Please try again later."
                twitter_client.post_reply(tweet_id, error_msg)
                return
                
        except Exception as e:
            logger.error(f"Video upload failed for Tweet {tweet_id}: {e}", exc_info=True)
            error_msg = f"Sorry, I couldn't upload the video to Twitter. Please try again later."
            twitter_client.post_reply(tweet_id, error_msg)
            return
        
        # Step 4: Post final reply with video
        final_message = f"Here's {persona_name} explaining '{topic}'! 🎥✨"
        logger.info(f"Posting final video reply for Tweet {tweet_id}: {final_message}")
        
        final_response = twitter_client.post_reply(tweet_id, final_message, media_id)
        if final_response:
            logger.info(f"Successfully posted video reply for Tweet {tweet_id}. Reply ID: {final_response.data.get('id')}")
        else:
            logger.error(f"Failed to post final video reply for Tweet {tweet_id}")
            # At this point, video is generated and uploaded, but reply failed
            # Consider if we should try to post without video or just log the error
            
    except Exception as e:
        logger.error(f"Unexpected error in process_video_request for Tweet {tweet_id}: {e}", exc_info=True)
        error_msg = "Sorry, I encountered an unexpected error while processing your request."
        twitter_client.post_reply(tweet_id, error_msg)

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
            logger.error(f"Failed to post error reply for Tweet {tweet_id}")
            
    except Exception as e:
        logger.error(f"Failed to post error reply for Tweet {tweet_id}: {e}", exc_info=True)

def get_available_personas() -> list:
    """
    Get list of available persona names for error messages.
    
    Returns:
        List of persona names
    """
    if not personas_data:
        return []
    return [p.get('name', 'Unknown') for p in personas_data.values()]
