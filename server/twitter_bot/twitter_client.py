import os
import time
import tweepy
import logging
from typing import Optional, Tuple, Dict, Any, Callable
from dotenv import load_dotenv
import action_handler

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Global variables for mention listening
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
# MENTION LISTENING 
# ============================================

def listen_for_mentions(callback_on_mention: Callable, test_mode: bool = False):
    """
    Periodically polls for new mentions to the bot's authenticated user using Twitter API v2.
    Also checks for completed video generation jobs.
    """
    if not api_v2:
        raise RuntimeError("Twitter API v2 client must be initialized before listening for mentions.")

    if not TWITTER_BOT_USERNAME:
        raise RuntimeError("TWITTER_BOT_USERNAME is not configured.")

    # Initialize mention listener
    bot_user_id, bot_username = _initialize_mention_listener()
    last_processed_mention_id = get_baseline_mention_id(api_v2)
    
    logger.info(f"Starting mention polling for @{bot_username}")
    
    # Main polling loop
    while not is_shutdown_requested():
        try:
            # Check for new mentions
            last_processed_mention_id = _process_mention_cycle(
                bot_user_id, last_processed_mention_id, callback_on_mention
            )
            
            # Check for completed video generation jobs
            try:
                logger.info("🎬 Checking for completed video generation jobs...")
                action_handler.check_completed_jobs()
                logger.info("✅ Completed job check finished")
            except Exception as e:
                logger.error(f"❌ Error checking completed jobs: {e}", exc_info=True)
            
        except Exception as e:
            logger.error(f"Error in polling cycle: {e}")
        
        _sleep_with_shutdown_check(MENTIONS_POLLING_INTERVAL_SECONDS, test_mode)
    
    logger.info("Mention listening stopped")

def _initialize_mention_listener():
    """Initialize mention listener and return bot user info."""
    bot_info = get_bot_user_info(api_v2)
    if not bot_info:
        raise RuntimeError("Failed to retrieve bot user information")
    
    bot_user_id, bot_username = bot_info
    
    if TWITTER_BOT_USERNAME.lower() != bot_username.lower():
        logger.warning(f"Username mismatch: env={TWITTER_BOT_USERNAME}, api={bot_username}")
    
    return bot_user_id, bot_username

def _process_mention_cycle(bot_user_id, since_id, callback_on_mention):
    """Process one mention polling cycle and return updated since_id."""
    response = fetch_mentions(api_v2, bot_user_id, since_id)
    if not response:
        return since_id
    
    mentions, has_errors = parse_mention_response(response)
    if has_errors:
        logger.warning("API returned errors when fetching mentions")
    
    if not mentions:
        return since_id
    
    return _process_mentions(mentions, bot_user_id, since_id, callback_on_mention)

def _process_mentions(mentions, bot_user_id, since_id, callback_on_mention):
    """Process a list of mentions and return updated since_id."""
    updated_since_id = since_id
    
    for tweet in reversed(mentions):  # Process chronologically
        if is_self_mention(tweet, bot_user_id):
            updated_since_id = max(tweet.id, updated_since_id or 0)
            continue
        
        try:
            callback_on_mention(tweet)
        except Exception as e:
            logger.error(f"Error processing mention {tweet.id}: {e}")
        
        updated_since_id = max(tweet.id, updated_since_id or 0)
    
    return updated_since_id

def _sleep_with_shutdown_check(seconds, test_mode=False):
    """Sleep in small intervals to allow quick shutdown response, or wait for user input in test mode."""
    if test_mode:
        try:
            print("\n🧪 Test mode: Press Enter to continue to next polling cycle (or Ctrl+C to stop)...")
            input()
        except KeyboardInterrupt:
            # Convert KeyboardInterrupt to shutdown request
            request_shutdown()
        except EOFError:
            # Handle case where input is closed (e.g., in automated tests)
            logger.info("Input closed, treating as shutdown request")
            request_shutdown()
    else:
        remaining = seconds
        while remaining > 0 and not is_shutdown_requested():
            sleep_time = min(1, remaining)
            time.sleep(sleep_time)
            remaining -= sleep_time

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
        logger.info(f"🐦 Attempting to post tweet with params: {tweet_params}")
        response = api_v2.create_tweet(**tweet_params)
        if response.data and response.data.get("id"):
            logger.info(f"✅ Tweet posted successfully! ID: {response.data.get('id')}")
            return response
        else:
            logger.error(f"❌ Twitter API response missing data or ID: {response}")
            return None
    except tweepy.TweepyException as e:
        logger.error(f"❌ TWITTER API EXCEPTION: {e}")
        logger.error(f"❌ Exception details: {e.response.text if hasattr(e, 'response') and e.response else 'No response details'}")
        if not is_retryable_twitter_error(e):
            logger.error(f"❌ Error is NOT retryable, returning None")
            return None
        logger.info(f"⚠️ Error is retryable, re-raising for retry logic")
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
                # No need to update file-based since_id anymore - we keep it in memory only
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