#!/usr/bin/env python3
"""
Test script for language detection functionality
"""

import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ''))

from app.pipelines.layer1_sanitization import SanitizationLayer
from app.pipelines.base import PipelineContext, PipelineResult
import asyncio
import json


async def test_language_validation():
    """Test language detection and validation"""
    
    sanitizer = SanitizationLayer()
    
    # Test cases: [prompt, expected_language, should_pass]
    test_cases = [
        # Should pass - Indonesian
        ("Saya ingin meningkatkan kebiasaan sholat tahajud", "id", True),
        
        # Should pass - English  
        ("I want to improve my daily prayer habits", "en", True),
        
        # Should fail - French (not supported) - using common words to avoid random detection
        ("Bonjour, je veux améliorer ma vie spirituelle avec la prière", "fr", False),
        
        # Should fail - Spanish (not supported) - using common words  
        ("Hola, quiero mejorar mi vida espiritual con la oración", "es", False),
        
        # Should fail - Random gibberish
        ("fkjali3 lkasdf laiues", None, False),
    ]
    
    print("Language Detection and Validation Tests")
    print("=" * 60)
    
    for i, (prompt, expected_lang, should_pass) in enumerate(test_cases, 1):
        print(f"\nTest {i}: {prompt}")
        print("-" * 40)
        
        # Create context
        context = PipelineContext(
            raw_input=prompt,
            language="id"  # Default language in request
        )
        
        # Test sanitization layer
        result = await sanitizer.process(context)
        
        passed = result.status == "passed"
        detected_lang = getattr(context, 'detected_language', None)
        
        print(f"Expected to pass: {should_pass}")
        print(f"Actually passed: {passed}")
        print(f"Expected language: {expected_lang}")
        print(f"Detected language: {detected_lang}")
        
        if result.status == "rejected":
            print(f"Rejection reason: {result.error_code}")
            print(f"Message (ID): {result.message_id}")
            print(f"Message (EN): {result.message_en}")
        
        # Check if test passed as expected
        test_passed = (passed == should_pass)
        print(f"Test result: {'✅ PASS' if test_passed else '❌ FAIL'}")
        
        if not test_passed:
            print(f"❗ Expected pass={should_pass}, got pass={passed}")
    
    print(f"\n{'='*60}")
    print("All tests completed!")


if __name__ == "__main__":
    asyncio.run(test_language_validation())