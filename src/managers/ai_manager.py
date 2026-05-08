"""AI Manager for generating social media metadata using OpenAI."""

import json
import os
import sys
from typing import Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv
from .api_client import APIClient
from .config_manager import ConfigManager

load_dotenv()


def safe_print(text: str) -> None:
    """Safely print text that may contain Unicode characters (emojis, etc)."""
    try:
        print(text)
    except UnicodeEncodeError:
        # Fallback: encode to ascii with error handling, or print without emojis
        try:
            # Try encoding with errors='replace' to substitute problematic chars
            safe_text = text.encode(sys.stdout.encoding or 'utf-8', errors='replace').decode(sys.stdout.encoding or 'utf-8', errors='replace')
            print(safe_text)
        except Exception:
            # Last resort: print ASCII-safe version
            print(text.encode('ascii', errors='replace').decode('ascii', errors='replace'))

class AIManager:
    """Manages AI-powered content generation for social media metadata."""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        Initialize the AI manager.
        
        Args:
            config_manager: Optional config manager instance
        """
        self.config_manager = config_manager or ConfigManager()
        config = self.config_manager.get_config()
        
        # Initialize OpenAI client for local fallback
        self.client = OpenAI()
        self.model = "gpt-4o-mini"  # Using gpt-4o-mini
        
        # Initialize backend API client if configured
        self.api_client = None
        if config.use_backend_api and config.api_key:
            try:
                self.api_client = APIClient(config.api_key, config.backend_api_url)
                # Test connection
                if self.api_client.test_connection():
                    print("[API] Connected to backend API")
                else:
                    print("[API] Backend API unreachable, will use local mode")
                    self.api_client = None
            except Exception as e:
                print(f"[API] Failed to initialize backend API client: {e}")
                self.api_client = None
    
    def generate_metadata(self, filename: str, game_context: str = "gaming", template_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Generate social media metadata for a video file.
        
        Uses backend API if available, falls back to local OpenAI.
        Supports custom prompt templates from database.
        
        Args:
            filename: Name of the video file
            game_context: Context about the game being played
            template_id: Optional specific template ID to use
            
        Returns:
            Dictionary containing title, caption, and hashtags
        """
        # Try backend API first if available
        if self.api_client:
            try:
                print("[AI] Using backend API for AI enrichment...")
                metadata = self.api_client.generate_metadata(filename, game_context)
                
                # Sanitize metadata to remove emojis and problematic characters
                metadata = self._sanitize_metadata(metadata)
                
                safe_print(f"[AI] AI generated metadata for {filename}")
                safe_print(f"   Title: {metadata.get('title', 'N/A')}")
                safe_print(f"   Caption: {metadata.get('caption', 'N/A')[:50]}...")
                safe_print(f"   Hashtags: {metadata.get('hashtags', 'N/A')}")
                
                return metadata
                
            except Exception as e:
                print(f"[AI] Backend API failed, falling back to local OpenAI: {e}")
        
        # Fallback to local OpenAI with template support
        return self._generate_metadata_local(filename, game_context, template_id)
    
    def _generate_metadata_local(self, filename: str, game_context: str = "gaming", template_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Generate metadata using local OpenAI client with optional template support.
        
        Args:
            filename: Name of the video file
            game_context: Context about the game being played
            
        Returns:
            Dictionary containing title, caption, and hashtags
        """
        try:
            print("[AI] Using local OpenAI for AI enrichment...")
            
            # Load template from database if available
            from analytics.database import AnalyticsDatabase
            
            db = AnalyticsDatabase()
            template = None
            
            if template_id:
                template = db.get_prompt_template(template_id)
            else:
                template = db.get_active_prompt_template()
            
            # Create the prompt based on template or default
            if template:
                print(f"[AI] Using template: {template.name}")
                prompt = template.prompt_text.replace("{filename}", filename).replace("{game_context}", game_context)
            else:
                prompt = self._create_prompt(filename, game_context)
            
            # Generate metadata using OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "video_metadata",
                        "strict": True,
                        "schema": {
                            "type": "object",
                            "properties": {
                                "title": {
                                    "type": "string",
                                    "description": "The title of the video."
                                },
                                "caption": {
                                    "type": "string",
                                    "description": "A descriptive caption for the video."
                                },
                                "hashtags": {
                                    "type": "array",
                                    "description": "A list of hashtags associated with the video.",
                                    "items": {
                                        "type": "string",
                                        "description": "A single hashtag, including the # symbol.",
                                        "pattern": "^#\\w+$"
                                    }
                                }
                            },
                            "required": [
                                "title",
                                "caption",
                                "hashtags"
                            ],
                            "additionalProperties": False
                        }
                    }
                },
                temperature=0.8,
                max_tokens=500
            )
            
            # Parse the response
            content = response.choices[0].message.content
            metadata = json.loads(content)
            
            # Convert hashtags array to string for compatibility with existing code
            if isinstance(metadata.get('hashtags'), list):
                metadata['hashtags'] = ' '.join(metadata['hashtags'])
            
            # Validate metadata before sanitization
            if not metadata.get('title') or not metadata.get('title', '').strip():
                raise ValueError("AI returned empty title")
            
            original_title = metadata.get('title', '')
            
            # Sanitize metadata to remove emojis and problematic characters
            metadata = self._sanitize_metadata(metadata)
            
            # Check if sanitization broke the title
            if not metadata.get('title', '').strip():
                safe_print(f"[AI] WARNING: Sanitization removed entire title, using original")
                metadata['title'] = original_title.strip()
            
            # Validate final title doesn't look like fallback
            final_title = metadata.get('title', '').strip().lower()
            if 'epic gaming moment' in final_title and filename.lower() in final_title:
                safe_print(f"[AI] WARNING: Title looks like fallback: '{metadata.get('title')}'")
                safe_print(f"[AI] WARNING: This suggests AI generation may have failed")
            
            safe_print(f"[AI] AI generated metadata for {filename}")
            safe_print(f"   Title: {metadata.get('title', 'N/A')}")
            safe_print(f"   Caption: {metadata.get('caption', 'N/A')[:50]}...")
            safe_print(f"   Hashtags: {metadata.get('hashtags', 'N/A')}")
            
            return metadata
            
        except json.JSONDecodeError as e:
            print(f"[AI] ERROR: Failed to parse AI response as JSON: {e}")
            if 'response' in locals() and response.choices:
                print(f"[AI] Response content: {response.choices[0].message.content[:500]}")
            # Re-raise instead of using fallback so caller knows it failed
            raise ValueError(f"AI returned invalid JSON: {str(e)}") from e
        except Exception as e:
            print(f"[AI] ERROR: AI generation failed: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            # Re-raise so caller can handle appropriately
            raise
    
    def _create_prompt(self, filename: str, game_context: str) -> str:
        """Create a prompt for AI metadata generation."""
        if "armagetron" in game_context.lower() or "tron" in game_context.lower():
            return f"""You are a social media strategist. It needs to be super hype. It needs to be super gen z,
no capitals, kinda dry, sarcastic, but full of bait and alpha.
Skull emojis and wilting flower emojis are your favorite emojis. add them at the end either 2 or 3 of any
In this video, we beat someone at a game. Embarassed them. Make it clickbait. 

The game is armagetron advanced. It's a tron clone lightcycle snake game. Highly fast reactions and predictions. Infinite skill ceiling. Hashtags should be very short and generic 
retrocycles, satisfying, tron, max 4.

include an emoji in the title

DO NOT include the filename in the title. Create a creative title based on the gameplay.
The filename "{filename}" is only for context - do not reference it in the title or caption."""
        else:
            return f"""You are a social media strategist. It needs to be super hype. It needs to be super gen z,
no capitals, kinda dry, sarcastic, but full of bait and alpha.
Skull emojis and wilting flower emojis are your favorite emojis. add them at the end either 2 or 3 of any
In this video, we beat someone at a game. Embarassed them. Make it clickbait.

Create an engaging, short title and caption for a 30-second gaming or reaction clip.
DO NOT include the filename or file extension in the title. Create a creative, unique title based on the gaming content.
The filename "{filename}" is only provided for context - do not use it in your response.

Output JSON with keys: title, caption, hashtags."""
    
    def _sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Remove emojis and problematic characters from metadata."""
        import re
        
        sanitized = {}
        for key, value in metadata.items():
            if isinstance(value, str):
                # Only remove emojis, keep other Unicode (like accents, etc)
                # This regex removes emoji ranges but keeps basic Unicode text
                sanitized_value = re.sub(
                    r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U000024C2-\U0001F251]+',
                    '',
                    value
                ).strip()
                
                # If sanitization removed everything, keep original
                if not sanitized_value and value:
                    safe_print(f"[AI] WARNING: Sanitization removed all content for {key}, keeping original")
                    sanitized_value = value.strip()
                
                sanitized[key] = sanitized_value
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _get_fallback_metadata(self, filename: str) -> Dict[str, Any]:
        """Get fallback metadata when AI generation fails."""
        # Clean filename - remove extension and convert underscores to spaces
        clean_name = filename.replace('.mp4', '').replace('.mkv', '').replace('.flv', '').replace('.avi', '').replace('.mov', '')
        clean_name = clean_name.replace('_', ' ').title()
        
        # Use cleaned filename without the generic "epic gaming moment" prefix
        return {
            "title": f"{clean_name} 🎮",
            "caption": "check out this insane play! we totally owned them 💀🥀",
            "hashtags": "#gaming #shorts #epic #clutch"
        }
    
    def generate_metadata_for_game(self, filename: str, game_name: str) -> Dict[str, Any]:
        """Generate metadata with specific game context."""
        return self.generate_metadata(filename, game_name)
    
    def check_quota(self) -> Optional[Dict[str, Any]]:
        """
        Check user's quota status (backend API only).
        
        Returns:
            Quota information dictionary or None if not using backend
        """
        if self.api_client:
            try:
                return self.api_client.check_quota()
            except Exception as e:
                print(f"⚠️  Failed to check quota: {e}")
                return None
        return None