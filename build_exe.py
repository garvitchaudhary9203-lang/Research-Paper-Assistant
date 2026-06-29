import os
import sys
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("build")

def run_pyinstaller_build() -> None:
    """Invokes PyInstaller with appropriate flags for PySide6, FAISS, and transformers."""
    logger.info("Initializing PyInstaller build process...")
    
    app_dir = os.path.dirname(os.path.abspath(__file__))
    entry_point = os.path.join(app_dir, "main.py")
    
    if not os.path.exists(entry_point):
        logger.error(f"Entry script {entry_point} not found. Cannot build.")
        sys.exit(1)

    # Standard windows path separator is semicolon
    separator = ";"
    
    # 1. Construct command list
    cmd = [
        "pyinstaller",
        "--clean",
        "--name=ResearchPaperAssistant",
        "--noconsole",
        "--onedir",
        # Bundle migrations folder inside executable
        f"--add-data={os.path.join('database', 'migrations')}{separator}{os.path.join('database', 'migrations')}",
        # Hidden imports for PyInstaller to capture dynamically loaded RAG/Embedding packages
        "--hidden-import=sentence_transformers",
        "--hidden-import=faiss",
        "--hidden-import=fitz",
        "--hidden-import=Crypto",
        "--hidden-import=Crypto.Cipher.AES",
        "--hidden-import=Crypto.Util.Padding",
        "--hidden-import=reportlab",
        "--hidden-import=reportlab.lib.pagesizes",
        "--hidden-import=reportlab.platypus",
        "--hidden-import=reportlab.lib.styles",
        "--hidden-import=PySide6",
        "--hidden-import=PySide6.QtCore",
        "--hidden-import=PySide6.QtWidgets",
        "--hidden-import=PySide6.QtGui",
        # Target main.py
        entry_point
    ]
    
    logger.info(f"Executing command: {' '.join(cmd)}")
    
    try:
        # Run PyInstaller shell command
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info("PyInstaller compilation completed successfully!")
        logger.info(result.stdout[-1000:]) # Log final output block
    except subprocess.CalledProcessError as e:
        logger.error("PyInstaller compilation failed!")
        logger.error(e.stderr)
        sys.exit(1)

if __name__ == "__main__":
    run_pyinstaller_build()
