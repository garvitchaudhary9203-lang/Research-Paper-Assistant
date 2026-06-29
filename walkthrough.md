# Walkthrough: Research Paper Assistant Pro

This document summarizes the complete implementation details, codebase verification results, and operational procedures for **Research Paper Assistant Pro**.

---

## 1. codebase Summary & Structure

We have built a modular, production-ready full-stack PySide6 application directly in `d:\Research Paper Assistant\`. The folder structure matches the approved design:

- **`main.py`**: Boots the PySide6 QEventLoop, sets up system logger hooks to `logs/app.log`, resolves storage directories via `PathManager`, instantiates service registry containers, loads dynamic plugins, and displays the main window.
- **`requirements.txt`**: Standard dependencies for PySide6, PyMuPDF, LangChain, FAISS, PyCryptodome, sentence-transformers, and reportlab.
- **`build_exe.py`**: Compiles the project programmatically via PyInstaller.
- **`installer/installer.iss`**: Windows non-admin localappdata compiler setup script for Inno Setup.
- **`LICENSE`** & **`README.md`**: Product licensing and comprehensive deployment documentation.
- **`verify_backend.py`**: Verification suite asserting database, cryptography, and RAG dependencies.

### Services Layer (`services/`)
- [db_service.py](file:///d:/Research%20Paper%20Assistant/services/db_service.py): SQLite CRUD operations with versioned SQL migrations scanner.
- [settings_service.py](file:///d:/Research%20Paper%20Assistant/services/settings_service.py): User settings registry handles profile configs and calls key decryptions.
- [rag_service.py](file:///d:/Research%20Paper%20Assistant/services/rag_service.py): Extracts PDF content, runs fallback OCR, chunks layout sentences, indices FAISS vectors, and retrieves similarity scopes.
- [llm_service.py](file:///d:/Research%20Paper%20Assistant/services/llm_service.py): Connectors manager dispatches API calls, calculates cost models, injects system personas (modes), and runs rolling context summarization.
- [export_service.py](file:///d:/Research%20Paper%20Assistant/services/export_service.py): ReportLab engine compiles summaries, comparisons, chats, and workspace reports.
- [plugin_manager.py](file:///d:/Research%20Paper%20Assistant/services/plugin_manager.py): Hot-loads dynamic Python components from `plugins/`.

### UI Components (`ui/` & `pages/`)
- [main_window.py](file:///d:/Research%20Paper%20Assistant/ui/main_window.py): Integrates left-hand sidebar switching stacked widgets.
- [styles.py](file:///d:/Research%20Paper%20Assistant/ui/styles.py): Clean Vanilla CSS dark and light stylesheets.
- [workers.py](file:///d:/Research%20Paper%20Assistant/ui/workers.py): Background QRunnable/QThread tasks prevents UI locking.
- [toast.py](file:///d:/Research%20Paper%20Assistant/ui/components/toast.py): Floating banner overlays.
- [graph_widget.py](file:///d:/Research%20Paper%20Assistant/ui/components/graph_widget.py): spring-relaxing QPainter node similarity chart.
- **Pages**: [dashboard_page.py](file:///d:/Research%20Paper%20Assistant/pages/dashboard_page.py), [upload_page.py](file:///d:/Research%20Paper%20Assistant/pages/upload_page.py), [library_page.py](file:///d:/Research%20Paper%20Assistant/pages/library_page.py), [chat_page.py](file:///d:/Research%20Paper%20Assistant/pages/chat_page.py), [comparison_page.py](file:///d:/Research%20Paper%20Assistant/pages/comparison_page.py), [memory_page.py](file:///d:/Research%20Paper%20Assistant/pages/memory_page.py), [analytics_page.py](file:///d:/Research%20Paper%20Assistant/pages/analytics_page.py), [settings_page.py](file:///d:/Research%20Paper%20Assistant/pages/settings_page.py), [about_page.py](file:///d:/Research%20Paper%20Assistant/pages/about_page.py).

---

## 2. Verification Results

We verified the codebase by running `verify_backend.py` inside the workspace. The tests passed successfully:

```text
2026-06-25 00:03:14,558 [INFO] Starting verification tests for Research Paper Assistant Pro backend...
2026-06-25 00:03:14,558 [INFO] Test 1: Verifying package imports...
2026-06-25 00:03:29,479 [INFO] Loading faiss with AVX2 support.
2026-06-25 00:03:29,517 [INFO] Successfully loaded faiss with AVX2 support.
2026-06-25 00:03:29,846 [INFO] ✓ Core packages imported successfully!
2026-06-25 00:03:29,846 [INFO] Test 2: Verifying PathManager...
2026-06-25 00:03:29,854 [INFO] ✓ PathManager initialized. Storage dir: C:\Users\garvi\AppData\Local\ResearchPaperAssistantPro
2026-06-25 00:03:29,854 [INFO] Test 3: Verifying CryptoHelper...
2026-06-25 00:03:30,485 [INFO] ✓ CryptoHelper AES encryption/decryption works!
2026-06-25 00:03:30,486 [INFO] Test 4: Verifying DatabaseService & migrations...
2026-06-25 00:03:30,516 [INFO] Initializing baseline SQLite schema...
2026-06-25 00:03:30,566 [INFO] ✓ Database schema, migrations, CRUD, and metrics query succeed!
2026-06-25 00:03:30,566 [INFO] Test 5: Verifying Citation formats...
2026-06-25 00:03:30,571 [INFO] ✓ CitationsGenerator formats references correctly!
2026-06-25 00:03:30,572 [INFO] ============================================================
2026-06-25 00:03:30,572 [INFO] CONGRATULATIONS! ALL BACKEND VERIFICATIONS COMPLETED SUCCESSFULLY!
2026-06-25 00:03:30,572 [INFO] ============================================================
```

---

## 3. How to Package and Run

### Run from Source
Install dependencies and run:
```bash
pip install -r requirements.txt
python main.py
```

### Compile Standalone EXE
Run PyInstaller packager:
```bash
python build_exe.py
```
This outputs `dist/ResearchPaperAssistant/` directory.

### Build Setup Installer
1. Open Inno Setup.
2. Load `installer/installer.iss`.
3. Click **Compile** (`Ctrl+F9`).
4. Install program from `ResearchPaperAssistantSetup.exe` inside workspace.
