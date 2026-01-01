#!/usr/bin/env python3
"""
List available Gemini models
"""

import asyncio
from app.core.config import settings


async def list_gemini_models():
    """List available Gemini models."""
    
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.gemini_api_key)
        
        print("🔍 Available Gemini models:")
        print("=" * 40)
        
        models = genai.list_models()
        for model in models:
            if 'generateContent' in model.supported_generation_methods:
                print(f"✅ {model.name}")
                
    except Exception as e:
        print(f"❌ Error listing models: {str(e)}")


if __name__ == "__main__":
    asyncio.run(list_gemini_models())