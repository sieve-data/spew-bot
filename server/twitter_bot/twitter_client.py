import os
import tweepy
import logging
from typing import Optional, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

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