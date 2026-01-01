#!/usr/bin/env python3
"""
Test raw Gemini response to debug the journey output format
"""

import asyncio
import json
from app.providers.gemini import GeminiProvider


async def test_raw_gemini():
    """Test raw Gemini response."""
    
    prompt = """You are the "Hala Journal Planner" Engine. Create a 3-day spiritual journey.

RULES:
1. OUTPUT FORMAT: Strictly JSON only
2. Bilingual: Indonesian and English
3. Return exactly this structure:

{
  "goal": "User's goal text",
  "total_days": 3,
  "introduction": {
    "id": "Indonesian introduction",
    "en": "English introduction"
  },
  "goal_keyword": "spiritual-growth",
  "tags": ["spiritual", "prayer"],
  "journey": [
    {
      "day": "1",
      "type": "dhikr",
      "time": "morning",
      "title": {"id": "Dzikir Pagi", "en": "Morning Dhikr"},
      "description": {"id": "Baca tasbih 33x", "en": "Recite tasbih 33x"}
    }
  ]
}

USER: I want to improve my morning prayer routine"""
    
    provider = GeminiProvider()
    
    try:
        result = await provider.generate(
            system_prompt="You are an Islamic spiritual guide.",
            user_message=prompt,
            response_format="json",
            temperature=0.3,
        )
        
        print("🔍 Raw Gemini JSON response:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(test_raw_gemini())