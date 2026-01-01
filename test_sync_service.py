#!/usr/bin/env python3
"""
Sync Service Test
Tests the sync service functionality.
"""

import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ''))

from app.services.sync_service import SyncService
from app.services.postgres_service import PostgresService
from app.services.chromadb_service import ChromaDBService


async def test_postgres_connection():
    """Test PostgreSQL connection."""
    print("\n📊 Testing PostgreSQL Connection")
    print("-" * 50)
    
    try:
        pg_service = PostgresService()
        await pg_service.connect()
        
        # Try to fetch knowledge references
        references = await pg_service.fetch_knowledge_references()
        print(f"✅ Connected to PostgreSQL")
        print(f"📚 Found {len(references)} knowledge references")
        
        # Try to fetch journey templates
        templates = await pg_service.fetch_journey_templates()
        print(f"📝 Found {len(templates)} journey templates")
        
        await pg_service.disconnect()
        return True
        
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {str(e)}")
        return False


async def test_chromadb_connection():
    """Test ChromaDB connection."""
    print("\n🔍 Testing ChromaDB Connection")
    print("-" * 50)
    
    try:
        chroma_service = ChromaDBService()
        await chroma_service.connect()
        
        stats = await chroma_service.get_collection_stats()
        print(f"✅ Connected to ChromaDB")
        print(f"📚 Knowledge references: {stats['knowledge_references']['count']}")
        print(f"📝 Journey templates: {stats['journey_templates']['count']}")
        
        await chroma_service.disconnect()
        return True
        
    except Exception as e:
        print(f"❌ ChromaDB connection failed: {str(e)}")
        return False


async def test_sync_service():
    """Test sync service."""
    print("\n🔄 Testing Sync Service")
    print("-" * 50)
    
    try:
        sync_service = SyncService()
        
        print("Running incremental sync...")
        stats = await sync_service.sync_all(force_full_sync=False)
        
        print(f"✅ Sync completed")
        print(f"  Knowledge references synced: {stats['knowledge_references_synced']}")
        print(f"  Journey templates synced: {stats['journey_templates_synced']}")
        print(f"  Errors: {stats['errors']}")
        print(f"  Duration: {stats['duration_seconds']:.2f}s")
        
        return True
        
    except Exception as e:
        print(f"❌ Sync service test failed: {str(e)}")
        return False


async def main():
    """Run all tests."""
    print("\n" + "="*50)
    print("🧪 Hala AI Sync Service Tests")
    print("="*50)
    
    results = []
    
    # Test PostgreSQL
    results.append(("PostgreSQL", await test_postgres_connection()))
    
    # Test ChromaDB
    results.append(("ChromaDB", await test_chromadb_connection()))
    
    # Test Sync Service
    results.append(("Sync Service", await test_sync_service()))
    
    # Summary
    print("\n" + "="*50)
    print("📋 Test Summary")
    print("="*50)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:.<30} {status}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n✅ All tests passed!")
        exit(0)
    else:
        print("\n❌ Some tests failed")
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
