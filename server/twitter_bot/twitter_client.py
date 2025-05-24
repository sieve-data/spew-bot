import os
import time
import tweepy
import logging
from typing import Optional, Tuple, Dict, Any, Callable
from dotenv import load_dotenv
import cv2
import numpy as np
import tempfile

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Global variables for since_id management
APP_DATA_BASE_DIR = os.environ.get('APP_DATA_BASE_DIR', 'data')
SINCE_ID_FILE = os.path.join(os.path.dirname(__file__), '..', APP_DATA_BASE_DIR, 'since_id.txt')
MENTIONS_POLLING_INTERVAL_SECONDS = int(os.getenv("MENTIONS_POLLING_INTERVAL_SECONDS", 30))
TWITTER_BOT_USERNAME = os.getenv("TWITTER_BOT_USERNAME")

# Global API client objects (will be set by init_client)
api_v1: Optional[tweepy.API] = None
api_v2: Optional[tweepy.Client] = None

# Global shutdown flag for graceful shutdown
_shutdown_requested = False

def request_shutdown():
    """Request shutdown of the mention listening loop."""
    global _shutdown_requested
    _shutdown_requested = True
    logger.info("Shutdown requested for mention listener")

def reset_shutdown_flag():
    """Reset the shutdown flag (used when restarting)."""
    global _shutdown_requested
    _shutdown_requested = False

def is_shutdown_requested() -> bool:
    """Check if shutdown has been requested."""
    return _shutdown_requested

def init_clients() -> Tuple[Optional[tweepy.API], Optional[tweepy.Client]]:
    """
    Initialize and authenticate Twitter API v1.1 and v2 clients.
    
    API v1.1 (tweepy.API) is used primarily for media uploads.
    API v2 (tweepy.Client) is used for most other operations like mentions, posting tweets.
    
    Returns:
        Tuple of (api_v1, api_v2). Either can be None if initialization failed.
    """
    # Load credentials from environment variables
    api_key = os.getenv("TWITTER_API_KEY")
    api_key_secret = os.getenv("TWITTER_API_KEY_SECRET")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
    bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
    
    # Validate required credentials
    if not all([api_key, api_key_secret, access_token, access_token_secret]):
        logger.critical(
            "Missing required Twitter API credentials. Ensure TWITTER_API_KEY, "
            "TWITTER_API_KEY_SECRET, TWITTER_ACCESS_TOKEN, and TWITTER_ACCESS_TOKEN_SECRET "
            "are set in environment variables."
        )
        return None, None
    
    if not bearer_token:
        logger.warning(
            "TWITTER_BEARER_TOKEN not set. Some API v2 endpoints may not work properly."
        )
    
    # Initialize API v1.1 client
    api_v1 = _init_v1_client(api_key, api_key_secret, access_token, access_token_secret)
    
    # Initialize API v2 client
    api_v2 = _init_v2_client(api_key, api_key_secret, access_token, access_token_secret, bearer_token)
    
    # Log final status
    if api_v1 and api_v2:
        logger.info("Both Twitter API v1.1 and v2 clients initialized successfully.")
    elif api_v1:
        logger.warning("Only Twitter API v1.1 client initialized. API v2 client failed.")
    elif api_v2:
        logger.warning("Only Twitter API v2 client initialized. API v1.1 client failed.")
    else:
        logger.critical("Failed to initialize both Twitter API clients.")
    
    return api_v1, api_v2

# Alias for compatibility with bot_core.py
def init_client() -> Tuple[Optional[tweepy.API], Optional[tweepy.Client]]:
    """
    Alias for init_clients() to maintain compatibility.
    Sets global api_v1 and api_v2 variables.
    """
    global api_v1, api_v2
    
    # Reset shutdown flag to ensure clean start
    reset_shutdown_flag()
    
    api_v1, api_v2 = init_clients()
    return api_v1, api_v2

