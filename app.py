import streamlit as st
import os
import sys
import json
import uuid
import datetime
import shutil
import hashlib

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.db_service import DatabaseService
from services.rag_service import RAGService
from services.llm_service import LLMService
from utils.path_manager import PathManager
from utils.citations import CitationsGenerator

# Set Page Config
st.set_page_config(
    page_title="Research Paper Assistant Pro - Web",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom styling for a modern, sleek interface
st.markdown("""
<style>
    .main {
        background-color: #0F172A;
        color: #F8FAFC;
    }
    .stApp {
        background-color: #0F172A;
    }
    div.stButton > button:first-child {
        background-color: #3B82F6;
        color: white;
        border-radius: 6px;
        border: none;
        padding: 8px 16px;
        font-weight: 500;
    }
    div.stButton > button:first-child:hover {
        background-color: #2563EB;
    }
    .card {
        background-color: #1E293B;
        padding: 20px;
        border-radius: 8px;
        border: 1px solid #334155;
        margin-bottom: 15px;
    }
    h1, h2, h3, h4 {
        color: #F8FAFC !important;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Bootstrap Database and RAG Services
if "initialized" not in st.session_state:
    PathManager.initialize()
    db_dir = PathManager.get_path("database")
    vector_dir = PathManager.get_path("vector_db")
    
    db = DatabaseService(db_dir)
    rag = RAGService(vector_dir)
    
    # Setup Default Profile and Project
    users = db.get_users()
    if not users:
        user = db.create_user("Default Researcher")
    else:
        user = users[0]
        
    projects = db.get_projects(user["id"])
    if not projects:
        project = db.create_project(user["id"], "My Research Project", "Web Workspace")
    else:
        project = projects[0]
        
    st.session_state.db = db
    st.session_state.rag = rag
    st.session_state.user_id = user["id"]
    st.session_state.project_id = project["id"]
    st.session_state.initialized = True

db = st.session_state.db
rag = st.session_state.rag
user_id = st.session_state.user_id
project_id = st.session_state.project_id

# Sidebar Setup
st.sidebar.title("📚 Research Pro - Web")
st.sidebar.markdown("---")

gemini_api_key = st.sidebar.text_input(
    "Google Gemini API Key",
    type="password",
    value=os.environ.get("GEMINI_API_KEY", ""),
    help="Required to generate executive summaries, comparison matrices, and paper chats."
)

active_model = st.sidebar.selectbox(
    "Active Model",
    ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
)

st.sidebar.markdown("---")
st.sidebar.info(
    "This web application operates as a companion deployable interface for your research library, "
    "fully integrated with your local project database."
)

# Mock Settings Service for LLMService compatibility
class MockSettingsService:
    def __init__(self, api_key, model):
        self.api_key = api_key
        self.model = model
    def get_active_provider(self, user_id):
        return "gemini"
    def get_provider_model(self, user_id, provider_name):
        return self.model
    def get_api_key(self, user_id, provider_name):
        return self.api_key
    def get_ollama_url(self, user_id):
        return "http://localhost:11434"

llm = LLMService(db, MockSettingsService(gemini_api_key, active_model))

# Main Tabs
tabs = st.tabs(["📄 Upload Papers", "📚 Research Library", "💬 Research Chat", "⚖️ Paper Comparison"])

# --- TAB 1: UPLOAD PAPERS ---
with tabs[0]:
    st.header("Upload Research Papers")
    st.write("Upload PDF research papers to index, chunk, and save them in your semantic library database.")
    
    uploaded_files = st.file_uploader(
        "Choose PDF Files",
        type=["pdf"],
        accept_multiple_files=True
    )
    
    if uploaded_files:
        if not gemini_api_key:
            st.warning("⚠️ Please enter a Gemini API Key in the sidebar to generate summaries and extract paper metadata.")
        
        for uploaded_file in uploaded_files:
            # Check duplicate by filename in memory
            existing_papers = db.get_papers(project_id)
            if any(p["name"] == uploaded_file.name for p in existing_papers):
                st.info(f"ℹ️ '{uploaded_file.name}' is already uploaded in this project.")
                continue
                
            st.write(f"Processing **{uploaded_file.name}**...")
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Save temporarily
            temp_dir = PathManager.get_path("temp")
            temp_path = os.path.join(temp_dir, uploaded_file.name)
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
                
            try:
                # 1. Extraction
                status_text.text("Extracting text and metadata from PDF...")
                progress_bar.progress(30)
                pages_content, total_pages, props = rag.extract_pdf_text_and_metadata(temp_path)
                
                title = props.get("title") or uploaded_file.name
                authors = props.get("authors") or "Unknown"
                abstract = props.get("abstract") or ""
                keywords = props.get("keywords") or ""
                doi = props.get("doi") or ""
                pub_year = props.get("year") or datetime.datetime.now().year
                file_hash = hashlib.md5(uploaded_file.getbuffer()).hexdigest()
                
                # Copy file to uploads folder
                uploads_dir = PathManager.get_path("uploads")
                paper_uuid = str(uuid.uuid4())
                dest_path = os.path.join(uploads_dir, f"{paper_uuid}_{uploaded_file.name}")
                shutil.copy2(temp_path, dest_path)
                
                # Try LLM metadata override if key exists
                if gemini_api_key:
                    status_text.text("Refining paper metadata via Gemini...")
                    sample_text = ""
                    for p in pages_content[:3]:
                        sample_text += p["text"]
                    sample_text = sample_text[:3000]
                    prompt = (
                        f"Extract academic metadata from the following beginning text of a paper. "
                        f"Fields: 'title', 'authors', 'abstract', 'keywords', 'doi', 'publication_year'. "
                        f"Output ONLY valid raw JSON. If unknown, output null.\n\nText:\n{sample_text}"
                    )
                    try:
                        res, _ = llm.generate(
                            user_id=user_id,
                            prompt=prompt,
                            context_chunks=[],
                            history=[],
                            custom_system_prompt="You are a JSON metadata extraction parser."
                        )
                        json_str = res.replace("```json", "").replace("```", "").strip()
                        meta_parsed = json.loads(json_str)
                        title = meta_parsed.get("title") or title
                        authors = meta_parsed.get("authors") or authors
                        abstract = meta_parsed.get("abstract") or abstract
                        keywords = meta_parsed.get("keywords") or keywords
                        doi = meta_parsed.get("doi") or doi
                        pub_year = meta_parsed.get("publication_year") or pub_year
                    except Exception:
                        pass
                
                # Save to database
                status_text.text("Saving record to database...")
                progress_bar.progress(70)
                
                paper_rec = db.add_paper(
                    user_id=user_id,
                    project_id=project_id,
                    name=uploaded_file.name,
                    file_path=dest_path,
                    title=title,
                    authors=authors,
                    abstract=abstract,
                    keywords=keywords,
                    doi=doi,
                    pub_year=int(pub_year) if pub_year else datetime.datetime.now().year,
                    pages=total_pages,
                    file_hash=file_hash
                )
                
                # 2. Chunking & Indexing
                status_text.text("Splitting text and generating FAISS vector index...")
                progress_bar.progress(85)
                chunks = rag.chunk_document(pages_content, str(authors), datetime.datetime.now().isoformat())
                
                rag.index_paper_chunks(
                    user_id=user_id,
                    project_id=project_id,
                    paper_id=paper_rec["id"],
                    paper_name=uploaded_file.name,
                    chunks=chunks,
                    embedding_model_name="all-MiniLM-L6-v2"
                )
                
                # 3. Generate summary
                if gemini_api_key:
                    status_text.text("Generating structured executive summary...")
                    summary_context = f"Title: {title}\nAbstract/Intro:\n"
                    if len(pages_content) > 0:
                        summary_context += pages_content[0]["text"][:2000]
                    prompt = (
                        f"Generate a structured academic summary of the paper '{uploaded_file.name}' in JSON format with keys: "
                        f"'executive_summary', 'objective', 'methodology', 'results', 'conclusion', 'contributions' (array).\n\n"
                        f"Context:\n{summary_context}"
                    )
                    try:
                        res, _ = llm.generate(
                            user_id=user_id,
                            prompt=prompt,
                            context_chunks=[],
                            history=[],
                            custom_system_prompt="You are a professional academic reviewer. Output raw JSON only."
                        )
                        json_str = res.replace("```json", "").replace("```", "").strip()
                        db.update_paper_summary(paper_rec["id"], json_str)
                    except Exception:
                        pass
                
                progress_bar.progress(100)
                status_text.text("Success! Paper added and indexed.")
                st.success(f"Indexed '{uploaded_file.name}' successfully!")
                
            except Exception as e:
                st.error(f"Error processing '{uploaded_file.name}': {e}")
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)

# --- TAB 2: RESEARCH LIBRARY ---
with tabs[1]:
    st.header("Research Library & Search")
    
    # Semantic Search bar
    st.subheader("Search Passages")
    search_col1, search_col2 = st.columns([4, 1])
    with search_col1:
        query = st.text_input("Search papers or semantic passages...", placeholder="Type concepts like 'transformer networks'...")
    with search_col2:
        search_mode = st.radio("Search Mode", ["Standard Search", "Semantic Search"])
        
    papers = db.get_papers(project_id)
    
    if query:
        if search_mode == "Semantic Search":
            st.subheader("Semantic Match Results")
            results = rag.retrieve_context(
                user_id=user_id,
                project_id=project_id,
                query=query,
                embedding_model_name="all-MiniLM-L6-v2",
                k=5
            )
            for idx, r in enumerate(results):
                st.markdown(f"""
                <div class="card">
                    <b>📄 {r['paper_name']} (Page {r['page_number']})</b> - Similarity Match: {r['score']:.3f}
                    <p style="margin-top:8px; font-style:italic;">"{r['content'][:600]}..."</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            filtered_papers = [p for p in papers if query.lower() in p["name"].lower() or query.lower() in p["title"].lower() or query.lower() in str(p["authors"]).lower()]
            st.subheader("Filtered Papers")
            for p in filtered_papers:
                st.markdown(f"**📄 {p['name']}** - *{p['title']}* ({p['pub_year']})")
    else:
        # Display main library grid
        if not papers:
            st.info("Your research library is empty. Go to 'Upload Papers' tab to upload documents.")
        else:
            col1, col2 = st.columns([3, 2])
            with col1:
                st.subheader("All Uploaded Papers")
                for p in papers:
                    if st.button(f"📄 {p['name']}", key=p["id"]):
                        st.session_state.selected_paper_id = p["id"]
                        
            with col2:
                selected_paper_id = st.session_state.get("selected_paper_id")
                if selected_paper_id:
                    paper = db.get_paper(selected_paper_id)
                    if paper:
                        st.subheader("Paper Details & Insights")
                        st.markdown(f"### {paper['title']}")
                        st.write(f"**Authors**: {paper['authors']}")
                        st.write(f"**Year**: {paper['pub_year']} | **DOI**: {paper['doi']}")
                        st.write(f"**Pages**: {paper['pages']}")
                        st.markdown("---")
                        
                        # Executive Summary
                        st.subheader("Executive Summary")
                        summary_json = paper.get("summary_json")
                        if summary_json:
                            try:
                                summary = json.loads(summary_json)
                                st.write(summary.get("executive_summary", "Not summarized yet."))
                                st.subheader("Objective")
                                st.write(summary.get("objective", ""))
                                st.subheader("Methodology")
                                st.write(summary.get("methodology", ""))
                                st.subheader("Results")
                                st.write(summary.get("results", ""))
                            except Exception:
                                st.write("Auto summary failed to parse.")
                        else:
                            st.write("Summary is not generated yet. Enter API key and re-upload to generate summary.")
                            
                        st.markdown("---")
                        st.subheader("Citations Bibliography")
                        apa = CitationsGenerator.to_apa(paper)
                        bibtex = CitationsGenerator.to_bibtex(paper)
                        st.write(f"**APA**: {apa}")
                        st.code(bibtex, language="bibtex")

# --- TAB 3: RESEARCH CHAT ---
with tabs[2]:
    st.header("Research Chat & Assistant")
    
    if not papers:
        st.info("Please upload research papers to start chatting.")
    else:
        st.subheader("Chat Configuration")
        chat_col1, chat_col2 = st.columns([3, 1])
        with chat_col1:
            chat_papers = st.multiselect(
                "Filter Scope (Target Papers)",
                options=[p["id"] for p in papers],
                format_func=lambda pid: next(p["name"] for p in papers if p["id"] == pid),
                default=[p["id"] for p in papers]
            )
        with chat_col2:
            persona = st.selectbox(
                "Assistant Mode",
                ["General", "Paper Reviewer", "Literature Reviewer", "Thesis Coach", "Comparison Expert"]
            )
            
        st.markdown("---")
        
        # Simple chat history in streamlit session state
        if "chat_messages" not in st.session_state:
            st.session_state.chat_messages = []
            
        for msg in st.session_state.chat_messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                
        user_prompt = st.chat_input("Ask a question about the papers...")
        if user_prompt:
            if not gemini_api_key:
                st.error("Please enter a Google Gemini API Key in the sidebar to start chatting.")
            else:
                # 1. User Message
                with st.chat_message("user"):
                    st.write(user_prompt)
                st.session_state.chat_messages.append({"role": "user", "content": user_prompt})
                
                # 2. RAG Context Retrieval
                with st.spinner("Searching vectors..."):
                    context_chunks = rag.retrieve_context(
                        user_id=user_id,
                        project_id=project_id,
                        query=user_prompt,
                        embedding_model_name="all-MiniLM-L6-v2",
                        paper_ids=chat_papers,
                        k=5
                    )
                
                # 3. LLM Response
                with st.spinner("Generating response..."):
                    system_prompts = {
                        "General": "You are a professional academic research assistant.",
                        "Paper Reviewer": "You are an expert peer reviewer. Critical of methodology.",
                        "Literature Reviewer": "You synthesize concepts across multiple target research papers.",
                        "Thesis Coach": "You guide academic thesis writing and research methodology.",
                        "Comparison Expert": "You contrast and compare theories and findings across papers."
                    }
                    
                    response, _ = llm.generate(
                        user_id=user_id,
                        prompt=user_prompt,
                        context_chunks=context_chunks,
                        history=st.session_state.chat_messages[:-1], # pass history
                        custom_system_prompt=system_prompts[persona]
                    )
                    
                with st.chat_message("assistant"):
                    st.write(response)
                    if context_chunks:
                        with st.expander("Show Source Attributions"):
                            for chunk in context_chunks:
                                st.markdown(f"**{chunk['paper_name']} (Page {chunk['page_number']})** - Match Score: {chunk['score']:.3f}")
                                st.caption(chunk["content"][:400] + "...")
                                
                st.session_state.chat_messages.append({"role": "assistant", "content": response})

# --- TAB 4: PAPER COMPARISON ---
with tabs[3]:
    st.header("Compare Papers")
    st.write("Select multiple research papers from your library to generate a comparative analysis matrix.")
    
    if len(papers) < 2:
        st.info("You need to upload at least 2 papers to compare them.")
    else:
        comparison_papers = st.multiselect(
            "Select Papers to Compare",
            options=[p["id"] for p in papers],
            format_func=lambda pid: next(p["name"] for p in papers if p["id"] == pid)
        )
        
        if st.button("Generate Comparison Matrix"):
            if len(comparison_papers) < 2:
                st.warning("Please select at least 2 papers.")
            elif not gemini_api_key:
                st.error("Gemini API Key is required to compare papers.")
            else:
                with st.spinner("Analyzing papers side-by-side..."):
                    # Build comparison prompt
                    papers_meta = []
                    for pid in comparison_papers:
                        p = db.get_paper(pid)
                        p_summary = json.loads(p["summary_json"]) if p.get("summary_json") else {}
                        papers_meta.append({
                            "name": p["name"],
                            "title": p["title"],
                            "authors": p["authors"],
                            "summary": p_summary
                        })
                        
                    prompt = (
                        f"Construct a detailed side-by-side comparative analysis of the following research papers: "
                        f"{json.dumps(papers_meta)}\n\n"
                        f"Provide a comparative matrix evaluating their Core Objectives, Methodology, Dataset/Target, Findings, and Limitations."
                    )
                    
                    res, _ = llm.generate(
                        user_id=user_id,
                        prompt=prompt,
                        context_chunks=[],
                        history=[],
                        custom_system_prompt="You are a comparative academic analyst."
                    )
                    
                    st.subheader("Comparison Analysis Matrix")
                    st.markdown(res)
