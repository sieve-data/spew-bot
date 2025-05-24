import os
import tweepy
import logging
from typing import Optional, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Global API client objects
api_v1: Optional[tweepy.API] = None
api_v2: Optional[tweepy.Client] = None

def init_clients() -> Tuple[Optional[tweepy.API], Optional[tweepy.Client]]:
    """
    Initialize and authenticate Twitter API v1.1 and v2 clients.
    
    API v1.1 (tweepy.API) is used primarily for media uploads.
    API v2 (tweepy.Client) is used for most other operations like mentions, posting tweets.
    
    Returns:
        Tuple of (api_v1, api_v2). Either can be None if initialization failed.
    """
    global api_v1, api_v2
    
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

def get_clients() -> Tuple[Optional[tweepy.API], Optional[tweepy.Client]]:
    """
    Get the initialized client instances.
    
    Returns:
        Tuple of (api_v1, api_v2). Call init_clients() first if not already done.
    """
    return api_v1, api_v2

def is_initialized() -> bool:
    """Check if at least one client is initialized."""
    return api_v1 is not None or api_v2 is not None