import sys
# Shiboken PySide6 / six.moves import hook crash workaround
try:
    import six
    import six.moves
except ImportError:
    pass

import os
import logging

# Configure basic logging to terminal
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("verify")

def run_tests() -> bool:
    logger.info("Starting verification tests for Research Paper Assistant Pro backend...")
    
    # Test 1: Verify Core Package Imports
    logger.info("Test 1: Verifying package imports...")
    try:
        import sentence_transformers
        import langchain
        import langchain_community
        import faiss
        import fitz  # PyMuPDF
        import reportlab
        import Crypto  # PyCryptodome
        import requests
        import PySide6
        logger.info("✓ Core packages imported successfully!")
    except ImportError as e:
        logger.error(f"✗ Import check failed: {e}")
        logger.error("Please run: pip install -r requirements.txt")
        return False

    # Test 2: Verify PathManager & Portable Mode
    logger.info("Test 2: Verifying PathManager...")
    try:
        from utils.path_manager import PathManager
        PathManager.initialize()
        
        # Test folder creation
        temp_logs = PathManager.get_path("logs")
        temp_db = PathManager.get_path("database")
        
        assert os.path.exists(temp_logs)
        assert os.path.exists(temp_db)
        logger.info(f"✓ PathManager initialized. Storage dir: {PathManager.get_base_data_dir()}")
    except Exception as e:
        logger.error(f"✗ PathManager failed: {e}")
        return False

    # Test 3: Verify Encryption / Decryption Vault
    logger.info("Test 3: Verifying CryptoHelper...")
    try:
        from utils.crypto_helper import CryptoHelper
        secret = "test_api_key_12345_xyz"
        encrypted = CryptoHelper.encrypt(secret)
        decrypted = CryptoHelper.decrypt(encrypted)
        
        assert secret == decrypted, "Decrypted value does not match original plaintext!"
        logger.info("✓ CryptoHelper AES encryption/decryption works!")
    except Exception as e:
        logger.error(f"✗ CryptoHelper failed: {e}")
        return False

    # Test 4: Verify Database schema & Migrations
    logger.info("Test 4: Verifying DatabaseService & migrations...")
    try:
        from services.db_service import DatabaseService
        db_dir = PathManager.get_path("database")
        db = DatabaseService(db_dir)
        
        # Create test profile
        username = "Test Researcher"
        user = db.create_user(username)
        assert user["id"] is not None
        assert user["username"] == username
        
        # Create project workspace
        proj = db.create_project(user["id"], "Test Project", "Project description")
        assert proj["id"] is not None
        assert proj["name"] == "Test Project"
        
        # Log mock API calls
        db.log_api_usage(user["id"], "openai", "gpt-4o-mini", 100, 50, 0.00015)
        metrics = db.get_api_usage_metrics(user["id"])
        
        assert metrics["total_requests"] == 1
        assert metrics["total_cost"] > 0.0
        
        # Cleanup test profile
        db.delete_user(user["id"])
        db.close()
        logger.info("✓ Database schema, migrations, CRUD, and metrics query succeed!")
    except Exception as e:
        logger.error(f"✗ DatabaseService failed: {e}")
        return False

    # Test 5: Verify Citation Formatting Rules
    logger.info("Test 5: Verifying Citation formats...")
    try:
        from utils.citations import CitationsGenerator
        mock_meta = {
            "title": "Attention Is All You Need",
            "authors": "Ashish Vaswani, Noam Shazeer, Niki Parmar",
            "pub_year": 2017,
            "doi": "10.48550/arXiv.1706.03762"
        }
        apa = CitationsGenerator.to_apa(mock_meta)
        assert "Vaswani, et al." in apa or "Vaswani" in apa
        assert "2017" in apa
        assert "Attention Is All You Need" in apa
        logger.info("✓ CitationsGenerator formats references correctly!")
    except Exception as e:
        logger.error(f"✗ CitationsGenerator failed: {e}")
        return False

    logger.info("=" * 60)
    logger.info("CONGRATULATIONS! ALL BACKEND VERIFICATIONS COMPLETED SUCCESSFULLY!")
    logger.info("=" * 60)
    return True

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