def _init_v1_client(api_key: str, api_key_secret: str, access_token: str, access_token_secret: str) -> Optional[tweepy.API]:
    """Initialize Twitter API v1.1 client."""
    try:
        logger.info("Initializing Twitter API v1.1 client...")
        
        auth = tweepy.OAuth1UserHandler(
            api_key, api_key_secret,
            access_token, access_token_secret
        )
        
        client = tweepy.API(auth, wait_on_rate_limit=True)
        
        # Verify credentials
        user = client.verify_credentials()
        if user:
            logger.info(f"Twitter API v1.1 client verified for user: @{user.screen_name}")
            return client
        else:
            logger.error("Failed to verify Twitter API v1.1 credentials.")
            return None
            
    except tweepy.TweepyException as e:
        logger.error(f"Error initializing Twitter API v1.1 client: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error initializing Twitter API v1.1 client: {e}")
        return None

def _init_v2_client(api_key: str, api_key_secret: str, access_token: str, access_token_secret: str, bearer_token: Optional[str]) -> Optional[tweepy.Client]:
    """Initialize Twitter API v2 client."""
    try:
        logger.info("Initializing Twitter API v2 client...")
        
        client = tweepy.Client(
            bearer_token=bearer_token,
            consumer_key=api_key,
            consumer_secret=api_key_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
            wait_on_rate_limit=True
        )
        
        # Verify credentials
        me_response = client.get_me(user_fields=["username"])
        if me_response and me_response.data:
            logger.info(f"Twitter API v2 client verified for user: @{me_response.data.username} (ID: {me_response.data.id})")
            return client
        else:
            logger.error("Failed to verify Twitter API v2 credentials.")
            return None
            
    except tweepy.TweepyException as e:
        logger.error(f"Error initializing Twitter API v2 client: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error initializing Twitter API v2 client: {e}")
        return None

# ============================================
# SINCE ID MANAGEMENT 
# ============================================

def _read_since_id() -> Optional[int]:
    """Reads the since_id from the SINCE_ID_FILE."""
    if not os.path.exists(SINCE_ID_FILE):
        logger.info(f"Since ID file not found at {SINCE_ID_FILE}. Will fetch latest mention as baseline.")
        return None
    try:
        with open(SINCE_ID_FILE, 'r') as f:
            content = f.read().strip()
            if content:
                logger.info(f"Successfully read since_id {content} from {SINCE_ID_FILE}")
                return int(content)
            else:
                logger.warning(f"Since ID file {SINCE_ID_FILE} is empty.")
                return None
    except ValueError:
        logger.error(f"Invalid content in since_id file {SINCE_ID_FILE}. Could not parse to int.")
        return None
    except IOError as e:
        logger.error(f"IOError reading since_id file {SINCE_ID_FILE}: {e}")
        return None

def _write_since_id(since_id: int) -> None:
    """Writes the since_id to the SINCE_ID_FILE."""
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(SINCE_ID_FILE), exist_ok=True)
        with open(SINCE_ID_FILE, 'w') as f:
            f.write(str(since_id))
        logger.info(f"Successfully wrote since_id {since_id} to {SINCE_ID_FILE}")
    except IOError as e:
        logger.error(f"IOError writing since_id to file {SINCE_ID_FILE}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error writing since_id {since_id} to {SINCE_ID_FILE}: {e}", exc_info=True)

def update_since_id_after_reply(original_tweet_id: str) -> None:
    """
    Updates the since_id file with the ID of the original tweet that was replied to.
    This ensures we don't reprocess tweets we've already replied to.
    
    Args:
        original_tweet_id: The ID of the tweet the bot replied to (not the bot's reply ID)
    """
    try:
        # Convert to int for proper comparison
        tweet_id_int = int(original_tweet_id)
        
        # Read current since_id to see if this is newer
        current_since_id = _read_since_id()
        
        # Only update if this ID is newer (higher) than the current since_id
        if current_since_id is None or tweet_id_int > current_since_id:
            logger.info(f"Updating since_id to {tweet_id_int} after successfully replying to tweet")
            _write_since_id(tweet_id_int)
        else:
            logger.debug(f"Not updating since_id after reply - current ID {current_since_id} is newer than {tweet_id_int}")
    except (ValueError, TypeError) as e:
        logger.error(f"Error converting tweet ID {original_tweet_id} to int: {e}")
    except Exception as e:
        logger.error(f"Unexpected error updating since_id after reply: {e}", exc_info=True)

