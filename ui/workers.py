import os
import json
import logging
import datetime
from typing import List, Dict, Any, Optional
from PySide6.QtCore import QObject, Signal, QRunnable, QThread
from services.db_service import DatabaseService
from services.settings_service import SettingsService
from services.rag_service import RAGService
from services.llm_service import LLMService

logger = logging.getLogger("app")

class WorkerSignals(QObject):
    progress = Signal(int, str)       # progress percentage, status message
    finished = Signal(dict)           # result dictionary (e.g. metadata, pages)
    error = Signal(str)               # error message
    warning = Signal(str)             # warning message
    duplicate_found = Signal(str, str, str)  # filename, match_type, paper_id

# --- PDF Extraction Worker ---
class ExtractionWorker(QRunnable):
    def __init__(self, 
                 file_path: str, 
                 user_id: str, 
                 project_id: str,
                 db_service: DatabaseService, 
                 rag_service: RAGService,
                 llm_service: LLMService,
                 settings_service: SettingsService,
                 force_upload: bool = False):
        super().__init__()
        self.file_path = file_path
        self.user_id = user_id
        self.project_id = project_id
        self.db = db_service
        self.rag = rag_service
        self.llm = llm_service
        self.settings = settings_service
        self.force_upload = force_upload
        self.signals = WorkerSignals()

    def run(self) -> None:
        """Run PDF extraction, OCR fallback, and LLM metadata fallback in background thread."""
        try:
            filename = os.path.basename(self.file_path)
            self.signals.progress.emit(10, f"Analyzing {filename} for duplicates...")

            # 1. Compute file hash
            file_hash = self.rag.calculate_file_hash(self.file_path)

            # 2. Extract basic info first
            pages_content, total_pages, props = self.rag.extract_pdf_text_and_metadata(self.file_path)
            
            # Simple heuristic title extraction from first few lines if PDF title metadata is missing
            heur_title = props.get("title", "")
            if not heur_title and pages_content:
                first_page_text = pages_content[0]["text"].strip()
                lines = [l.strip() for l in first_page_text.split("\n") if l.strip()]
                if lines:
                    heur_title = lines[0][:150] # Take first line as heuristic title
            
            # Simple DOI extraction heuristic from first page text
            doi_pattern = r"10\.\d{4,9}/[-._;()/:A-Z0-9]+"
            import re
            heur_doi = ""
            if pages_content:
                match = re.search(doi_pattern, pages_content[0]["text"], re.IGNORECASE)
                if match:
                    heur_doi = match.group(0)

            # 3. Duplicate check
            if not self.force_upload:
                dup = self.db.check_duplicate_paper(self.project_id, file_hash, heur_title, heur_doi)
                if dup:
                    self.signals.duplicate_found.emit(filename, "Hash/Title/DOI Match", dup["id"])
                    return

            # 4. Extract complete text page by page
            self.signals.progress.emit(30, f"Extracting text from {total_pages} pages...")
            
            # 5. Metadata extraction with LLM Fallback if heuristics fail
            self.signals.progress.emit(60, "Inferring paper metadata (Title, Authors, Abstract, Year)...")
            
            title = heur_title
            authors = props.get("author", "Unknown")
            abstract = ""
            keywords = props.get("keywords", "")
            doi = heur_doi
            pub_year = None

            # Check if heuristics are insufficient
            needs_llm_fallback = not title or authors == "Unknown" or not abstract or not doi
            
            if needs_llm_fallback:
                # Compile first page text for LLM metadata extraction
                sample_text = pages_content[0]["text"][:1500] if pages_content else ""
                prompt = (
                    f"Analyze the following text from the first page of a research paper and extract its metadata in JSON format. "
                    f"Fields: 'title', 'authors', 'abstract', 'keywords', 'doi', 'publication_year'. "
                    f"If you cannot determine a field, output null or an empty string. Output ONLY valid raw JSON, no markdown code blocks.\n\n"
                    f"Text:\n{sample_text}"
                )
                try:
                    # Request metadata from LLM
                    # Pass empty history
                    res, _ = self.llm.generate(
                        user_id=self.user_id,
                        prompt=prompt,
                        context_chunks=[],
                        history=[],
                        custom_system_prompt="You are a JSON metadata extraction parser. Output raw JSON objects only."
                    )
                    # Clean markdown if returned
                    json_str = res.replace("```json", "").replace("```", "").strip()
                    meta_parsed = json.loads(json_str)
                    
                    title = meta_parsed.get("title") or title
                    authors = meta_parsed.get("authors") or authors
                    abstract = meta_parsed.get("abstract") or abstract
                    keywords = meta_parsed.get("keywords") or keywords
                    doi = meta_parsed.get("doi") or doi
                    pub_year = meta_parsed.get("publication_year") or pub_year
                    if pub_year:
                        try:
                            pub_year = int(pub_year)
                        except ValueError:
                            pub_year = None
                except Exception as err:
                    logger.warning(f"LLM metadata fallback failed: {err}. Using heuristics/meta details instead.")

            # Create paper record in DB (summary placeholder will be generated by another flow)
            self.signals.progress.emit(85, "Saving paper to database...")
            
            # Ensure year is default if None
            pub_year_val = pub_year if pub_year else datetime.datetime.now().year
            
            paper_rec = self.db.add_paper(
                user_id=self.user_id,
                project_id=self.project_id,
                name=filename,
                file_path=self.file_path,
                title=title if title else filename,
                authors=authors,
                abstract=abstract,
                keywords=keywords,
                doi=doi,
                pub_year=pub_year_val,
                pages=total_pages,
                file_hash=file_hash
            )

            result = {
                "paper": paper_rec,
                "pages_content": pages_content
            }
            self.signals.progress.emit(100, "Extraction completed successfully!")
            self.signals.finished.emit(result)
            
        except Exception as e:
            logger.error(f"Extraction worker error: {e}")
            self.signals.error.emit(str(e))

