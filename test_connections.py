#!/usr/bin/env python3
"""
Simple test to verify database connections without chromadb
"""
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test environment variables
print("=" * 60)
print("ENVIRONMENT VARIABLES")
print("=" * 60)

postgres_host = os.getenv("POSTGRES_HOST", "localhost")
postgres_port = os.getenv("POSTGRES_PORT", "5432")
postgres_user = os.getenv("POSTGRES_USER", "postgres")
postgres_password = os.getenv("POSTGRES_PASSWORD", "")
postgres_db = os.getenv("POSTGRES_DB", "hala-app")

print(f"PostgreSQL Host: {postgres_host}")
print(f"PostgreSQL Port: {postgres_port}")
print(f"PostgreSQL User: {postgres_user}")
print(f"PostgreSQL DB: {postgres_db}")

# Build connection string
postgres_url = f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}"
print(f"\nConnection String: {postgres_url}")

# Test PostgreSQL connection
print("\n" + "=" * 60)
print("TESTING POSTGRESQL CONNECTION")
print("=" * 60)

try:
    import asyncpg
    
    async def test_pg():
        try:
            # Test connection
            conn = await asyncpg.connect(
                host=postgres_host,
                port=int(postgres_port),
                user=postgres_user,
                password=postgres_password,
                database=postgres_db,
                timeout=5
            )
            
            # Test query
            version = await conn.fetchval('SELECT version();')
            print(f"✓ PostgreSQL Connection Successful!")
            print(f"  Version: {version}")
            
            await conn.close()
            return True
            
        except Exception as e:
            print(f"✗ PostgreSQL Connection Failed!")
            print(f"  Error: {type(e).__name__}: {str(e)}")
            return False
    
    result = asyncio.run(test_pg())
    
except ImportError:
    print("✗ asyncpg not installed")

# Test ChromaDB
print("\n" + "=" * 60)
print("TESTING CHROMADB")
print("=" * 60)

chroma_persist_dir = os.getenv("CHROMA_PERSIST_DIRECTORY", "./data/chromadb")
print(f"ChromaDB Persist Directory: {chroma_persist_dir}")

try:
    import chromadb
    
    # Create persistent client
    client = chromadb.PersistentClient(path=chroma_persist_dir)
    print(f"✓ ChromaDB Connection Successful!")
    print(f"  Persist Directory: {chroma_persist_dir}")
    
    # Check collections
    collections = client.list_collections()
    print(f"  Collections: {len(collections)} found")
    for col in collections:
        print(f"    - {col.name}: {col.count()} items")
    
except ImportError:
    print("✗ chromadb not installed")
except Exception as e:
    print(f"✗ ChromaDB Error!")
    print(f"  Error: {type(e).__name__}: {str(e)}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