# ============================================
# MENTION LISTENING 
# ============================================

def listen_for_mentions(callback_on_mention: Callable):
    """
    Periodically polls for new mentions to the bot's authenticated user using Twitter API v2.
    
    Args:
        callback_on_mention: A function to call for each new mention. 
                             It will receive the Tweepy Tweet object (v2) as an argument.
    """
    if not api_v2:
        logger.critical("listen_for_mentions: Twitter API v2 client not initialized. Cannot listen.")
        raise RuntimeError("Twitter API v2 client must be initialized before listening for mentions.")

    if not TWITTER_BOT_USERNAME:
        logger.critical("listen_for_mentions: TWITTER_BOT_USERNAME is not set. Cannot determine which user to monitor.")
        raise RuntimeError("TWITTER_BOT_USERNAME is not configured.")

    try:
        logger.info("Attempting to retrieve bot's user ID for mention listening...")
        bot_user_response = api_v2.get_me(user_fields=["id", "username"])
        if not bot_user_response or not bot_user_response.data:
            logger.error(f"Could not retrieve bot user information using get_me(). Response: {bot_user_response}")
            raise RuntimeError("Failed to retrieve bot user ID. Cannot listen for mentions.")
        
        bot_user_id = bot_user_response.data.id
        bot_username_from_api = bot_user_response.data.username
        logger.info(f"Successfully fetched bot user details: ID={bot_user_id}, Username=@{bot_username_from_api}. This is the authenticated user.")

        if TWITTER_BOT_USERNAME.lower() != bot_username_from_api.lower():
            logger.warning(
                f"TWITTER_BOT_USERNAME from .env ('{TWITTER_BOT_USERNAME}') does not match authenticated user from API ('{bot_username_from_api}'). "
                f"Will listen for mentions to @{bot_username_from_api} (the authenticated user)."
            )

    except tweepy.TweepyException as e:
        logger.critical(f"Tweepy error while getting bot user ID: {e}", exc_info=True)
        raise RuntimeError(f"API error getting bot user ID: {e}")
    except Exception as e:
        logger.critical(f"Unexpected error getting bot user ID: {e}", exc_info=True)
        raise RuntimeError(f"Unexpected error getting bot user ID: {e}")

    # Initialize since_id: Try to read from file first.
    last_processed_mention_id = _read_since_id()

    if last_processed_mention_id is None:
        logger.info(f"No valid since_id found in {SINCE_ID_FILE} or file doesn't exist. Fetching initial latest mention ID for @{bot_username_from_api} to set processing baseline...")
        try:
            initial_mentions_response = api_v2.get_users_mentions(
                id=bot_user_id,
                max_results=5,
                tweet_fields=["author_id", "created_at", "conversation_id", "in_reply_to_user_id", "referenced_tweets"]
            )
            if initial_mentions_response.data and len(initial_mentions_response.data) > 0:
                last_processed_mention_id = initial_mentions_response.data[0].id
                logger.info(f"Initial baseline mention ID set to: {last_processed_mention_id} from Twitter API.")
                _write_since_id(last_processed_mention_id)
            elif initial_mentions_response.errors:
                for error in initial_mentions_response.errors:
                     logger.error(f"API error during initial mention fetch: {error.get('title', '')} - {error.get('detail', '')}")
                logger.warning("Could not establish baseline due to API errors. Will fetch all new mentions on first poll if no since_id is loaded.")
            else:
                logger.info(f"No recent mentions found for @{bot_username_from_api}. Will process mentions from this point forward if no since_id is loaded.")
        except tweepy.TweepyException as e:
            logger.error(f"Tweepy error fetching initial mentions: {e}. Will proceed without an initial since_id if none was loaded from file.", exc_info=True)
        except Exception as e:
            logger.error(f"Unexpected error fetching initial mentions: {e}. Will proceed without an initial since_id if none was loaded from file.", exc_info=True)
    else:
        logger.info(f"Successfully loaded last_processed_mention_id {last_processed_mention_id} from {SINCE_ID_FILE}.")

    logger.info(f"Starting to poll for mentions to @{bot_username_from_api} (ID: {bot_user_id}) every {MENTIONS_POLLING_INTERVAL_SECONDS} seconds...")
    
    # Brief pause before starting the loop
    time.sleep(2)

    while True:
        logger.info(f"Mention polling cycle START for @{bot_username_from_api} (ID: {bot_user_id}). Since_id: {last_processed_mention_id}")
        
        # Check for shutdown request at the start of each cycle
        if is_shutdown_requested():
            logger.info("Shutdown requested. Stopping mention polling loop.")
            break
            
        try:
            logger.info(f"Attempting to fetch mentions for user ID {bot_user_id} (since_id: {last_processed_mention_id})...")
            
            mentions_response = api_v2.get_users_mentions(
                id=bot_user_id,
                since_id=last_processed_mention_id,
                tweet_fields=["author_id", "created_at", "text", "conversation_id", "in_reply_to_user_id", "referenced_tweets"],
                expansions=["author_id"],
                max_results=25
            )

            if mentions_response.errors:
                logger.info(f"Received errors from get_users_mentions API: {mentions_response.errors}")
                for error in mentions_response.errors:
                    logger.error(f"Twitter API error when fetching mentions: {error.get('title', '')} - {error.get('detail', '')} (Value: {error.get('value', '')})")

            new_mentions_processed_this_cycle = 0
            if mentions_response.data:
                tweets_to_process = reversed(mentions_response.data)
                logger.info(f"Found {len(mentions_response.data)} new mention(s) to process.")
                
                for tweet in tweets_to_process:
                    if str(tweet.author_id) == str(bot_user_id):
                        logger.info(f"Skipping mention from bot itself (Tweet ID: {tweet.id}, Author ID: {tweet.author_id}, Bot ID: {bot_user_id})")
                        if tweet.id > (last_processed_mention_id or 0):
                             last_processed_mention_id = tweet.id
                        continue

                    logger.info(f"Processing mention: Tweet ID {tweet.id}, Author ID {tweet.author_id}, Text: \"{tweet.text}\"")
                    
                    try:
                        callback_on_mention(tweet)
                        
                        if tweet.id > (last_processed_mention_id or 0):
                            last_processed_mention_id = tweet.id
                        
                        new_mentions_processed_this_cycle += 1
                    except Exception as e:
                        logger.error(f"Error processing mention (Tweet ID: {tweet.id}) with callback: {e}", exc_info=True)
                        if tweet.id > (last_processed_mention_id or 0):
                             last_processed_mention_id = tweet.id

                if new_mentions_processed_this_cycle > 0:
                    logger.info(f"Successfully processed {new_mentions_processed_this_cycle} new mention(s) in this cycle.")
                    if last_processed_mention_id:
                        _write_since_id(last_processed_mention_id)
                else:
                    if mentions_response.data:
                        logger.info("No new, actionable mentions processed this cycle (e.g., all were self-mentions or skipped).")
                        if last_processed_mention_id:
                            _write_since_id(last_processed_mention_id)
                    else:
                         logger.info("No new mentions found in this polling cycle.")

            else:
                logger.info("No new mentions found in this polling cycle.")

        except tweepy.TweepyException as e:
            logger.error(f"Tweepy API error during mention polling loop: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Unexpected error in mention polling loop: {e}", exc_info=True)
            time.sleep(MENTIONS_POLLING_INTERVAL_SECONDS * 2)
        
        logger.info(f"Mention polling cycle for @{bot_username_from_api} COMPLETE. Sleeping for {MENTIONS_POLLING_INTERVAL_SECONDS} seconds.")
        
        # Sleep in smaller intervals so we can respond to shutdown requests quickly
        sleep_remaining = MENTIONS_POLLING_INTERVAL_SECONDS
        while sleep_remaining > 0 and not is_shutdown_requested():
            sleep_time = min(1, sleep_remaining)  # Sleep in 1-second intervals
            time.sleep(sleep_time)
            sleep_remaining -= sleep_time

        if is_shutdown_requested():
            logger.info("Shutdown requested. Stopping mention polling loop.")
            break

    logger.info("Mention listening loop has stopped.")

