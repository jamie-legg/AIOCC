"""AI enrichment service using OpenAI."""

import json
from typing import Dict, Any
from openai import OpenAI
from ..config import settings


class AIService:
    """Handle AI-powered metadata generation."""
    
    def __init__(self):
        """Initialize OpenAI client."""
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = "gpt-4o-mini"
    
    def generate_metadata(self, filename: str, game_context: str = "gaming") -> Dict[str, Any]:
        """
        Generate social media metadata for a video file.
        
        Args:
            filename: Name of the video file
            game_context: Context about the game being played
            
        Returns:
            Dictionary containing title, caption, and hashtags
        """
        try:
            prompt = self._create_prompt(filename, game_context)
            
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
            
            content = response.choices[0].message.content
            metadata = json.loads(content)
            
            # Convert hashtags array to string for compatibility
            if isinstance(metadata.get('hashtags'), list):
                metadata['hashtags'] = ' '.join(metadata['hashtags'])
            
            return metadata
            
        except json.JSONDecodeError as e:
            print(f"[AI Service] ERROR: Failed to parse AI response as JSON: {e}")
            if 'response' in locals() and response.choices:
                print(f"[AI Service] Response content: {response.choices[0].message.content[:500]}")
            # Don't use fallback - raise error so it can be properly handled
            raise ValueError(f"AI returned invalid JSON: {str(e)}")
        except Exception as e:
            print(f"[AI Service] ERROR: AI generation failed: {type(e).__name__}: {e}")
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
    
    def _get_fallback_metadata(self, filename: str) -> Dict[str, Any]:
        """Get fallback metadata when AI generation fails."""
        # Use a more generic fallback that doesn't include the filename
        # Extract a clean name from filename if possible
        clean_name = filename.replace('.mp4', '').replace('.mkv', '').replace('_', ' ').title()
        return {
            "title": f"{clean_name} 🎮",
            "caption": "check out this insane play! we totally owned them 💀🥀",
            "hashtags": "#gaming #shorts #epic #clutch"
        }

