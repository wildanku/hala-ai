#!/usr/bin/env python3
"""
Sync CLI
Command-line interface for running data sync operations.
Can be used as a cronjob.

Usage:
    python -m app.cli.sync --help
    python -m app.cli.sync full        # Full sync (clears ChromaDB first)
    python -m app.cli.sync incremental # Incremental sync (only new/updated)
    python -m app.cli.sync stats       # Show collection statistics
"""

import asyncio
import argparse
import json
import logging
from datetime import datetime

from app.services.sync_service import SyncService

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('./sync.log')
    ]
)
logger = logging.getLogger(__name__)


async def sync_full():
    """Run full synchronization (clears ChromaDB first)."""
    logger.info("Starting full synchronization...")
    
    sync_service = SyncService()
    
    try:
        stats = await sync_service.sync_all(force_full_sync=True)
        
        print("\n" + "="*50)
        print("✅ Full Synchronization Complete")
        print("="*50)
        print(json.dumps(stats, indent=2, default=str))
        
        return True
        
    except Exception as e:
        logger.error(f"Full sync failed: {str(e)}")
        print(f"\n❌ Full Synchronization Failed: {str(e)}")
        return False


async def sync_incremental():
    """Run incremental synchronization (only new/updated)."""
    logger.info("Starting incremental synchronization...")
    
    sync_service = SyncService()
    
    try:
        stats = await sync_service.sync_all(force_full_sync=False)
        
        print("\n" + "="*50)
        print("✅ Incremental Synchronization Complete")
        print("="*50)
        print(json.dumps(stats, indent=2, default=str))
        
        return True
        
    except Exception as e:
        logger.error(f"Incremental sync failed: {str(e)}")
        print(f"\n❌ Incremental Synchronization Failed: {str(e)}")
        return False


async def show_stats():
    """Show ChromaDB collection statistics."""
    from app.services.chromadb_service import ChromaDBService
    
    logger.info("Fetching ChromaDB statistics...")
    
    chroma_service = ChromaDBService()
    
    try:
        await chroma_service.connect()
        stats = await chroma_service.get_collection_stats()
        
        print("\n" + "="*50)
        print("📊 ChromaDB Collection Statistics")
        print("="*50)
        print(json.dumps(stats, indent=2))
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to fetch stats: {str(e)}")
        print(f"\n❌ Failed to fetch statistics: {str(e)}")
        return False
        
    finally:
        await chroma_service.disconnect()


async def sync_knowledge_reference(reference_id: str):
    """Sync a single knowledge reference."""
    logger.info(f"Syncing knowledge reference: {reference_id}")
    
    sync_service = SyncService()
    
    try:
        success = await sync_service.sync_knowledge_reference(reference_id)
        
        if success:
            print(f"\n✅ Knowledge reference {reference_id} synced successfully")
        else:
            print(f"\n❌ Failed to sync knowledge reference {reference_id}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error syncing knowledge reference: {str(e)}")
        print(f"\n❌ Error: {str(e)}")
        return False


async def sync_journey_template(template_id: str):
    """Sync a single journey template."""
    logger.info(f"Syncing journey template: {template_id}")
    
    sync_service = SyncService()
    
    try:
        success = await sync_service.sync_journey_template(template_id)
        
        if success:
            print(f"\n✅ Journey template {template_id} synced successfully")
        else:
            print(f"\n❌ Failed to sync journey template {template_id}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error syncing journey template: {str(e)}")
        print(f"\n❌ Error: {str(e)}")
        return False


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Hala AI Service - Data Sync CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m app.cli.sync full                    # Full sync
  python -m app.cli.sync incremental             # Incremental sync
  python -m app.cli.sync stats                   # Show statistics
  python -m app.cli.sync ref <reference_id>      # Sync single reference
  python -m app.cli.sync template <template_id>  # Sync single template
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Full sync command
    subparsers.add_parser("full", help="Full synchronization (clears ChromaDB first)")
    
    # Incremental sync command
    subparsers.add_parser("incremental", help="Incremental synchronization (only new/updated)")
    
    # Stats command
    subparsers.add_parser("stats", help="Show collection statistics")
    
    # Single reference sync
    ref_parser = subparsers.add_parser("ref", help="Sync single knowledge reference")
    ref_parser.add_argument("reference_id", help="Knowledge reference ID")
    
    # Single template sync
    template_parser = subparsers.add_parser("template", help="Sync single journey template")
    template_parser.add_argument("template_id", help="Journey template ID")
    
    args = parser.parse_args()
    
    # Handle commands
    if args.command == "full":
        success = asyncio.run(sync_full())
    elif args.command == "incremental":
        success = asyncio.run(sync_incremental())
    elif args.command == "stats":
        success = asyncio.run(show_stats())
    elif args.command == "ref":
        success = asyncio.run(sync_knowledge_reference(args.reference_id))
    elif args.command == "template":
        success = asyncio.run(sync_journey_template(args.template_id))
    else:
        parser.print_help()
        success = True
    
    # Exit with appropriate code
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