def get_baseline_mention_id(api_v2: tweepy.Client) -> Optional[str]:
    """
    Get the most recent mention to establish a baseline.
    Only process mentions newer than this on startup.
    
    Args:
        api_v2: Initialized Twitter API v2 client
    
    Returns:
        The ID of the most recent mention, or None if no mentions found or error occurred.
    """
    if not api_v2:
        logger.error("get_baseline_mention_id: Twitter API v2 client is None.")
        return None
    
    try:
        # Get bot's user ID first
        bot_user_response = api_v2.get_me(user_fields=["id", "username"])
        if not bot_user_response or not bot_user_response.data:
            logger.error("Could not retrieve bot user information for baseline mention query.")
            return None
        
        bot_user_id = bot_user_response.data.id
        logger.info(f"Fetching baseline mention for bot user: @{bot_user_response.data.username} (ID: {bot_user_id})")
        
        # Fetch just the most recent mentions
        response = api_v2.get_users_mentions(
            id=bot_user_id,
            max_results=5,  # Just need the latest few
            tweet_fields=["created_at", "author_id"]
        )
        
        if response.data and len(response.data) > 0:
            latest_mention = response.data[0]  # Most recent mention
            latest_id = latest_mention.id
            logger.info(f"Baseline mention ID established: {latest_id} (from {latest_mention.created_at})")
            return latest_id
        else:
            logger.info("No recent mentions found - will process all new mentions from this point forward")
            return None
            
    except tweepy.TweepyException as e:
        logger.error(f"Twitter API error getting baseline mention: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting baseline mention: {e}")
        return None