# --- Vector Indexing Worker ---
class IndexingWorker(QRunnable):
    def __init__(self, 
                 paper: Dict[str, Any], 
                 pages_content: List[Dict[str, Any]], 
                 embedding_model: str,
                 rag_service: RAGService,
                 db_service: DatabaseService,
                 llm_service: LLMService):
        super().__init__()
        self.paper = paper
        self.pages_content = pages_content
        self.embedding_model = embedding_model
        self.rag = rag_service
        self.db = db_service
        self.llm = llm_service
        self.signals = WorkerSignals()

    def run(self) -> None:
        """Run text chunking, embedding generation, and FAISS indexing, plus generate paper Summary."""
        try:
            paper_id = self.paper["id"]
            paper_name = self.paper["name"]
            user_id = self.paper["user_id"]
            project_id = self.paper["project_id"]

            # 1. Chunk document
            self.signals.progress.emit(20, f"Splitting text into chunks (Size: 1000, Overlap: 200)...")
            chunks = self.rag.chunk_document(
                self.pages_content, 
                self.paper.get("authors", "Unknown"), 
                self.paper.get("upload_date", "")
            )

            # 2. Embedding generation & FAISS save
            self.signals.progress.emit(40, f"Generating vector embeddings with {self.embedding_model}...")
            self.rag.index_paper_chunks(
                user_id=user_id,
                project_id=project_id,
                paper_id=paper_id,
                paper_name=paper_name,
                chunks=chunks,
                embedding_model_name=self.embedding_model
            )

            # 3. Generate initial Summary, Contributions, Limitations, Future Work
            self.signals.progress.emit(70, "Generating paper Executive Summary & Key Insights...")
            
            # Combine first two pages and last page for summarization context (representative of paper contents)
            summary_context = ""
            if len(self.pages_content) > 0:
                summary_context += f"Abstract/Intro:\n{self.pages_content[0]['text'][:2000]}\n"
            if len(self.pages_content) > 1:
                summary_context += f"Methodology Sample:\n{self.pages_content[1]['text'][:1000]}\n"
            if len(self.pages_content) > 2:
                summary_context += f"Conclusion/Results:\n{self.pages_content[-1]['text'][:2000]}"
                
            prompt = (
                f"Analyze the following parts of the research paper '{paper_name}' and generate a structured summary in JSON format. "
                f"Ensure the response is a single valid JSON object containing exactly the following keys:\n"
                f"- 'executive_summary': A comprehensive paragraph summarizing the entire paper.\n"
                f"- 'objective': The primary research question or objective.\n"
                f"- 'methodology': The methodology or approach used.\n"
                f"- 'results': The experimental results, findings, and accuracies.\n"
                f"- 'conclusion': The main conclusion.\n"
                f"- 'contributions': A JSON array of 4 key contribution strings.\n"
                f"- 'limitations': A JSON object with 'technical', 'dataset', 'methodological', and 'practical' limitation descriptions.\n"
                f"- 'future_work': A JSON object with 'short_term', 'long_term', and 'extensions' descriptions.\n\n"
                f"Paper Text Context:\n{summary_context}"
            )
            
            try:
                res, _ = self.llm.generate(
                    user_id=user_id,
                    prompt=prompt,
                    context_chunks=[],
                    history=[],
                    custom_system_prompt="You are a professional academic reviewer. Output raw JSON only."
                )
                
                # Cleanup markdown if returned
                json_str = res.replace("```json", "").replace("```", "").strip()
                summary_parsed = json.loads(json_str)
                
                # Save to database
                self.db.update_paper_summary(paper_id, json.dumps(summary_parsed))
                logger.info(f"Summary generated and saved for paper: {paper_name}")
            except Exception as e:
                logger.error(f"Failed to generate summary: {e}")
                # Save partial/placeholder structure so database never has missing JSON
                placeholder = {
                    "executive_summary": "Auto summary failed to generate due to provider timeouts.",
                    "objective": "N/A", "methodology": "N/A", "results": "N/A", "conclusion": "N/A",
                    "contributions": ["N/A", "N/A", "N/A", "N/A"],
                    "limitations": {"technical": "N/A", "dataset": "N/A", "methodological": "N/A", "practical": "N/A"},
                    "future_work": {"short_term": "N/A", "long_term": "N/A", "extensions": "N/A"}
                }
                self.db.update_paper_summary(paper_id, json.dumps(placeholder))
                self.signals.warning.emit("Indexing completed, but executive summary generation failed.")

            self.signals.progress.emit(100, "Paper successfully indexed and summarized!")
            self.signals.finished.emit({"paper_id": paper_id, "paper_name": paper_name})

        except Exception as e:
            logger.error(f"Indexing worker error: {e}")
            self.signals.error.emit(str(e))

