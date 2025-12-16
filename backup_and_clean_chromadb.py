"""
Backup and Clean ChromaDB Script
Respaldar la base de datos de documentos fiscales antes de limpiarla
"""
import shutil
from pathlib import Path
from datetime import datetime
import config
from loguru import logger

def backup_chromadb():
    """Backup ChromaDB folder before cleaning"""
    logger.info("Starting ChromaDB backup...")
    
    source = config.CHROMA_DIR
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path("chroma_db_backup")
    backup_dir.mkdir(exist_ok=True)
    
    backup_path = backup_dir / f"chroma_db_backup_{timestamp}"
    
    if source.exists():
        logger.info(f"Backing up {source} to {backup_path}")
        shutil.copytree(source, backup_path)
        logger.success(f"✅ Backup created: {backup_path}")
        
        # Get size
        size_mb = sum(f.stat().st_size for f in backup_path.rglob('*') if f.is_file()) / (1024 * 1024)
        logger.info(f"Backup size: {size_mb:.2f} MB")
        
        return backup_path
    else:
        logger.warning("ChromaDB directory does not exist, nothing to backup")
        return None

def clean_chromadb():
    """Remove ChromaDB collection (keep folder structure)"""
    logger.info("Cleaning ChromaDB...")
    
    import chromadb
    from chromadb.config import Settings
    
    try:
        client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
        
        # List collections
        collections = client.list_collections()
        logger.info(f"Found {len(collections)} collections")
        
        for collection in collections:
            logger.info(f"Deleting collection: {collection.name}")
            client.delete_collection(collection.name)
            logger.success(f"✅ Collection '{collection.name}' deleted")
        
        logger.success("✅ ChromaDB cleaned successfully")
        
    except Exception as e:
        logger.error(f"Error cleaning ChromaDB: {e}")
        raise

def main():
    """Main backup and clean process"""
    print("="*70)
    print("CHROMADB BACKUP & CLEAN SCRIPT")
    print("="*70)
    print()
    print("⚠️  WARNING: This will remove all fiscal documents from the vector database")
    print("⚠️  A backup will be created in chroma_db_backup/ folder")
    print()
    
    response = input("Continue? (yes/no): ").strip().lower()
    
    if response != "yes":
        print("❌ Operation cancelled")
        return
    
    print()
    
    # Step 1: Backup
    backup_path = backup_chromadb()
    
    if backup_path:
        print()
        input("Press ENTER to continue with cleaning...")
        print()
        
        # Step 2: Clean
        clean_chromadb()
        
        print()
        print("="*70)
        print("✅ BACKUP & CLEAN COMPLETED")
        print("="*70)
        print(f"📁 Backup location: {backup_path}")
        print()
        print("Next steps:")
        print("1. Test the system without RAG")
        print("2. If needed, restore from backup")
        print()
    else:
        print("❌ No backup created, cleaning aborted")

if __name__ == "__main__":
    main()