def get_bot_user_info(api_v2: tweepy.Client) -> Optional[Tuple[str, str]]:
    """
    Get bot's user ID and username.
    
    Args:
        api_v2: Initialized Twitter API v2 client
    
    Returns:
        Tuple of (user_id, username) or None if error occurred.
    """
    if not api_v2:
        logger.error("get_bot_user_info: Twitter API v2 client is None.")
        return None
    
    try:
        bot_user_response = api_v2.get_me(user_fields=["id", "username"])
        if bot_user_response and bot_user_response.data:
            user_id = bot_user_response.data.id
            username = bot_user_response.data.username
            logger.info(f"Retrieved bot user info: @{username} (ID: {user_id})")
            return user_id, username
        else:
            logger.error("Could not retrieve bot user information.")
            return None
            
    except tweepy.TweepyException as e:
        logger.error(f"Twitter API error getting bot user info: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting bot user info: {e}")
        return None

def fetch_mentions(api_v2: tweepy.Client, user_id: str, since_id: Optional[str] = None, max_results: int = 25) -> Optional[tweepy.Response]:
    """
    Fetch mentions for a user.
    
    Args:
        api_v2: Initialized Twitter API v2 client
        user_id: The user ID to fetch mentions for
        since_id: Optional ID to fetch mentions since (newer than this ID)
        max_results: Maximum number of mentions to fetch (default 25, max 100)
    
    Returns:
        Twitter API response object or None if error occurred.
    """
    if not api_v2:
        logger.error("fetch_mentions: Twitter API v2 client is None.")
        return None
    
    try:
        params = {
            "id": user_id,
            "max_results": max_results,
            "tweet_fields": ["author_id", "created_at", "text", "conversation_id", "in_reply_to_user_id", "referenced_tweets"],
            "expansions": ["author_id"]
        }
        
        if since_id:
            params["since_id"] = since_id
            logger.info(f"Fetching mentions for user {user_id} since ID {since_id}")
        else:
            logger.info(f"Fetching latest {max_results} mentions for user {user_id}")
        
        response = api_v2.get_users_mentions(**params)
        
        if response.errors:
            logger.warning(f"API returned errors when fetching mentions: {response.errors}")
        
        return response
        
    except tweepy.TweepyException as e:
        logger.error(f"Twitter API error fetching mentions: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching mentions: {e}")
        return None

