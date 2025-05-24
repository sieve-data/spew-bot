import logging
import os
import sys
import signal
from typing import Optional, Tuple
from dotenv import load_dotenv

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import our modules - since we're in twitter_bot directory, import directly
import twitter_client
import action_handler

# Configure logging
level_str = os.environ.get('LOG_LEVEL', 'INFO').upper()
level = logging.getLevelName(level_str)
logging.basicConfig(level=level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TwitterBot:
    """
    Main Twitter bot orchestrator that coordinates all components.
    Handles initialization, startup, and graceful shutdown.
    """
    
    def __init__(self, personas_file_path: str = None, test_mode: bool = False):
        """
        Initialize the Twitter bot with all required components.
        
        Args:
            personas_file_path: Optional path to personas.json file
            test_mode: If True, use manual input instead of timer for polling
        """
        self.personas_file_path = personas_file_path
        self.test_mode = test_mode
        self.api_v1: Optional[twitter_client.tweepy.API] = None
        self.api_v2: Optional[twitter_client.tweepy.Client] = None
        self.is_running = False
        self.bot_username = None
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.shutdown()
        
    def initialize(self) -> bool:
        """
        Initialize all bot components.
        
        Returns:
            True if initialization successful, False otherwise
        """
        logger.info("Initializing TwitterBot components...")
        
        # 1. Load environment variables
        self._load_environment()
        
        # 2. Initialize Twitter API clients
        if not self._init_twitter_clients():
            return False
            
        # 3. Initialize action handler with Sieve orchestrator
        if not self._init_action_handler():
            return False
            
        logger.info("TwitterBot initialization completed successfully!")
        return True
        
    def _load_environment(self):
        """Load environment variables from .env file"""
        dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
        if os.path.exists(dotenv_path):
            load_dotenv(dotenv_path)
            logger.info(f"Loaded .env file from: {dotenv_path}")
        else:
            logger.warning(f".env file not found at {dotenv_path}. Will rely on system environment variables.")
            
    def _init_twitter_clients(self) -> bool:
        """Initialize Twitter API v1.1 and v2 clients"""
        try:
            logger.info("Initializing Twitter API clients...")
            self.api_v1, self.api_v2 = twitter_client.init_client()
            
            if not self.api_v1 or not self.api_v2:
                logger.critical("Failed to initialize Twitter API clients. Check credentials in .env")
                return False
                
            # Get bot username for logging
            try:
                bot_user_response = self.api_v2.get_me(user_fields=["username"])
                if bot_user_response and bot_user_response.data:
                    self.bot_username = bot_user_response.data.username
                    logger.info(f"Twitter clients initialized successfully. Bot User: @{self.bot_username}")
                else:
                    logger.warning("Could not retrieve bot username, but clients are initialized")
            except Exception as e:
                logger.warning(f"Could not retrieve bot username: {e}, but clients are initialized")
                
            return True
            
        except Exception as e:
            logger.critical(f"Failed to initialize Twitter clients: {e}")
            return False
            
    def _init_action_handler(self) -> bool:
        """Initialize the action handler with Sieve orchestrator"""
        try:
            logger.info("Initializing action handler and Sieve orchestrator...")
            action_handler.init_action_handler(self.personas_file_path)
            logger.info("Action handler initialized successfully!")
            return True
            
        except Exception as e:
            logger.critical(f"Failed to initialize action handler: {e}")
            return False
            
    def start(self):
        """
        Start the bot's main mention listening loop.
        This method blocks until shutdown is called.
        """
        if not self.api_v1 or not self.api_v2:
            logger.critical("Cannot start bot - Twitter clients not initialized")
            return
            
        if not action_handler.personas_data:
            logger.critical("Cannot start bot - Action handler not initialized")
            return
            
        self.is_running = True
        bot_username = self.bot_username or twitter_client.TWITTER_BOT_USERNAME
        
        logger.info(f"Starting TwitterBot mention listener for @{bot_username}...")
        logger.info("Bot is now running and listening for mentions. Press Ctrl+C to stop.")
        
        try:
            # Start the mention listening loop - this blocks until shutdown
            twitter_client.listen_for_mentions(
                callback_on_mention=action_handler.handle_mention,
                test_mode=self.test_mode
            )
            
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down...")
            # Don't call shutdown again if already shutting down
            if self.is_running:
                self.shutdown()
        except Exception as e:
            logger.critical(f"Twitter mention listener failed: {e}")
            self.shutdown()
            
    def shutdown(self):
        """Gracefully shutdown the bot"""
        if not self.is_running:
            return
            
        logger.info("Shutting down TwitterBot...")
        self.is_running = False
        
        # Request shutdown of the mention listening loop
        twitter_client.request_shutdown()
        
        # Currently, we don't have background threads to clean up
        # In future phases with worker threads, we'd clean them up here
        
        logger.info("TwitterBot shutdown complete.")
        
    def get_status(self) -> dict:
        """
        Get current bot status for monitoring/debugging.
        
        Returns:
            Dictionary with bot status information
        """
        status = {
            "is_running": self.is_running,
            "bot_username": self.bot_username,
            "twitter_v1_initialized": self.api_v1 is not None,
            "twitter_v2_initialized": self.api_v2 is not None,
            "action_handler_initialized": action_handler.personas_data is not None,
            "available_personas": action_handler.get_available_personas(),
            "pending_jobs_count": action_handler.get_pending_jobs_count(),
        }
        
        # Add detailed job info if there are pending jobs
        if action_handler.get_pending_jobs_count() > 0:
            status["pending_jobs"] = action_handler.get_pending_jobs_info()
        
        return status

def create_bot(personas_file_path: str = None, test_mode: bool = False) -> TwitterBot:
    """
    Factory function to create and initialize a TwitterBot instance.
    
    Args:
        personas_file_path: Optional path to personas.json file
        test_mode: If True, use manual input instead of timer for polling
        
    Returns:
        Initialized TwitterBot instance
        
    Raises:
        RuntimeError: If initialization fails
    """
    bot = TwitterBot(personas_file_path, test_mode)
    
    if not bot.initialize():
        raise RuntimeError("Failed to initialize TwitterBot")
        
    return bot

def main():
    """
    Main entry point for running the bot as a standalone script.
    """
    logger.info("Starting CelebXplain Twitter Bot...")
    
    try:
        # Create and initialize bot
        bot = create_bot()
        
        # Print status for verification
        status = bot.get_status()
        logger.info(f"Bot Status: {status}")
        
        # Start the bot (this blocks)
        bot.start()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, exiting...")
    except Exception as e:
        logger.critical(f"Fatal error starting bot: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Bot has shut down.")

if __name__ == "__main__":
    main()
