#!/usr/bin/env python3
"""
Test the journey generation endpoint
"""

import asyncio
import json
from app.api.v1.schemas.journey import JourneyRequest
from app.api.v1.endpoints.journey import generate_journey


async def test_journey_generation():
    """Test the journey generation endpoint."""
    
    print("🧪 Testing Journey Generation")
    print("=" * 50)
    
    # Create a test request
    request = JourneyRequest(
        prompt="Saya ingin meningkatkan kebiasaan sholat tahajud dan merasa lebih dekat dengan Allah",
        language="id",
        user_id="test-user-123",
        session_id="test-session-456"
    )
    
    print(f"📝 Test prompt: {request.prompt}")
    print(f"🌐 Language: {request.language}")
    print()
    
    try:
        print("🚀 Generating journey...")
        result = await generate_journey(request)
        
        print("✅ Journey generated successfully!")
        print(f"📊 Status: {result.get('status')}")
        
        # Print raw result for debugging
        print("🔍 Raw result:")
        print(json.dumps(result, indent=2, ensure_ascii=False)[:1000] + "...")
        print()
        # Show metadata
        meta = result.get('meta', {})
        print(f"⚡ Total time: {meta.get('total_time_ms', 0):.1f}ms")
        print(f"📚 Documents retrieved: {meta.get('documents_retrieved', 0)}")
        print(f"🤖 LLM Provider: {meta.get('llm_provider')}")
        print(f"🎯 Template used: {meta.get('template_used', False)}")
        
        # Show journey data
        data = result.get('data', {})
        if data:
            print(f"🎯 Goal: {data.get('goal', 'N/A')}")
            print(f"📅 Total days: {data.get('total_days', 'N/A')}")
            print(f"🏷️ Goal keyword: {data.get('goal_keyword', 'N/A')}")
            print(f"🔖 Tags: {', '.join(data.get('tags', []))}")
            
            journey_tasks = data.get('journey', [])
            print(f"📋 Journey tasks: {len(journey_tasks)}")
            
            # Show first few tasks
            for i, task in enumerate(journey_tasks[:3]):
                day = task.get('day', 'N/A')
                task_type = task.get('type', 'N/A')
                time = task.get('time', 'N/A')
                title = task.get('title', {})
                title_text = title.get('id', title.get('en', 'N/A')) if isinstance(title, dict) else str(title)
                print(f"   Day {day} ({task_type}, {time}): {title_text}")
                
            if len(journey_tasks) > 3:
                print(f"   ... and {len(journey_tasks) - 3} more tasks")
        
        print()
        print("🎉 Journey generation test passed!")
        
    except Exception as e:
        print(f"❌ Journey generation failed: {str(e)}")
        print()
        
        # Check for specific error types
        error_str = str(e)
        if "quota" in error_str.lower():
            print("💡 This is a quota error. Try:")
            print("   - Wait a few minutes and try again")
            print("   - Check your API usage at https://ai.dev/usage")
            print("   - Consider upgrading your Gemini plan")
        elif "authentication" in error_str.lower():
            print("💡 This is an authentication error. Check your API key.")
        elif "out_of_scope" in error_str.lower():
            print("💡 This prompt was detected as out of scope.")
        else:
            print("💡 This is an unexpected error. Check logs for details.")


if __name__ == "__main__":
    asyncio.run(test_journey_generation())