def is_self_mention(tweet: tweepy.Tweet, bot_user_id: str) -> bool:
    """
    Check if a tweet is from the bot itself.
    
    Args:
        tweet: The tweet object to check
        bot_user_id: The bot's user ID
    
    Returns:
        True if the tweet is from the bot itself, False otherwise.
    """
    if not tweet or not hasattr(tweet, 'author_id'):
        return False
    
    return str(tweet.author_id) == str(bot_user_id)

def parse_mention_response(response: tweepy.Response) -> Tuple[list, bool]:
    """
    Extract mentions from Twitter API response.
    
    Args:
        response: Twitter API response from get_users_mentions
    
    Returns:
        Tuple of (mentions_list, has_errors) where:
        - mentions_list: List of tweet objects (empty if no mentions)
        - has_errors: Boolean indicating if the response contained errors
    """
    if not response:
        return [], True
    
    mentions = []
    has_errors = bool(response.errors)
    
    if response.data:
        mentions = list(response.data)
        logger.info(f"Parsed {len(mentions)} mentions from API response")
    else:
        logger.info("No mentions found in API response")
    
    if has_errors:
        logger.warning(f"Response contained {len(response.errors)} error(s)")
    
    return mentions, has_errors

# ============================================
# HELPER FUNCTIONS FOR POSTING AND UPLOADS
# ============================================

# Define specific HTTP status codes that should not be retried
NON_RETRYABLE_STATUS_CODES = [400, 401, 403, 404]  # Bad Request, Unauthorized, Forbidden, Not Found

def is_retryable_twitter_error(error: Exception) -> bool:
    """
    Determine if a Twitter API error should be retried.
    
    Args:
        error: The exception or error object
    
    Returns:
        True if the error should be retried, False otherwise.
    """
    if isinstance(error, tweepy.TweepyException):
        status_code = getattr(error.response, 'status_code', None)
        if status_code in NON_RETRYABLE_STATUS_CODES:
            return False
    
    return True

def _attempt_tweet_post(api_v2: tweepy.Client, tweet_params: dict) -> Optional[tweepy.Response]:
    """Simple tweet posting without retry logic."""
    try:
        response = api_v2.create_tweet(**tweet_params)
        if response.data and response.data.get("id"):
            return response
        return None
    except tweepy.TweepyException as e:
        if not is_retryable_twitter_error(e):
            return None
        raise  # Re-raise for retry logic

def post_reply_to_tweet(
    api_v2: tweepy.Client, 
    tweet_id: str, 
    text: str, 
    media_id: Optional[str] = None,
    max_retries: int = 3,
    retry_delay: int = 5
) -> Optional[tweepy.Response]:
    """
    Posts a reply to a given tweet. Optionally attaches media.
    
    Args:
        api_v2: Initialized Twitter API v2 client
        tweet_id: The ID of the tweet to reply to
        text: The text content of the reply
        media_id: Optional media ID to attach (e.g., from video upload)
        max_retries: Maximum number of retry attempts (default 3)
        retry_delay: Seconds to wait between retries (default 5)
    
    Returns:
        A tweepy.Response object if successful, None otherwise.
    """
    if not api_v2:
        return None

    reply_params = {"in_reply_to_tweet_id": tweet_id, "text": text}
    if media_id:
        reply_params["media_ids"] = [media_id]

    for attempt in range(max_retries):
        try:
            response = _attempt_tweet_post(api_v2, reply_params)
            if response:
                # Update since_id after successful reply
                update_since_id_after_reply(tweet_id)
                return response
        except tweepy.TweepyException:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                return None
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                return None

    return None

