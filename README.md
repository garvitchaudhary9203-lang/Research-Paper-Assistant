# Research Paper Assistant Pro

Research Paper Assistant Pro is a production-ready desktop application built for researchers, students, and academics. It leverages Retrieval-Augmented Generation (RAG) to index, analyze, search, compare, and synthesize scientific papers across multiple research projects.

The application operates completely offline for document chunking, indexing, and semantic search (using a local FAISS database and `sentence-transformers` embeddings) and communicates with multiple cloud AI providers (or local Ollama servers) for generating chats and comparison reports.

---

## Key Features

1. **Multi-User Profiles**: Maintain isolated document library collections, chat logs, API credentials, and preferences for multiple researchers on the same physical device.
2. **Project Workspaces**: Group papers, conversations, and comparative matrices under distinct workspaces (e.g., "Deep Learning", "Cybersecurity").
3. **Global Semantic Search**: Query the local vector database using natural language to search matching text passages across all papers in the active project.
4. **Duplicate Detection**: Guards library integrity by checking MD5 file hashes, title similarities, and DOI matches upon document uploads.
5. **Interactive Similarity Graph**: Renders a spring-embedded 2D network diagram visualizing structural similarities of papers in the workspace.
6. **Encrypted Credentials**: Local API keys are encrypted via AES-CBC using keys dynamically derived from hardware signatures.
7. **ReportLab PDF Exports**: Export high-fidelity PDF documents of conversation logs, comparison charts, individual executive summaries, and workspace-wide research reports.
8. **Specialized Assistant Modes**: Chat with papers using tailored personas (General Research, Paper Reviewer, Literature Reviewer, Thesis Coach, or Comparison Expert).
9. **Memory Compression**: Implements rolling conversation summarization to compress early messages, reducing token costs while retaining memory of old threads.
10. **Offline Mode**: Operates fully offline when connected to local Ollama servers, skipping all external checks.

---

## Technical Stack

- **UI Framework**: PySide6 (Qt for Python)
- **Vector Database**: FAISS (Facebook AI Similarity Search)
- **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` (with support for BGE and E5 models)
- **Metadata Database**: SQLite3 (with schema migration system)
- **PDF Extraction**: PyMuPDF (fitz) with `pytesseract` OCR fallbacks
- **Report Exports**: ReportLab (PDF) and Python `csv` (Analytics)
- **Packaging**: PyInstaller & Inno Setup

---

## Installation & Setup

### Prerequisites
- Python 3.9 - 3.11 (Required for compiling from source)
- Tesseract OCR (Optional, required if you need scanned PDF OCR support)

### Run from Source
1. Clone the project repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the bootstrap entry script:
   ```bash
   python main.py
   ```

---

## Standalone Building Guide

To compile a downloadable, double-clickable installer for non-technical users without needing Python, follow these steps:

### Step 1: Compile the Executable (PyInstaller)
Run the programmatic build script in the project directory:
```bash
python build_exe.py
```
This command compiles the application into a single folder containing `ResearchPaperAssistant.exe` and its shared dynamic libraries under the `dist/ResearchPaperAssistant/` folder.

### Step 2: Build the Windows Installer (Inno Setup)
1. Download and install [Inno Setup](https://jrsoftware.org/isinfo.php).
2. Open Inno Setup Compiler.
3. Open the script `installer/installer.iss` located in the project folder.
4. Click **Compile** (or press `Ctrl+F9`).
5. The compiler will generate a single, unified installer file: `ResearchPaperAssistantSetup.exe` in the root folder.
6. Share `ResearchPaperAssistantSetup.exe` with users. They can double-click it to install and launch the app in one click.

---

## Provider Setup

Go to the **Settings** page in the application, select your profile, choose a provider, and enter credentials:

1. **OpenAI**: Input API Key. Click *Test Connection* to fetch models (e.g. `gpt-4o`, `gpt-4o-mini`).
2. **Google Gemini**: Input API Key. Click *Test Connection* to discover active models.
3. **Anthropic Claude**: Input API Key and select model.
4. **Groq**: Input API Key.
5. **OpenRouter**: Input API Key to browse any LLM.
6. **Ollama**: Verify local URL (defaults to `http://localhost:11434`). Click *Test Connection* to fetch local models running on your machine.

---

## Troubleshooting & FAQ

### The UI is freezing when uploading large PDFs
- Large files are processed in a background thread using `QRunnable` workers. If you experience lags, verify your system CPU load or check the logs at `logs/app.log` to confirm if background workers are operating normally.

### I get "No module named 'fitz'" when running python main.py
- PyMuPDF is imported as `fitz` in Python. Verify that `pymupdf` is correctly installed: `pip install pymupdf`.

### Where is my data stored?
- **Default Mode**: Data (SQLite, FAISS index, uploads, and settings) is stored in your user directory:
  `C:\Users\<Username>\AppData\Local\ResearchPaperAssistantPro\`
- **Portable Mode**: If enabled in Settings (or if a `portable.txt` file exists in the app root), all data is stored inside the application directory itself. You can move the folder to a USB drive or other computers without data loss.

### SQLite Database is locked
- Close any other SQLite browsers that might have opened `database/memory.db`. The application automatically unlocks databases on closures. Check `logs/app.log` for logs.
