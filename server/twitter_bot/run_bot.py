#!/usr/bin/env python3
"""
Simple entry point script to run the CelebXplain Twitter Bot.

Usage:
    python run_bot.py [--personas-file path/to/personas.json]
"""

import argparse
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import from same directory
from bot_core import create_bot

def main():
    """Main entry point for the bot runner script"""
    parser = argparse.ArgumentParser(
        description="Run the CelebXplain Twitter Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables Required:
    TWITTER_API_KEY                - Twitter API Key
    TWITTER_API_KEY_SECRET         - Twitter API Key Secret  
    TWITTER_ACCESS_TOKEN           - Twitter Access Token
    TWITTER_ACCESS_TOKEN_SECRET    - Twitter Access Token Secret
    TWITTER_BEARER_TOKEN           - Twitter Bearer Token
    TWITTER_BOT_USERNAME           - Bot's Twitter username (e.g., @CelebXplainBot)
    OPENAI_API_KEY                 - OpenAI API Key for tweet parsing

Optional Environment Variables:
    LOG_LEVEL                      - Logging level (DEBUG, INFO, WARNING, ERROR)
    MENTIONS_POLLING_INTERVAL_SECONDS - How often to check for mentions (default: 30)
    APP_DATA_BASE_DIR              - Base directory for data files (default: data)
        """
    )
    
    parser.add_argument(
        '--personas-file',
        type=str,
        help='Path to personas.json file (default: ../data/personas.json)'
    )
    
    parser.add_argument(
        '--check-status',
        action='store_true',
        help='Check bot status and exit (useful for debugging setup)'
    )
    
    parser.add_argument(
        '--test',
        action='store_true',
        help='Run in test mode - use manual input instead of timer for polling cycles'
    )
    
    args = parser.parse_args()
    
    try:
        print("🚀 Initializing CelebXplain Twitter Bot...")
        
        # Create and initialize the bot
        bot = create_bot(personas_file_path=args.personas_file, test_mode=args.test)
        
        if args.check_status:
            # Just check status and exit
            status = bot.get_status()
            print("\n📊 Bot Status:")
            for key, value in status.items():
                print(f"  {key}: {value}")
            print("\n✅ Bot is properly initialized and ready to run!")
            return 0
        
        # Start the bot (this blocks until shutdown)
        print("✅ Bot initialized successfully!")
        print("\n🎭 Available personas:", ", ".join(bot.get_status()["available_personas"]))
        
        if args.test:
            print("\n🧪 TEST MODE ACTIVE - Press Enter to trigger polling cycles manually")
        
        print("\n🔄 Starting mention listener...")
        print("📝 Bot is now listening for mentions. Press Ctrl+C to stop.\n")
        
        bot.start()
        
    except KeyboardInterrupt:
        print("\n👋 Received shutdown signal, stopping bot...")
        return 0
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        return 1
    finally:
        print("🛑 Bot has stopped.")

if __name__ == "__main__":
    sys.exit(main()) 