# Alias for compatibility with action_handler.py
def post_reply(tweet_id: str, text: str, media_id: Optional[str] = None) -> Optional[tweepy.Response]:
    """
    Alias for post_reply_to_tweet() to maintain compatibility.
    Uses global api_v2 client.
    """
    if not api_v2:
        logger.error("post_reply: Twitter API v2 client not initialized.")
        return None
    return post_reply_to_tweet(api_v2, tweet_id, text, media_id)

def get_video_processing_status(api_v1: tweepy.API, media_id: str) -> Dict[str, Any]:
    """
    Check the processing status of an uploaded video.
    
    Args:
        api_v1: Initialized Twitter API v1.1 client
        media_id: The media ID to check status for
    
    Returns:
        Dict with keys: 'state', 'progress_percent', 'error', 'success'
    """
    if not api_v1:
        return {'state': 'unknown', 'success': False, 'error': 'No API client'}
    
    try:
        upload_status = api_v1.get_media_upload_status(media_id)
        processing_info = upload_status.processing_info or {}
        
        state = processing_info.get('state', 'unknown')
        result = {
            'state': state,
            'progress_percent': processing_info.get('progress_percent', 0),
            'success': state == 'succeeded',
            'error': None
        }
        
        if state == 'failed':
            error_info = processing_info.get('error', {})
            result['error'] = f"{error_info.get('name', 'Unknown')}: {error_info.get('message', 'No details')}"
        
        return result
        
    except Exception as e:
        return {'state': 'unknown', 'success': False, 'error': str(e), 'progress_percent': None}

def _wait_for_video_processing(api_v1: tweepy.API, media_id: str, max_checks: int, interval: int) -> bool:
    """Wait for video processing to complete. Returns True if successful."""
    for _ in range(max_checks):
        status = get_video_processing_status(api_v1, media_id)
        
        if status['success']:
            return True
        elif status['state'] == 'failed':
            return False
        elif status['state'] in ['in_progress', 'pending']:
            time.sleep(interval)
        else:
            time.sleep(interval)
    
    return False  # Timeout

def upload_video_to_twitter(
    api_v1: tweepy.API, 
    video_filepath: str,
    max_status_checks: int = 24,
    status_check_interval: int = 5
) -> Optional[str]:
    """
    Upload a video to Twitter using chunked upload.
    
    Args:
        api_v1: Initialized Twitter API v1.1 client
        video_filepath: Absolute path to the video file
        max_status_checks: Maximum number of status checks (default 24)
        status_check_interval: Seconds between status checks (default 5)
    
    Returns:
        The Twitter media_id string if successful, None otherwise.
    """
    if not api_v1 or not os.path.exists(video_filepath):
        return None

    try:
        file_size = os.path.getsize(video_filepath)
        logger.info(f"Starting video upload for: {video_filepath} (Size: {file_size / (1024*1024):.2f} MB)")

        # Upload the video (handles INIT, APPEND, FINALIZE phases)
        media_upload_response = api_v1.media_upload(
            filename=video_filepath, 
            media_category='tweet_video', 
            chunked=True
        )
        media_id = media_upload_response.media_id_string
        logger.info(f"Video Upload - INIT successful. Media ID: {media_id}")

        # Wait for processing to complete
        if _wait_for_video_processing(api_v1, media_id, max_status_checks, status_check_interval):
            logger.info(f"Video processing for media_id {media_id} SUCCEEDED.")
            return media_id
        else:
            logger.error(f"Video processing for media_id {media_id} failed or timed out.")
            return None

    except Exception as e:
        logger.error(f"Unexpected error during video upload for {video_filepath}: {e}", exc_info=True)
        return None

# Alias for compatibility with action_handler.py
def upload_video(video_filepath: str) -> Optional[str]:
    """
    Alias for upload_video_to_twitter() to maintain compatibility.
    Uses global api_v1 client.
    """
    if not api_v1:
        logger.error("upload_video: Twitter API v1.1 client not initialized.")
        return None
    return upload_video_to_twitter(api_v1, video_filepath)