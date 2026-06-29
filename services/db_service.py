import os
import sqlite3
import json
import uuid
import datetime
import logging
import glob
import threading
import functools
from typing import List, Dict, Any, Optional
from utils.path_manager import PathManager

logger = logging.getLogger("app")

def lock_all_methods(cls):
    for attr_name, attr_value in list(cls.__dict__.items()):
        if callable(attr_value) and not attr_name.startswith("__"):
            def make_wrapper(method):
                @functools.wraps(method)
                def wrapper(self, *args, **kwargs):
                    with self._lock:
                        return method(self, *args, **kwargs)
                return wrapper
            setattr(cls, attr_name, make_wrapper(attr_value))
    return cls

@lock_all_methods
class DatabaseService:
    def __init__(self, db_dir: str):
        self.db_path = os.path.join(db_dir, "memory.db")
        self.conn = None
        self._lock = threading.RLock()
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the SQLite database connection and run schema migrations."""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA foreign_keys = ON;")
            self._run_migrations()
        except Exception as e:
            logger.error(f"Failed to initialize SQLite database at {self.db_path}: {e}")
            raise e

    def _run_migrations(self) -> None:
        """Run database migrations in database/migrations/ and keep schema updated."""
        cursor = self.conn.cursor()
        current_version = 0

        # Step 1: Check if the schema_version table exists
        try:
            cursor.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1;")
            row = cursor.fetchone()
            if row:
                current_version = row[0]
        except sqlite3.OperationalError:
            # Table schema_version does not exist. Initialize db with baseline schema.
            logger.info("Initializing baseline SQLite schema...")
            self._execute_baseline()
            current_version = 1

        # Step 2: Scan for dynamic migrations in the migrations folder
        migrations_dir = os.path.join(PathManager.get_app_dir(), "database", "migrations")
        if os.path.exists(migrations_dir):
            sql_files = glob.glob(os.path.join(migrations_dir, "*.sql"))
            # Sort files by version prefix, e.g. 001_initial.sql -> 1, 002_x.sql -> 2
            sorted_migrations = []
            for filepath in sql_files:
                basename = os.path.basename(filepath)
                parts = basename.split("_", 1)
                if len(parts) > 0 and parts[0].isdigit():
                    version = int(parts[0])
                    sorted_migrations.append((version, filepath))
            
            sorted_migrations.sort(key=lambda x: x[0])

            for version, filepath in sorted_migrations:
                if version > current_version:
                    logger.info(f"Running migration version {version} from {os.path.basename(filepath)}")
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            sql_script = f.read()
                        self.conn.executescript(sql_script)
                        self.conn.execute("INSERT OR REPLACE INTO schema_version (version) VALUES (?);", (version,))
                        self.conn.commit()
                        current_version = version
                        logger.info(f"Migration {version} executed successfully.")
                    except Exception as err:
                        self.conn.rollback()
                        logger.error(f"Migration version {version} failed: {err}")
                        raise err

    def _execute_baseline(self) -> None:
        """Runs the baseline schema in case no migrations folder is bundled or on first launch."""
        baseline_sql = """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS papers (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            upload_date TEXT NOT NULL,
            title TEXT,
            authors TEXT,
            abstract TEXT,
            keywords TEXT,
            doi TEXT,
            pub_year INTEGER,
            pages INTEGER,
            file_hash TEXT,
            summary_json TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            citations_json TEXT,
            FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS comparisons (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            papers_compared TEXT NOT NULL, -- JSON list of paper IDs
            comparison_data TEXT NOT NULL,  -- JSON comparison content
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS api_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            prompt_tokens INTEGER DEFAULT 0,
            completion_tokens INTEGER DEFAULT 0,
            cost REAL DEFAULT 0.0,
            timestamp TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS collections (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            name TEXT NOT NULL,
            query_rules_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY
        );
        INSERT OR IGNORE INTO schema_version (version) VALUES (1);
        """
        self.conn.executescript(baseline_sql)
        self.conn.commit()

    def close(self) -> None:
        """Close SQLite database connection safely."""
        if self.conn:
            self.conn.close()
            self.conn = None

    # --- User Management ---
    def create_user(self, username: str) -> Dict[str, Any]:
        user_id = str(uuid.uuid4())
        created_at = datetime.datetime.now().isoformat()
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO users (id, username, created_at) VALUES (?, ?, ?);",
            (user_id, username, created_at)
        )
        self.conn.commit()
        return {"id": user_id, "username": username, "created_at": created_at}

    def get_users(self) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users ORDER BY username ASC;")
        return [dict(row) for row in cursor.fetchall()]

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?;", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def delete_user(self, user_id: str) -> None:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = ?;", (user_id,))
        self.conn.commit()

    # --- Project Management ---
    def create_project(self, user_id: str, name: str, description: str = "") -> Dict[str, Any]:
        project_id = str(uuid.uuid4())
        created_at = datetime.datetime.now().isoformat()
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO projects (id, user_id, name, description, created_at) VALUES (?, ?, ?, ?, ?);",
            (project_id, user_id, name, description, created_at)
        )
        self.conn.commit()
        return {"id": project_id, "user_id": user_id, "name": name, "description": description, "created_at": created_at}

    def get_projects(self, user_id: str) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM projects WHERE user_id = ? ORDER BY name ASC;", (user_id,))
        return [dict(row) for row in cursor.fetchall()]

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM projects WHERE id = ?;", (project_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def delete_project(self, project_id: str) -> None:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM projects WHERE id = ?;", (project_id,))
        self.conn.commit()

    # --- Paper Management ---
    def add_paper(self, user_id: str, project_id: str, name: str, file_path: str,
                  title: str = "", authors: str = "", abstract: str = "",
                  keywords: str = "", doi: str = "", pub_year: Optional[int] = None,
                  pages: int = 0, file_hash: str = "", summary_json: str = "") -> Dict[str, Any]:
        # Normalize list/non-string fields to strings for robust SQLite binding
        if isinstance(authors, list):
            authors = ", ".join(str(a) for a in authors)
        elif not isinstance(authors, str):
            authors = str(authors) if authors is not None else ""

        if isinstance(keywords, list):
            keywords = ", ".join(str(k) for k in keywords)
        elif not isinstance(keywords, str):
            keywords = str(keywords) if keywords is not None else ""

        if not isinstance(title, str):
            title = str(title) if title is not None else ""
        if not isinstance(abstract, str):
            abstract = str(abstract) if abstract is not None else ""
        if not isinstance(doi, str):
            doi = str(doi) if doi is not None else ""

        paper_id = str(uuid.uuid4())
        upload_date = datetime.datetime.now().isoformat()
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT INTO papers (id, user_id, project_id, name, file_path, upload_date, 
                                  title, authors, abstract, keywords, doi, pub_year, pages, file_hash, summary_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);""",
            (paper_id, user_id, project_id, name, file_path, upload_date,
             title, authors, abstract, keywords, doi, pub_year, pages, file_hash, summary_json)
        )
        self.conn.commit()
        return {
            "id": paper_id, "user_id": user_id, "project_id": project_id, "name": name,
            "file_path": file_path, "upload_date": upload_date, "title": title,
            "authors": authors, "abstract": abstract, "keywords": keywords, "doi": doi,
            "pub_year": pub_year, "pages": pages, "file_hash": file_hash, "summary_json": summary_json
        }

    def check_duplicate_paper(self, project_id: str, file_hash: str, title: str, doi: str) -> Optional[Dict[str, Any]]:
        """Checks if a paper already exists in the project by hash, DOI, or title (case-insensitive similarity)."""
        cursor = self.conn.cursor()
        
        # Check by Hash
        if file_hash:
            cursor.execute("SELECT * FROM papers WHERE project_id = ? AND file_hash = ?;", (project_id, file_hash))
            row = cursor.fetchone()
            if row:
                return dict(row)

        # Check by DOI
        if doi and doi.strip():
            cursor.execute("SELECT * FROM papers WHERE project_id = ? AND doi = ? AND doi != '';", (project_id, doi.strip()))
            row = cursor.fetchone()
            if row:
                return dict(row)

        # Check by Title
        if title and title.strip():
            cursor.execute("SELECT * FROM papers WHERE project_id = ? AND LOWER(title) = ? AND title != '';", (project_id, title.strip().lower()))
            row = cursor.fetchone()
            if row:
                return dict(row)
                
        return None

    def get_papers(self, project_id: str) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM papers WHERE project_id = ? ORDER BY upload_date DESC;", (project_id,))
        return [dict(row) for row in cursor.fetchall()]

    def get_paper(self, paper_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM papers WHERE id = ?;", (paper_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_paper_metadata(self, paper_id: str, title: str, authors: str, abstract: str, keywords: str, doi: str, pub_year: int) -> None:
        # Normalize list/non-string fields to strings for robust SQLite binding
        if isinstance(authors, list):
            authors = ", ".join(str(a) for a in authors)
        elif not isinstance(authors, str):
            authors = str(authors) if authors is not None else ""

        if isinstance(keywords, list):
            keywords = ", ".join(str(k) for k in keywords)
        elif not isinstance(keywords, str):
            keywords = str(keywords) if keywords is not None else ""

        if not isinstance(title, str):
            title = str(title) if title is not None else ""
        if not isinstance(abstract, str):
            abstract = str(abstract) if abstract is not None else ""
        if not isinstance(doi, str):
            doi = str(doi) if doi is not None else ""

        cursor = self.conn.cursor()
        cursor.execute(
            """UPDATE papers 
               SET title = ?, authors = ?, abstract = ?, keywords = ?, doi = ?, pub_year = ? 
               WHERE id = ?;""",
            (title, authors, abstract, keywords, doi, pub_year, paper_id)
        )
        self.conn.commit()

    def update_paper_summary(self, paper_id: str, summary_json: str) -> None:
        cursor = self.conn.cursor()
        cursor.execute("UPDATE papers SET summary_json = ? WHERE id = ?;", (summary_json, paper_id))
        self.conn.commit()

    def delete_paper(self, paper_id: str) -> None:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM papers WHERE id = ?;", (paper_id,))
        self.conn.commit()

    # --- Smart Collections ---
    def create_collection(self, user_id: str, project_id: str, name: str, query_rules: Dict[str, Any]) -> Dict[str, Any]:
        col_id = str(uuid.uuid4())
        created_at = datetime.datetime.now().isoformat()
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO collections (id, user_id, project_id, name, query_rules_json, created_at) VALUES (?, ?, ?, ?, ?, ?);",
            (col_id, user_id, project_id, name, json.dumps(query_rules), created_at)
        )
        self.conn.commit()
        return {"id": col_id, "user_id": user_id, "project_id": project_id, "name": name, "query_rules": query_rules, "created_at": created_at}

    def get_collections(self, project_id: str) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM collections WHERE project_id = ? ORDER BY name ASC;", (project_id,))
        rows = cursor.fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["query_rules"] = json.loads(d["query_rules_json"])
            result.append(d)
        return result

    def get_collection_papers(self, collection_id: str) -> List[Dict[str, Any]]:
        """Queries papers matching a collection's smart rules (like keyword in title/abstract or publication year)."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM collections WHERE id = ?;", (collection_id,))
        col_row = cursor.fetchone()
        if not col_row:
            return []
        
        col = dict(col_row)
        rules = json.loads(col["query_rules_json"])
        project_id = col["project_id"]

        # Formulate query based on rules (e.g. {'keywords': ['transformer', 'attention'], 'year_min': 2020})
        query = "SELECT * FROM papers WHERE project_id = ?"
        params = [project_id]

        clauses = []
        if "keywords" in rules and rules["keywords"]:
            sub_clauses = []
            for kw in rules["keywords"]:
                sub_clauses.append("(LOWER(title) LIKE ? OR LOWER(abstract) LIKE ? OR LOWER(keywords) LIKE ?)")
                like_val = f"%{kw.lower()}%"
                params.extend([like_val, like_val, like_val])
            clauses.append("(" + " OR ".join(sub_clauses) + ")")

        if "year_min" in rules and rules["year_min"]:
            clauses.append("pub_year >= ?")
            params.append(rules["year_min"])

        if "year_max" in rules and rules["year_max"]:
            clauses.append("pub_year <= ?")
            params.append(rules["year_max"])

        if clauses:
            query += " AND " + " AND ".join(clauses)

        query += " ORDER BY upload_date DESC;"
        cursor.execute(query, tuple(params))
        return [dict(row) for row in cursor.fetchall()]

    def delete_collection(self, collection_id: str) -> None:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM collections WHERE id = ?;", (collection_id,))
        self.conn.commit()

    # --- Session & Conversation Management ---
    def create_session(self, user_id: str, project_id: str, name: str) -> Dict[str, Any]:
        session_id = str(uuid.uuid4())
        created_at = datetime.datetime.now().isoformat()
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO sessions (id, user_id, project_id, name, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?);",
            (session_id, user_id, project_id, name, created_at, created_at)
        )
        self.conn.commit()
        return {"id": session_id, "user_id": user_id, "project_id": project_id, "name": name, "created_at": created_at, "updated_at": created_at}

    def get_sessions(self, project_id: str) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE project_id = ? ORDER BY updated_at DESC;", (project_id,))
        return [dict(row) for row in cursor.fetchall()]

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE id = ?;", (session_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_session_timestamp(self, session_id: str) -> None:
        now = datetime.datetime.now().isoformat()
        cursor = self.conn.cursor()
        cursor.execute("UPDATE sessions SET updated_at = ? WHERE id = ?;", (now, session_id))
        self.conn.commit()

    def rename_session(self, session_id: str, new_name: str) -> None:
        cursor = self.conn.cursor()
        cursor.execute("UPDATE sessions SET name = ? WHERE id = ?;", (new_name, session_id))
        self.conn.commit()

    def delete_session(self, session_id: str) -> None:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE id = ?;", (session_id,))
        self.conn.commit()

    def save_message(self, session_id: str, role: str, content: str, citations_json: str = "[]") -> Dict[str, Any]:
        message_id = str(uuid.uuid4())
        timestamp = datetime.datetime.now().isoformat()
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO conversations (id, session_id, role, content, timestamp, citations_json) VALUES (?, ?, ?, ?, ?, ?);",
            (message_id, session_id, role, content, timestamp, citations_json)
        )
        self.conn.commit()
        self.update_session_timestamp(session_id)
        return {"id": message_id, "session_id": session_id, "role": role, "content": content, "timestamp": timestamp, "citations_json": citations_json}

    def get_chat_history(self, session_id: str) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM conversations WHERE session_id = ? ORDER BY timestamp ASC;", (session_id,))
        return [dict(row) for row in cursor.fetchall()]

    # --- Comparisons Management ---
    def save_comparison(self, user_id: str, project_id: str, papers_compared: List[str], comparison_data: Dict[str, Any]) -> Dict[str, Any]:
        comp_id = str(uuid.uuid4())
        created_at = datetime.datetime.now().isoformat()
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO comparisons (id, user_id, project_id, papers_compared, comparison_data, created_at) VALUES (?, ?, ?, ?, ?, ?);",
            (comp_id, user_id, project_id, json.dumps(papers_compared), json.dumps(comparison_data), created_at)
        )
        self.conn.commit()
        return {"id": comp_id, "user_id": user_id, "project_id": project_id, "papers_compared": papers_compared, "comparison_data": comparison_data, "created_at": created_at}

    def get_comparisons(self, project_id: str) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM comparisons WHERE project_id = ? ORDER BY created_at DESC;", (project_id,))
        rows = cursor.fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["papers_compared"] = json.loads(d["papers_compared"])
            d["comparison_data"] = json.loads(d["comparison_data"])
            result.append(d)
        return result

    def delete_comparison(self, comparison_id: str) -> None:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM comparisons WHERE id = ?;", (comparison_id,))
        self.conn.commit()

    # --- API Usage & Benchmarks ---
    def log_api_usage(self, user_id: str, provider: str, model: str, prompt_tokens: int, completion_tokens: int, cost: float) -> None:
        timestamp = datetime.datetime.now().isoformat()
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO api_usage (user_id, provider, model, prompt_tokens, completion_tokens, cost, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?);",
            (user_id, provider, model, prompt_tokens, completion_tokens, cost, timestamp)
        )
        self.conn.commit()

    def get_api_usage_metrics(self, user_id: str) -> Dict[str, Any]:
        cursor = self.conn.cursor()
        cursor.execute(
            """SELECT 
                COUNT(*) as total_requests,
                SUM(prompt_tokens) as total_prompt_tokens,
                SUM(completion_tokens) as total_completion_tokens,
                SUM(cost) as total_cost
               FROM api_usage 
               WHERE user_id = ?;""",
            (user_id,)
        )
        row = cursor.fetchone()
        metrics = dict(row) if row else {"total_requests": 0, "total_prompt_tokens": 0, "total_completion_tokens": 0, "total_cost": 0.0}
        
        # Replace None with 0
        for k in ["total_prompt_tokens", "total_completion_tokens", "total_cost"]:
            if metrics.get(k) is None:
                metrics[k] = 0.0 if k == "total_cost" else 0

        # Provider Breakdown
        cursor.execute(
            """SELECT provider, COUNT(*) as count, SUM(cost) as cost 
               FROM api_usage 
               WHERE user_id = ? 
               GROUP BY provider;""",
            (user_id,)
        )
        metrics["provider_breakdown"] = [dict(r) for r in cursor.fetchall()]

        # Model Breakdown
        cursor.execute(
            """SELECT model, COUNT(*) as count, SUM(cost) as cost 
               FROM api_usage 
               WHERE user_id = ? 
               GROUP BY model;""",
            (user_id,)
        )
        metrics["model_breakdown"] = [dict(r) for r in cursor.fetchall()]

        # Daily Usage (last 30 days)
        cursor.execute(
            """SELECT date(timestamp) as day, COUNT(*) as count, SUM(cost) as cost
               FROM api_usage 
               WHERE user_id = ? AND timestamp >= date('now', '-30 days')
               GROUP BY day 
               ORDER BY day ASC;""",
            (user_id,)
        )
        metrics["daily_usage"] = [dict(r) for r in cursor.fetchall()]

        return metrics

    # --- Search Features (SQLite Metadata level) ---
    def global_search_metadata(self, project_id: str, query: str) -> List[Dict[str, Any]]:
        """Search papers based on metadata attributes (Title, Authors, Abstract, Keywords)."""
        cursor = self.conn.cursor()
        like_query = f"%{query}%"
        cursor.execute(
            """SELECT * FROM papers 
               WHERE project_id = ? 
                 AND (title LIKE ? OR authors LIKE ? OR abstract LIKE ? OR keywords LIKE ? OR name LIKE ?)
               ORDER BY upload_date DESC;""",
            (project_id, like_query, like_query, like_query, like_query, like_query)
        )
        return [dict(row) for row in cursor.fetchall()]
