#!/usr/bin/env python3
"""
Quick test for Gemini API configuration
"""

import os
import asyncio
from app.core.config import settings
from app.providers.gemini import GeminiProvider


async def test_gemini():
    """Test Gemini API configuration and basic functionality."""
    
    print("🧪 Testing Gemini API Configuration")
    print("=" * 50)
    
    # Check environment
    print(f"📁 Working directory: {os.getcwd()}")
    print(f"🔧 Model name from settings: {settings.gemini_model_name}")
    print(f"🔑 API key present: {bool(settings.gemini_api_key)}")
    if settings.gemini_api_key:
        print(f"🔑 API key preview: {settings.gemini_api_key[:10]}...")
    print()
    
    # Test provider initialization
    print("🚀 Initializing Gemini provider...")
    provider = GeminiProvider()
    print(f"✅ Provider model: {provider.model_name}")
    print()
    
    # Test health check
    print("🏥 Testing API health check...")
    try:
        is_healthy = await provider.health_check()
        if is_healthy:
            print("✅ Gemini API is healthy!")
        else:
            print("❌ Gemini API health check failed")
            return
    except Exception as e:
        print(f"❌ Health check error: {str(e)}")
        return
    
    print()
    
    # Test simple generation
    print("💬 Testing simple text generation...")
    try:
        result = await provider.generate(
            system_prompt="You are a helpful assistant. Respond briefly.",
            user_message="Say 'Hello from Gemini!' in Indonesian and English",
            response_format="text",
            temperature=0.1,
        )
        print(f"✅ Response: {result.get('content', 'No content')[:100]}...")
        print()
        
    except Exception as e:
        print(f"❌ Generation error: {str(e)}")
        print()
        
        # Check if it's a quota error
        if "quota" in str(e).lower():
            print("💡 Tips for quota issues:")
            print("   - Wait a few minutes and try again")
            print("   - Check your Gemini API billing at: https://ai.dev/usage")
            print("   - Consider switching to gemini-1.5-flash-8b for higher free limits")
            print("   - Verify your API key at: https://ai.google.dev/")
        
        return
    
    print("🎉 All tests passed!")


if __name__ == "__main__":
    asyncio.run(test_gemini())