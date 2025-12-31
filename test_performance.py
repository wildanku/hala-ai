#!/usr/bin/env python3
"""
Performance test for optimized validation endpoint
"""

import asyncio
import time
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ''))

async def test_validation_performance():
    """Test validation performance with optimizations"""
    
    from app.services.embedding_service import EmbeddingService
    from app.pipelines.layer1_sanitization import SanitizationLayer
    from app.pipelines.layer2_semantic import SemanticValidationLayer
    from app.pipelines.base import PipelineContext
    
    test_prompt = "amalan supaya rezeki lancar"
    
    print("🚀 Testing Validation Performance Optimizations")
    print("=" * 60)
    
    # Test 1: Sanitization only (fast mode)
    print("\n📋 Test 1: Sanitization Only (Fast Mode)")
    start_time = time.perf_counter()
    
    context = PipelineContext(raw_input=test_prompt, language="id")
    layer1 = SanitizationLayer()
    result1 = await layer1.process(context)
    
    sanitization_time = (time.perf_counter() - start_time) * 1000
    print(f"⚡ Sanitization time: {sanitization_time:.2f}ms")
    print(f"✅ Result: {result1.status}")
    print(f"🌍 Detected language: {getattr(context, 'detected_language', 'N/A')}")
    
    # Test 2: Full validation (first time - with model loading)
    print("\n🧠 Test 2: Full Validation (First Time)")
    start_time = time.perf_counter()
    
    # Fresh context
    context = PipelineContext(raw_input=test_prompt, language="id")
    
    # Sanitization
    layer1 = SanitizationLayer()
    await layer1.process(context)
    
    # Embedding service initialization
    embedding_service = EmbeddingService()
    await embedding_service.initialize()
    
    # Semantic validation
    layer2 = SemanticValidationLayer()
    layer2.set_embedding_service(embedding_service)
    result2 = await layer2.process(context)
    
    full_time_first = (time.perf_counter() - start_time) * 1000
    print(f"🔥 Full validation (1st): {full_time_first:.2f}ms")
    print(f"✅ Result: {result2.status}")
    print(f"🎯 Detected scope: {getattr(context, 'detected_scope', 'N/A')}")
    print(f"📊 Confidence: {list(context.semantic_scores.values())[0]:.3f}" if context.semantic_scores else "N/A")
    
    # Test 3: Full validation (second time - cached)
    print("\n⚡ Test 3: Full Validation (Second Time - Cached)")
    start_time = time.perf_counter()
    
    # Fresh context
    context = PipelineContext(raw_input=test_prompt, language="id")
    
    # Sanitization
    layer1 = SanitizationLayer()
    await layer1.process(context)
    
    # Embedding service (should be initialized already)
    embedding_service = EmbeddingService()
    await embedding_service.initialize()
    
    # Semantic validation (should use cached embeddings)
    layer2 = SemanticValidationLayer()
    layer2.set_embedding_service(embedding_service)
    result3 = await layer2.process(context)
    
    full_time_cached = (time.perf_counter() - start_time) * 1000
    print(f"⚡ Full validation (2nd): {full_time_cached:.2f}ms")
    print(f"✅ Result: {result3.status}")
    print(f"🎯 Detected scope: {getattr(context, 'detected_scope', 'N/A')}")
    
    # Summary
    print("\n📈 Performance Summary")
    print("=" * 40)
    print(f"Fast mode (sanitization only):  {sanitization_time:.2f}ms")
    print(f"Full mode (first time):         {full_time_first:.2f}ms")
    print(f"Full mode (cached):             {full_time_cached:.2f}ms")
    print(f"Speed improvement (cached):     {(full_time_first/full_time_cached):.1f}x faster")
    print(f"Fast vs Full (cached):          {(full_time_cached/sanitization_time):.1f}x slower")
    
    print("\n💡 Recommendations:")
    print("- Use fast mode (?fast=true) for real-time typing validation")
    print("- Use full mode for final submission validation")
    print("- First request will be slower, subsequent requests much faster")


if __name__ == "__main__":
    asyncio.run(test_validation_performance())