# --- Chat LLM Request Worker ---
class ChatWorker(QThread):
    finished = Signal(str, list)      # response_content, citations_list
    error = Signal(str)

    def __init__(self, 
                 user_id: str, 
                 project_id: str,
                 prompt: str, 
                 embedding_model: str,
                 history: List[Dict[str, str]], 
                 mode: str,
                 paper_ids: Optional[List[str]],
                 rag_service: RAGService,
                 llm_service: LLMService):
        super().__init__()
        self.user_id = user_id
        self.project_id = project_id
        self.prompt = prompt
        self.embedding_model = embedding_model
        self.history = history
        self.mode = mode
        self.paper_ids = paper_ids
        self.rag = rag_service
        self.llm = llm_service

    def run(self) -> None:
        """Executes similarity search on FAISS and dispatches the query to LLM provider."""
        try:
            # 1. Retrieve RAG Chunks
            context_chunks = self.rag.retrieve_context(
                user_id=self.user_id,
                project_id=self.project_id,
                query=self.prompt,
                embedding_model_name=self.embedding_model,
                k=5,
                paper_ids=self.paper_ids
            )

            # 2. Call LLM
            content, citations = self.llm.generate(
                user_id=self.user_id,
                prompt=self.prompt,
                context_chunks=context_chunks,
                history=self.history,
                mode=self.mode
            )
            
            self.finished.emit(content, citations)
        except Exception as e:
            logger.error(f"Chat worker thread error: {e}")
            self.error.emit(str(e))
