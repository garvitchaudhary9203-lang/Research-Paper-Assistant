import os
import hashlib
import datetime
import logging
import threading
from typing import List, Dict, Any, Optional, Tuple
import fitz  # PyMuPDF
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
# Optional OCR imports
try:
    import pytesseract
    from PIL import Image
    import io
    HAS_OCR = True
except ImportError:
    HAS_OCR = False

logger = logging.getLogger("app")

class RAGService:
    def __init__(self, vector_db_dir: str):
        self.vector_db_dir = vector_db_dir
        self._current_model_name = None
        self._embeddings = None
        self._lock = threading.Lock()

    def _get_embeddings(self, model_name: str) -> HuggingFaceEmbeddings:
        """Dynamically load or reuse the sentence embedding model."""
        if self._embeddings is None or self._current_model_name != model_name:
            # Map clean option to standard HuggingFace Hub name
            mapping = {
                "all-MiniLM-L6-v2": "sentence-transformers/all-MiniLM-L6-v2",
                "bge-small": "BAAI/bge-small-en-v1.5",
                "bge-base": "BAAI/bge-base-en-v1.5",
                "e5-large": "intfloat/e5-large-v2"
            }
            hf_path = mapping.get(model_name, "sentence-transformers/all-MiniLM-L6-v2")
            logger.info(f"Loading embedding model: {hf_path}...")
            try:
                self._embeddings = HuggingFaceEmbeddings(model_name=hf_path)
                self._current_model_name = model_name
            except Exception as e:
                logger.error(f"Error loading embedding model {hf_path}: {e}")
                # Fallback to local default MiniLM
                self._embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
                self._current_model_name = "all-MiniLM-L6-v2"
        return self._embeddings

    def calculate_file_hash(self, file_path: str) -> str:
        """Compute the MD5 hash of a file for duplicate checking."""
        hasher = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                buf = f.read(65536)
                while len(buf) > 0:
                    hasher.update(buf)
                    buf = f.read(65536)
            return hasher.hexdigest()
        except Exception as e:
            logger.error(f"Failed to hash file {file_path}: {e}")
            return ""

    def extract_pdf_text_and_metadata(self, file_path: str) -> Tuple[List[Dict[str, Any]], int, Dict[str, Any]]:
        """
        Extract text and author metadata from PDF using PyMuPDF.
        If pages appear scanned, falls back to pytesseract OCR.
        
        Returns:
            Tuple of:
            - List[dict]: List of page dicts: [{"page_number": int, "text": str}]
            - int: total pages
            - dict: extracted file properties (author, title, etc. from fitz metadata)
        """
        pages_content = []
        doc = None
        try:
            doc = fitz.open(file_path)
            total_pages = len(doc)
            meta = doc.metadata
            properties = {
                "author": meta.get("author", "") if meta.get("author") else "Unknown",
                "title": meta.get("title", "") if meta.get("title") else "",
                "subject": meta.get("subject", "") if meta.get("subject") else "",
                "keywords": meta.get("keywords", "") if meta.get("keywords") else ""
            }

            for page_idx in range(total_pages):
                page = doc.load_page(page_idx)
                text = page.get_text()
                
                # Check for scanned page OCR fallback
                if not text.strip() or len(text.strip()) < 50:
                    text = self._perform_ocr_fallback(page, page_idx)
                
                pages_content.append({
                    "page_number": page_idx + 1,
                    "text": text
                })
            
            return pages_content, total_pages, properties
        except Exception as e:
            logger.error(f"Error processing PDF {file_path}: {e}")
            raise e
        finally:
            if doc:
                doc.close()

    def _perform_ocr_fallback(self, page: Any, page_idx: int) -> str:
        """Perform OCR on a PDF page if pytesseract is available."""
        if not HAS_OCR:
            logger.warning(f"Scanned page {page_idx+1} detected but OCR libraries (pytesseract/pillow) are missing.")
            return f"[Page {page_idx+1}: Scanned page. (OCR library not installed)]"
        
        try:
            logger.info(f"Running OCR fallback on page {page_idx+1}...")
            # Render page to image
            pix = page.get_pixmap(dpi=150)
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            text = pytesseract.image_to_string(img)
            return text
        except Exception as e:
            logger.error(f"OCR failed on page {page_idx+1}: {e}")
            return f"[Page {page_idx+1}: Scanned page. (OCR execution failed)]"

    def chunk_document(self, 
                       pages_content: List[Dict[str, Any]], 
                       author: str, 
                       upload_date: str) -> List[Dict[str, Any]]:
        """Split document pages into semantic chunks of size 1000 with overlap 200."""
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        
        chunks = []
        for page in pages_content:
            page_num = page["page_number"]
            page_text = page["text"]
            
            if not page_text.strip():
                continue
                
            split_texts = text_splitter.split_text(page_text)
            for split_text in split_texts:
                chunks.append({
                    "text": split_text,
                    "page_number": page_num,
                    "author": author,
                    "upload_date": upload_date
                })
        return chunks

    def index_paper_chunks(self, 
                           user_id: str, 
                           project_id: str, 
                           paper_id: str, 
                           paper_name: str, 
                           chunks: List[Dict[str, Any]], 
                           embedding_model_name: str) -> None:
        """Embed and save document chunks in partitioned FAISS vector database."""
        with self._lock:
            faiss_dir = os.path.join(self.vector_db_dir, user_id, project_id, embedding_model_name)
            embeddings = self._get_embeddings(embedding_model_name)
            
            docs = []
            for chunk in chunks:
                docs.append(Document(
                    page_content=chunk["text"],
                    metadata={
                        "paper_id": paper_id,
                        "paper_name": paper_name,
                        "page_number": chunk["page_number"],
                        "upload_date": chunk["upload_date"],
                        "author": chunk["author"]
                    }
                ))

            if not docs:
                logger.warning(f"No text extracted to index for paper: {paper_name}")
                return

            if os.path.exists(os.path.join(faiss_dir, "index.faiss")):
                logger.info(f"Adding documents to existing FAISS index in {faiss_dir}...")
                db = FAISS.load_local(faiss_dir, embeddings, allow_dangerous_deserialization=True)
                db.add_documents(docs)
            else:
                logger.info(f"Creating new FAISS index in {faiss_dir}...")
                db = FAISS.from_documents(docs, embeddings)

            db.save_local(faiss_dir)
            logger.info(f"FAISS index saved successfully for paper: {paper_name}")

    def delete_paper_from_index(self, user_id: str, project_id: str, paper_id: str, embedding_model_name: str) -> None:
        """Remove a paper's vectors from the FAISS database."""
        with self._lock:
            faiss_dir = os.path.join(self.vector_db_dir, user_id, project_id, embedding_model_name)
            if not os.path.exists(os.path.join(faiss_dir, "index.faiss")):
                return

            embeddings = self._get_embeddings(embedding_model_name)
            try:
                db = FAISS.load_local(faiss_dir, embeddings, allow_dangerous_deserialization=True)
                
                # Reconstruct the index excluding the paper's document chunks
                remaining_docs = []
                for doc_id, doc in db.docstore._dict.items():
                    if doc.metadata.get("paper_id") != paper_id:
                        remaining_docs.append(doc)

                if remaining_docs:
                    logger.info(f"Rebuilding FAISS index after removing paper {paper_id}...")
                    new_db = FAISS.from_documents(remaining_docs, embeddings)
                    new_db.save_local(faiss_dir)
                else:
                    logger.info(f"Index is empty. Deleting FAISS path: {faiss_dir}")
                    import shutil
                    shutil.rmtree(faiss_dir, ignore_errors=True)
            except Exception as e:
                logger.error(f"Failed to delete paper {paper_id} from FAISS index: {e}")

    def retrieve_context(self, 
                         user_id: str, 
                         project_id: str, 
                         query: str, 
                         embedding_model_name: str, 
                         k: int = 5,
                         paper_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Retrieves matching chunks from FAISS vector store.
        If paper_ids is provided, filters retrieved chunks to only those papers.
        """
        faiss_dir = os.path.join(self.vector_db_dir, user_id, project_id, embedding_model_name)
        if not os.path.exists(os.path.join(faiss_dir, "index.faiss")):
            return []

        embeddings = self._get_embeddings(embedding_model_name)
        try:
            db = FAISS.load_local(faiss_dir, embeddings, allow_dangerous_deserialization=True)
            
            # Setup filter and fetch size
            filter_func = (lambda m: m.get("paper_id") in paper_ids) if paper_ids else None
            fetch_k = db.index.ntotal if paper_ids else k
            
            results = db.similarity_search_with_score(query, k=k, filter=filter_func, fetch_k=fetch_k)
            
            chunks = []
            for doc, score in results:
                # FAISS score is L2 distance, convert to similarity metric
                similarity_score = float(1.0 / (1.0 + score))
                p_id = doc.metadata.get("paper_id")
                
                chunks.append({
                    "paper_id": p_id,
                    "paper_name": doc.metadata.get("paper_name"),
                    "page_number": doc.metadata.get("page_number"),
                    "upload_date": doc.metadata.get("upload_date"),
                    "author": doc.metadata.get("author"),
                    "content": doc.page_content,
                    "score": similarity_score
                })
                    
            return chunks
        except Exception as e:
            logger.error(f"Error during semantic retrieval: {e}")
            return []
