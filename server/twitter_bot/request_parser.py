import os
import json
import logging
from typing import Optional, Tuple, List, Dict
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# Import the existing LLM utility
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from sieve_functions.utils.llm import call_llm

# Configure logging
logger = logging.getLogger(__name__)

class TweetExtract(BaseModel):
    """
    Pydantic model for structured LLM output.
    The LLM should extract the main topic and the persona ID mentioned.
    """
    topic: Optional[str]
    persona_id: Optional[str]

class PersonaInfo:
    """Helper class to manage persona data and provide easy access to supported celebrities."""
    
    def __init__(self, personas_data: dict):
        self.personas_data = personas_data
        self._id_lookup = self._build_id_lookup()
    
    def _build_id_lookup(self) -> Dict[str, str]:
        """Build a case-insensitive lookup from persona IDs to persona IDs (for ID-based search)."""
        lookup = {}
        for persona in self.personas_data.get("personas", []):
            persona_id = persona.get("id", "").strip().lower()
            if persona_id:
                lookup[persona_id] = persona.get("id", "")  # Store original case
        return lookup
    
    def get_supported_celebrities(self) -> List[str]:
        """Return a list of supported celebrity names."""
        return [persona.get("name", "") for persona in self.personas_data.get("personas", []) 
                if persona.get("name")]
    
    def get_supported_persona_ids(self) -> List[str]:
        """Return a list of supported persona IDs."""
        return [persona.get("id", "") for persona in self.personas_data.get("personas", []) 
                if persona.get("id")]
    
    def find_persona_id(self, persona_id: str) -> Optional[str]:
        """Find persona ID by exact persona ID match (case-insensitive)."""
        identifier_lower = persona_id.strip().lower()
        return self._id_lookup.get(identifier_lower)

def parse_tweet(tweet_text: str, personas_data: dict) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Parse tweet text to extract a topic and a mentioned celebrity using the existing LLM utility.

    Args:
        tweet_text: The full text of the tweet.
        personas_data: Loaded personas data (from personas.json).

    Returns:
        A tuple (topic, persona_id, error_message).
        - topic: The extracted topic.
        - persona_id: The ID of the matched persona.
        - error_message: A string containing an error message if parsing fails
                         or celebrity is not found, otherwise None.
    """
    # Input validation
    if not tweet_text or not tweet_text.strip():
        return None, None, "Tweet text is empty."

    if not personas_data or "personas" not in personas_data:
        return None, None, "Personas data is invalid or missing."

    # Initialize persona helper
    persona_info = PersonaInfo(personas_data)
    supported_persona_ids = persona_info.get_supported_persona_ids()
    
    try:
        logger.info(f"Parsing tweet: \"{tweet_text}\"")
        
        # Create system prompt with supported persona IDs for better extraction
        system_prompt = f"""You are an expert tweet analyst.
Your task is to identify two key pieces of information from a user's tweet:
1. The main **topic** or question the user wants explained.
2. The **persona_id** that the user wants to use for the explanation.

Supported persona IDs include: {', '.join(supported_persona_ids)}

If the user doesn't explicitly mention a persona ID, or if the persona ID is not clearly identifiable, return null for `persona_id`.
The topic should be a concise summary of what needs to be explained.
The persona_id should be extracted exactly as mentioned in the tweet.
Do not infer a persona_id if not mentioned."""

        user_prompt = f"Here's the tweet: \"{tweet_text}\""

        # Use the existing LLM utility with structured output
        extracted_data = call_llm(
            provider="gpt",
            prompt=user_prompt,
            system_prompt=system_prompt,
            response_model=TweetExtract
        )

        if not isinstance(extracted_data, TweetExtract):
            logger.error("LLM parsing failed to return expected TweetExtract structure.")
            return None, None, "Error: Could not parse tweet structure from LLM."

        topic = extracted_data.topic
        persona_id = extracted_data.persona_id

        logger.info(f"LLM extracted: Topic='{topic}', Persona ID='{persona_id}'")

        # Validate topic extraction
        if not topic or not topic.strip():
            return None, None, "Error: Could not determine the topic from the tweet."

        # Handle missing persona ID
        if not persona_id or not persona_id.strip():
            return topic, None, "No persona ID mentioned or identified in the tweet."

        # Match persona ID to persona
        matched_persona_id = persona_info.find_persona_id(persona_id)
        
        if not matched_persona_id:
            supported_list = ', '.join(supported_persona_ids)
            logger.warning(f"Persona ID '{persona_id}' not found in personas data.")
            return topic, None, f"Error: Persona ID '{persona_id}' is not supported. Supported persona IDs: {supported_list}"

        logger.info(f"Successfully matched persona ID '{persona_id}' to persona ID: '{matched_persona_id}'")
        return topic, matched_persona_id, None

    except Exception as e:
        logger.error(f"Error during tweet parsing or LLM call: {e}")
        return None, None, f"An unexpected error occurred: {str(e)}"

def load_personas_data(data_dir: str = "data") -> dict:
    """
    Helper function to load personas data from the standard location.
    
    Args:
        data_dir: Directory containing personas.json (relative to server directory)
    
    Returns:
        dict: Loaded personas data or empty dict if loading fails
    """
    current_dir = os.path.dirname(__file__)
    personas_path = os.path.join(current_dir, "..", data_dir, "personas.json")
    
    try:
        with open(personas_path, "r") as f:
            personas_data = json.load(f)
        logger.info(f"Successfully loaded personas.json from {personas_path}")
        return personas_data
    except FileNotFoundError:
        logger.error(f"personas.json not found at {personas_path}")
        return {"personas": []}
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing personas.json: {e}")
        return {"personas": []}
    except Exception as e:
        logger.error(f"Error loading personas.json: {e}")
        return {"personas": []}

def get_supported_personas() -> List[Dict[str, str]]:
    """
    Convenience function to get a list of supported personas with their IDs and names.
    
    Returns:
        List of dicts with 'id' and 'name' keys
    """
    personas_data = load_personas_data()
    persona_info = PersonaInfo(personas_data)
    
    return [
        {"id": persona.get("id", ""), "name": persona.get("name", "")}
        for persona in personas_data.get("personas", [])
        if persona.get("id") and persona.get("name")
    ]
