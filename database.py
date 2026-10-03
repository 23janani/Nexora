"""
Enterprise Relational SQLite Database Manager
Supports ACID transactions, Write-Ahead Logging (WAL), foreign key constraints,
parameterized queries, and persistent storage for Users, Jobs, Candidates,
Evaluations, Customized AI Interview Questions, and Security Audit Logs.
"""

import os
import json
import uuid
import sqlite3
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

logger = logging.getLogger("DatabaseManager")

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resume_matcher.db")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now_ts() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


class DatabaseManager:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Create a thread-safe connection with dictionary cursor and foreign keys enabled."""
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def _init_db(self):
        """Create database tables and indexes if they do not exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Users Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                user_type TEXT NOT NULL CHECK(user_type IN ('hr', 'candidate', 'admin')),
                created_at TEXT NOT NULL,
                last_login TEXT
            );
            """)

            # 2. Jobs / Requirements Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                department TEXT,
                experience_level TEXT,
                must_haves_json TEXT NOT NULL,
                nice_to_haves_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """)

            # 3. Candidates Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS candidates (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                location TEXT,
                current_title TEXT,
                years_experience REAL DEFAULT 0,
                raw_text TEXT,
                parsed_data_json TEXT,
                resume_hash TEXT,
                source TEXT DEFAULT 'Upload',
                created_at TEXT NOT NULL
            );
            """)

            # 4. Evaluations Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS evaluations (
                id TEXT PRIMARY KEY,
                candidate_id TEXT NOT NULL,
                job_id TEXT NOT NULL,
                fit_score INTEGER NOT NULL,
                confidence_score INTEGER NOT NULL,
                must_have_score INTEGER DEFAULT 0,
                nice_to_have_score INTEGER DEFAULT 0,
                matches_json TEXT NOT NULL,
                gaps_json TEXT NOT NULL,
                flags_json TEXT NOT NULL,
                category_breakdown_json TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
                FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
            );
            """)

            # 5. Customized AI Interview Questions Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS interview_questions (
                id TEXT PRIMARY KEY,
                evaluation_id TEXT,
                candidate_id TEXT NOT NULL,
                question_text TEXT NOT NULL,
                category TEXT NOT NULL,
                difficulty TEXT DEFAULT 'Senior',
                evaluation_hint TEXT,
                candidate_coaching TEXT,
                is_custom INTEGER DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
            );
            """)

            # 6. Enterprise Audit Logs Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT NOT NULL,
                action TEXT NOT NULL,
                ip_address TEXT,
                details_json TEXT,
                timestamp TEXT NOT NULL
            );
            """)

            # 7. Scheduled Interviews Table (Feature 1)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS interviews (
                id TEXT PRIMARY KEY,
                candidate_id TEXT NOT NULL,
                evaluation_id TEXT,
                interviewer_email TEXT NOT NULL,
                interviewer_name TEXT,
                candidate_name TEXT,
                candidate_email TEXT,
                job_title TEXT,
                scheduled_at TEXT NOT NULL,
                duration_minutes INTEGER DEFAULT 45,
                calendar_event_id TEXT,
                meeting_link TEXT,
                status TEXT DEFAULT 'scheduled' CHECK(status IN ('scheduled', 'completed', 'rescheduled', 'cancelled')),
                questions_json TEXT,
                rating REAL,
                notes TEXT,
                feedback_summary TEXT,
                reminders_sent INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
            );
            """)

            # 8. Career Roadmaps Table (Feature 2)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS roadmaps (
                id TEXT PRIMARY KEY,
                candidate_id TEXT,
                evaluation_id TEXT,
                candidate_name TEXT,
                job_title TEXT NOT NULL,
                baseline_readiness REAL DEFAULT 0.0,
                current_readiness REAL DEFAULT 0.0,
                summary TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT
            );
            """)

            # 9. Career Roadmap Milestone Items Table (Feature 2)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS roadmap_items (
                id TEXT PRIMARY KEY,
                roadmap_id TEXT NOT NULL,
                phase TEXT NOT NULL CHECK(phase IN ('foundational', 'applied', 'interview_ready')),
                skill TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                recommendation_reason TEXT NOT NULL,
                priority TEXT NOT NULL CHECK(priority IN ('critical', 'high', 'medium', 'low')),
                prerequisites_json TEXT,
                estimated_hours INTEGER DEFAULT 10,
                resource_types_json TEXT,
                readiness_impact_pct REAL DEFAULT 5.0,
                is_completed INTEGER DEFAULT 0,
                completed_at TEXT,
                sort_order INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (roadmap_id) REFERENCES roadmaps(id) ON DELETE CASCADE
            );
            """)

            # 10. HR Email Monitors Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_monitors (
                id TEXT PRIMARY KEY,
                hr_email TEXT NOT NULL UNIQUE,
                imap_host TEXT DEFAULT 'imap.gmail.com',
                imap_port INTEGER DEFAULT 993,
                imap_user TEXT,
                imap_pass TEXT,
                use_ssl INTEGER DEFAULT 1,
                is_active INTEGER DEFAULT 1,
                poll_interval_seconds INTEGER DEFAULT 30,
                last_checked_at TEXT,
                total_processed INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """)

            # 11. Email Ingestion Logs Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_ingestion_logs (
                id TEXT PRIMARY KEY,
                hr_email TEXT NOT NULL,
                sender TEXT NOT NULL,
                subject TEXT,
                candidate_id TEXT,
                candidate_name TEXT,
                fit_score REAL,
                status TEXT DEFAULT 'processed',
                created_at TEXT NOT NULL
            );
            """)

            # Create Indexes for Query Optimization
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_candidates_name ON candidates(name);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_eval_candidate ON evaluations(candidate_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_questions_cand ON interview_questions(candidate_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_logs(timestamp);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_interviews_cand ON interviews(candidate_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_interviews_interviewer ON interviews(interviewer_email);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_interviews_status ON interviews(status);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_roadmaps_cand ON roadmaps(candidate_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_roadmap_items_roadmap ON roadmap_items(roadmap_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_email_monitors_hr ON email_monitors(hr_email);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_email_logs_hr ON email_ingestion_logs(hr_email);")

            conn.commit()

    # =========================================================================
    # USER OPERATIONS
    # =========================================================================

    def create_user(self, user_id: str, email: str, password_hash: str, name: str, role: str, user_type: str = "hr") -> bool:
        """Create a user with hashed password."""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT INTO users (id, email, password_hash, name, role, user_type, created_at, last_login)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (user_id, email.lower().strip(), password_hash, name, role, user_type, _now_iso(), _now_iso()))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Retrieve user record by email."""
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),)).fetchone()
            return dict(row) if row else None

    def update_last_login(self, email: str):
        """Update last login timestamp."""
        with self.get_connection() as conn:
            conn.execute("UPDATE users SET last_login = ? WHERE email = ?", (_now_iso(), email.lower().strip()))
            conn.commit()

    # =========================================================================
    # JOB OPERATIONS
    # =========================================================================

    def save_job(self, job_id: str, title: str, department: str, experience_level: str, must_haves: List[str], nice_to_haves: List[str]) -> bool:
        """Upsert a target job posting."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO jobs (id, title, department, experience_level, must_haves_json, nice_to_haves_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                job_id,
                title,
                department,
                experience_level,
                json.dumps(must_haves),
                json.dumps(nice_to_haves),
                _now_iso()
            ))
            conn.commit()
            return True

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a job by ID."""
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            if not row:
                return None
            res = dict(row)
            res["must_haves"] = json.loads(res["must_haves_json"])
            res["nice_to_haves"] = json.loads(res["nice_to_haves_json"])
            return res

    def list_jobs(self) -> List[Dict[str, Any]]:
        """Retrieve all active jobs."""
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM jobs ORDER BY created_at ASC").fetchall()
            jobs = []
            for r in rows:
                item = dict(r)
                item["must_haves"] = json.loads(item["must_haves_json"])
                item["nice_to_haves"] = json.loads(item["nice_to_haves_json"])
                jobs.append(item)
            return jobs

    # =========================================================================
    # CANDIDATE OPERATIONS
    # =========================================================================

    def save_candidate(self, candidate_data: Dict[str, Any]) -> str:
        """Upsert a candidate record."""
        c_id = candidate_data.get("id") or str(_now_ts())
        parsed = candidate_data.get("parsed_data", {})
        basic = parsed.get("basic_info", {})

        name = candidate_data.get("name") or basic.get("name", "Unknown Candidate")
        email = candidate_data.get("email") or basic.get("email", "")
        phone = candidate_data.get("phone") or basic.get("phone", "")
        location = candidate_data.get("location") or basic.get("location", "")
        current_title = candidate_data.get("current_title", "")
        years_exp = candidate_data.get("years_experience", 0)
        raw_text = candidate_data.get("raw_text", "")
        source = candidate_data.get("source", "Direct Upload")
        resume_hash = candidate_data.get("resume_hash", "")

        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO candidates (
                    id, name, email, phone, location, current_title, years_experience,
                    raw_text, parsed_data_json, resume_hash, source, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                c_id, name, email, phone, location, current_title, years_exp,
                raw_text, json.dumps(parsed), resume_hash, source,
                _now_iso()
            ))
            conn.commit()
        return c_id

    def get_candidate(self, candidate_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a candidate with their latest evaluation and interview questions."""
        with self.get_connection() as conn:
            cand_row = conn.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,)).fetchone()
            if not cand_row:
                return None
            cand = dict(cand_row)
            cand["parsed_data"] = json.loads(cand["parsed_data_json"]) if cand["parsed_data_json"] else {}

            # Attach evaluation
            eval_row = conn.execute("SELECT * FROM evaluations WHERE candidate_id = ? ORDER BY created_at DESC LIMIT 1", (candidate_id,)).fetchone()
            if eval_row:
                eval_dict = dict(eval_row)
                eval_dict["matches"] = json.loads(eval_dict["matches_json"])
                eval_dict["gaps"] = json.loads(eval_dict["gaps_json"])
                eval_dict["flags"] = json.loads(eval_dict["flags_json"])
                eval_dict["category_breakdown"] = json.loads(eval_dict["category_breakdown_json"]) if eval_dict["category_breakdown_json"] else {}
                cand["analysis"] = eval_dict

                # Attach questions
                q_rows = conn.execute("SELECT * FROM interview_questions WHERE candidate_id = ? ORDER BY sort_order ASC, created_at ASC", (candidate_id,)).fetchall()
                questions = [dict(q) for q in q_rows]
                cand["analysis"]["mock_interview"] = questions
            return cand

    def list_candidates(self) -> List[Dict[str, Any]]:
        """List all candidates with evaluations."""
        with self.get_connection() as conn:
            cand_rows = conn.execute("SELECT * FROM candidates ORDER BY created_at DESC").fetchall()
            candidates = []
            for cr in cand_rows:
                cand = dict(cr)
                cand["parsed_data"] = json.loads(cand["parsed_data_json"]) if cand["parsed_data_json"] else {}

                # Latest evaluation
                eval_row = conn.execute("SELECT * FROM evaluations WHERE candidate_id = ? ORDER BY created_at DESC LIMIT 1", (cand["id"],)).fetchone()
                if eval_row:
                    eval_dict = dict(eval_row)
                    eval_dict["matches"] = json.loads(eval_dict["matches_json"])
                    eval_dict["gaps"] = json.loads(eval_dict["gaps_json"])
                    eval_dict["flags"] = json.loads(eval_dict["flags_json"])
                    eval_dict["category_breakdown"] = json.loads(eval_dict["category_breakdown_json"]) if eval_dict["category_breakdown_json"] else {}
                    cand["analysis"] = eval_dict
                    cand["fit_score"] = eval_dict["fit_score"]
                    cand["flags"] = eval_dict["flags"]
                else:
                    cand["fit_score"] = 0
                    cand["flags"] = {
                        "duplicate": {"is_duplicate": False},
                        "ai_content": {"is_flagged": False},
                        "repeated_content": {"is_flagged": False}
                    }
                candidates.append(cand)
            return candidates

    def delete_candidate(self, candidate_id: str) -> bool:
        """Delete a candidate and cascaded evaluations / questions."""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM candidates WHERE id = ?", (candidate_id,))
            conn.commit()
            return True

    # =========================================================================
    # EVALUATION OPERATIONS
    # =========================================================================

    def save_evaluation(self, eval_data: Dict[str, Any]) -> str:
        """Upsert candidate evaluation."""
        eval_id = eval_data.get("id") or f"eval_{_now_ts()}"
        c_id = eval_data["candidate_id"]
        job_id = eval_data.get("job_id", "senior_ds_genai")

        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO evaluations (
                    id, candidate_id, job_id, fit_score, confidence_score,
                    must_have_score, nice_to_have_score, matches_json, gaps_json,
                    flags_json, category_breakdown_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                eval_id,
                c_id,
                job_id,
                eval_data.get("fit_score", 0),
                eval_data.get("confidence_score", 85),
                eval_data.get("must_have_score", 0),
                eval_data.get("nice_to_have_score", 0),
                json.dumps(eval_data.get("matches", [])),
                json.dumps(eval_data.get("gaps", [])),
                json.dumps(eval_data.get("flags", {})),
                json.dumps(eval_data.get("category_breakdown", {})),
                _now_iso()
            ))
            conn.commit()
        return eval_id

    # =========================================================================
    # INTERVIEW QUESTION OPERATIONS
    # =========================================================================

    def save_questions(self, candidate_id: str, questions: List[Dict[str, Any]], evaluation_id: Optional[str] = None):
        """Replace or save interview questions for a candidate."""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM interview_questions WHERE candidate_id = ?", (candidate_id,))
            for idx, q in enumerate(questions):
                q_id = f"q_{candidate_id}_{idx+1}_{uuid.uuid4().hex[:6]}"
                q["id"] = q_id
                conn.execute("""
                    INSERT INTO interview_questions (
                        id, evaluation_id, candidate_id, question_text, category, difficulty,
                        evaluation_hint, candidate_coaching, is_custom, sort_order, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    q_id,
                    evaluation_id,
                    candidate_id,
                    q.get("question") or q.get("question_text", ""),
                    q.get("category", "Gap Remediation"),
                    q.get("difficulty", "Senior"),
                    q.get("evaluation_hint", ""),
                    q.get("candidate_coaching", ""),
                    1 if q.get("is_custom") else 0,
                    idx,
                    _now_iso()
                ))
            conn.commit()

    def get_questions_by_candidate(self, candidate_id: str) -> List[Dict[str, Any]]:
        """Retrieve interview questions for a candidate."""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM interview_questions WHERE candidate_id = ? ORDER BY sort_order ASC, created_at ASC",
                (candidate_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    get_candidate_questions = get_questions_by_candidate

    def add_custom_question(self, candidate_id: str, question_data: Dict[str, Any]) -> Dict[str, Any]:
        """Manually add a proprietary custom question."""
        q_id = question_data.get("id") or f"q_custom_{_now_ts()}"
        now = _now_iso()
        with self.get_connection() as conn:
            max_order_row = conn.execute("SELECT MAX(sort_order) as m FROM interview_questions WHERE candidate_id = ?", (candidate_id,)).fetchone()
            order = (max_order_row["m"] or 0) + 1 if max_order_row else 0

            conn.execute("""
                INSERT INTO interview_questions (
                    id, candidate_id, question_text, category, difficulty,
                    evaluation_hint, candidate_coaching, is_custom, sort_order, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
            """, (
                q_id,
                candidate_id,
                question_data.get("question_text", "").strip(),
                question_data.get("category", "Custom Company Requirement"),
                question_data.get("difficulty", "Senior"),
                question_data.get("evaluation_hint", ""),
                question_data.get("candidate_coaching", ""),
                order,
                now,
                now
            ))
            conn.commit()
            row = conn.execute("SELECT * FROM interview_questions WHERE id = ?", (q_id,)).fetchone()
            return dict(row)

    def update_question(self, question_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing interview question."""
        allowed = ["question_text", "category", "difficulty", "evaluation_hint", "candidate_coaching"]
        fields = []
        params = []
        for k in allowed:
            if k in updates:
                fields.append(f"{k} = ?")
                params.append(updates[k])

        if not fields:
            return None

        fields.append("is_custom = 1")
        fields.append("updated_at = ?")
        params.append(_now_iso())
        params.append(question_id)

        with self.get_connection() as conn:
            conn.execute(f"UPDATE interview_questions SET {', '.join(fields)} WHERE id = ?", params)
            conn.commit()
            row = conn.execute("SELECT * FROM interview_questions WHERE id = ?", (question_id,)).fetchone()
            return dict(row) if row else None

    def delete_question(self, question_id: str) -> bool:
        """Remove a question."""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM interview_questions WHERE id = ?", (question_id,))
            conn.commit()
            return True

    # =========================================================================
    # AUDIT LOGGING
    # =========================================================================

    def record_audit(self, user_email: str, action: str, ip_address: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """Append an entry to the audit log."""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT INTO audit_logs (user_email, action, ip_address, details_json, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    user_email or "anonymous",
                    action,
                    ip_address or "127.0.0.1",
                    json.dumps(details or {}),
                    _now_iso()
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Audit log error: {e}")

    def get_audit_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent audit logs."""
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
            logs = []
            for r in rows:
                item = dict(r)
                item["details"] = json.loads(item["details_json"]) if item["details_json"] else {}
                logs.append(item)
            return logs

    # =========================================================================
    # FEATURE 1: INTERVIEW SCHEDULING OPERATIONS
    # =========================================================================

    def create_interview(
        self,
        interview_id: str,
        candidate_id: str,
        evaluation_id: Optional[str],
        interviewer_email: str,
        scheduled_at: str,
        duration_minutes: int = 45,
        meeting_link: Optional[str] = None,
        calendar_event_id: Optional[str] = None,
        questions: Optional[List[Dict[str, Any]]] = None,
        candidate_name: Optional[str] = None,
        candidate_email: Optional[str] = None,
        job_title: Optional[str] = None,
        interviewer_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a scheduled interview entry with attached AI questions."""
        now = _now_iso()
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO interviews (
                    id, candidate_id, evaluation_id, interviewer_email, interviewer_name,
                    candidate_name, candidate_email, job_title, scheduled_at, duration_minutes,
                    calendar_event_id, meeting_link, status, questions_json, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'scheduled', ?, ?, ?)
            """, (
                interview_id, candidate_id, evaluation_id, interviewer_email, interviewer_name or "Lead Technical Assessor",
                candidate_name or "Candidate", candidate_email or "", job_title or "Target Role",
                scheduled_at, duration_minutes, calendar_event_id or "", meeting_link or "",
                json.dumps(questions or []), now, now
            ))
            conn.commit()

        self.record_audit(interviewer_email, "INTERVIEW_SCHEDULED", details={
            "interview_id": interview_id,
            "candidate_id": candidate_id,
            "scheduled_at": scheduled_at,
            "meeting_link": meeting_link
        })
        return self.get_interview(interview_id)

    def get_interview(self, interview_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve interview details by ID."""
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM interviews WHERE id = ?", (interview_id,)).fetchone()
            if not row:
                return None
            item = dict(row)
            item["questions"] = json.loads(item["questions_json"]) if item["questions_json"] else []
            return item

    def list_interviews(
        self,
        candidate_id: Optional[str] = None,
        interviewer_email: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List scheduled interviews with optional filters."""
        query = "SELECT * FROM interviews WHERE 1=1"
        params: List[Any] = []
        if candidate_id:
            query += " AND candidate_id = ?"
            params.append(candidate_id)
        if interviewer_email:
            query += " AND interviewer_email = ?"
            params.append(interviewer_email)
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY scheduled_at ASC LIMIT ?"
        params.append(limit)

        with self.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            results = []
            for r in rows:
                item = dict(r)
                item["questions"] = json.loads(item["questions_json"]) if item["questions_json"] else []
                results.append(item)
            return results

    def reschedule_interview(self, interview_id: str, new_scheduled_at: str, duration_minutes: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Update interview time and transition status to rescheduled."""
        now = _now_iso()
        with self.get_connection() as conn:
            if duration_minutes:
                conn.execute("""
                    UPDATE interviews
                    SET scheduled_at = ?, duration_minutes = ?, status = 'rescheduled', updated_at = ?
                    WHERE id = ?
                """, (new_scheduled_at, duration_minutes, now, interview_id))
            else:
                conn.execute("""
                    UPDATE interviews
                    SET scheduled_at = ?, status = 'rescheduled', updated_at = ?
                    WHERE id = ?
                """, (new_scheduled_at, now, interview_id))
            conn.commit()

        self.record_audit("system", "INTERVIEW_RESCHEDULED", details={
            "interview_id": interview_id,
            "new_scheduled_at": new_scheduled_at
        })
        return self.get_interview(interview_id)

    def cancel_interview(self, interview_id: str, reason: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Cancel scheduled interview."""
        now = _now_iso()
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE interviews
                SET status = 'cancelled', notes = coalesce(notes, '') || ?, updated_at = ?
                WHERE id = ?
            """, (f" [Cancellation Reason: {reason}]" if reason else "", now, interview_id))
            conn.commit()

        self.record_audit("system", "INTERVIEW_CANCELLED", details={
            "interview_id": interview_id,
            "reason": reason
        })
        return self.get_interview(interview_id)

    def update_interview_feedback(
        self,
        interview_id: str,
        rating: float,
        notes: str,
        feedback_summary: str
    ) -> Optional[Dict[str, Any]]:
        """Save interviewer rating, notes, and AI-generated feedback summary."""
        now = _now_iso()
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE interviews
                SET rating = ?, notes = ?, feedback_summary = ?, status = 'completed', updated_at = ?
                WHERE id = ?
            """, (rating, notes, feedback_summary, now, interview_id))
            conn.commit()

        self.record_audit("system", "INTERVIEW_FEEDBACK_RECORDED", details={
            "interview_id": interview_id,
            "rating": rating
        })
        return self.get_interview(interview_id)

    def increment_reminder_count(self, interview_id: str) -> Optional[Dict[str, Any]]:
        """Increment reminders sent count."""
        now = _now_iso()
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE interviews
                SET reminders_sent = reminders_sent + 1, updated_at = ?
                WHERE id = ?
            """, (now, interview_id))
            conn.commit()

        self.record_audit("system", "INTERVIEW_REMINDER_SENT", details={"interview_id": interview_id})
        return self.get_interview(interview_id)

    # =========================================================================
    # FEATURE 2: CAREER ROADMAP & BENCHMARK OPERATIONS
    # =========================================================================

    def create_roadmap(
        self,
        roadmap_id: str,
        candidate_id: Optional[str],
        evaluation_id: Optional[str],
        job_title: str,
        baseline_readiness: float,
        summary: str,
        items: List[Dict[str, Any]],
        candidate_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a multi-phase career roadmap with milestone items."""
        now = _now_iso()
        with self.get_connection() as conn:
            # Upsert / insert roadmap
            conn.execute("""
                INSERT OR REPLACE INTO roadmaps (
                    id, candidate_id, evaluation_id, candidate_name, job_title,
                    baseline_readiness, current_readiness, summary, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                roadmap_id, candidate_id, evaluation_id, candidate_name or "Candidate", job_title,
                baseline_readiness, baseline_readiness, summary, now, now
            ))

            # Delete old items if updating existing roadmap
            conn.execute("DELETE FROM roadmap_items WHERE roadmap_id = ?", (roadmap_id,))

            # Insert all roadmap items
            for idx, item in enumerate(items, 1):
                item_id = item.get("id") or f"rmi_{uuid.uuid4().hex[:10]}"
                conn.execute("""
                    INSERT INTO roadmap_items (
                        id, roadmap_id, phase, skill, title, description,
                        recommendation_reason, priority, prerequisites_json, estimated_hours,
                        resource_types_json, readiness_impact_pct, is_completed, sort_order, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item_id,
                    roadmap_id,
                    item.get("phase", "foundational"),
                    item.get("skill", "Core Competency"),
                    item.get("title", f"Milestone {idx}"),
                    item.get("description", ""),
                    item.get("recommendation_reason", "Direct requirement gap identified in target job description."),
                    item.get("priority", "high"),
                    json.dumps(item.get("prerequisites", [])),
                    int(item.get("estimated_hours", 10)),
                    json.dumps(item.get("resource_types", ["Official Documentation", "Hands-on Practice"])),
                    float(item.get("readiness_impact_pct", 5.0)),
                    1 if item.get("is_completed") else 0,
                    idx,
                    now
                ))
            conn.commit()

        return self.get_roadmap(roadmap_id)

    def get_roadmap(self, roadmap_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve roadmap with all phase milestone items."""
        with self.get_connection() as conn:
            r_row = conn.execute("SELECT * FROM roadmaps WHERE id = ?", (roadmap_id,)).fetchone()
            if not r_row:
                return None
            roadmap = dict(r_row)

            item_rows = conn.execute("""
                SELECT * FROM roadmap_items WHERE roadmap_id = ? ORDER BY phase ASC, sort_order ASC
            """, (roadmap_id,)).fetchall()

            items = []
            for r in item_rows:
                item = dict(r)
                item["prerequisites"] = json.loads(item["prerequisites_json"]) if item["prerequisites_json"] else []
                item["resource_types"] = json.loads(item["resource_types_json"]) if item["resource_types_json"] else []
                item["rationale"] = item.get("recommendation_reason", "")
                p_str = (item.get("phase") or "foundational").lower()
                item["phase_number"] = 1 if p_str == "foundational" else (2 if p_str == "applied" else 3)
                items.append(item)

            roadmap["items"] = items
            roadmap["target_role"] = roadmap.get("job_title")
            roadmap["baseline_score"] = roadmap.get("baseline_readiness")
            # Group items by phase for convenience
            roadmap["phases"] = {
                "foundational": [i for i in items if i["phase"] == "foundational"],
                "applied": [i for i in items if i["phase"] == "applied"],
                "interview_ready": [i for i in items if i["phase"] == "interview_ready"]
            }
            return roadmap

    def get_roadmap_by_candidate(self, candidate_id: str, job_title: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieve latest roadmap for candidate."""
        query = "SELECT id FROM roadmaps WHERE candidate_id = ?"
        params = [candidate_id]
        if job_title:
            query += " AND job_title = ?"
            params.append(job_title)
        query += " ORDER BY created_at DESC LIMIT 1"

        with self.get_connection() as conn:
            row = conn.execute(query, params).fetchone()
            if row:
                return self.get_roadmap(row["id"])
            return None

    def toggle_roadmap_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """
        Toggle milestone completion status.
        Dynamically recalculates roadmap's current readiness percentage.
        """
        now = _now_iso()
        with self.get_connection() as conn:
            item_row = conn.execute("SELECT * FROM roadmap_items WHERE id = ?", (item_id,)).fetchone()
            if not item_row:
                return None
            item = dict(item_row)
            new_status = 0 if item["is_completed"] else 1
            completed_at = now if new_status == 1 else None

            conn.execute("""
                UPDATE roadmap_items
                SET is_completed = ?, completed_at = ?
                WHERE id = ?
            """, (new_status, completed_at, item_id))

            roadmap_id = item["roadmap_id"]

            # Recalculate live readiness percentage
            r_row = conn.execute("SELECT * FROM roadmaps WHERE id = ?", (roadmap_id,)).fetchone()
            if r_row:
                baseline = float(r_row["baseline_readiness"] or 0.0)
                completed_sum_row = conn.execute("""
                    SELECT SUM(readiness_impact_pct) as total_impact
                    FROM roadmap_items
                    WHERE roadmap_id = ? AND is_completed = 1
                """, (roadmap_id,)).fetchone()
                total_impact = float(completed_sum_row["total_impact"] or 0.0) if completed_sum_row else 0.0
                new_readiness = min(100.0, round(baseline + total_impact, 1))

                conn.execute("""
                    UPDATE roadmaps
                    SET current_readiness = ?, updated_at = ?
                    WHERE id = ?
                """, (new_readiness, now, roadmap_id))

            conn.commit()

        return self.get_roadmap(roadmap_id)

    def get_role_benchmarks(
        self,
        job_title: str,
        candidate_score: float,
        category_scores: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Returns anonymized role benchmarks for fit score and category scores.
        STRICT PRIVACY REQUIREMENT:
        Only show percentiles when sample size >= 20; otherwise show "Not enough data".
        Never expose other candidates' identities or individual data.
        """
        with self.get_connection() as conn:
            # Query all evaluations matching job title (case-insensitive substring)
            rows = conn.execute("""
                SELECT e.fit_score, e.confidence_score, e.must_have_score, e.nice_to_have_score, e.category_breakdown_json
                FROM evaluations e
                JOIN jobs j ON e.job_id = j.id
                WHERE LOWER(j.title) LIKE ?
            """, (f"%{job_title.lower()}%",)).fetchall()

            sample_size = len(rows)

            if sample_size < 20:
                return {
                    "status": "insufficient_data",
                    "sample_size": sample_size,
                    "required_sample_size": 20,
                    "message": "Not enough data (minimum 20 candidates required to calculate anonymized statistical percentiles)",
                    "percentile": None,
                    "median_score": None,
                    "p25_score": None,
                    "p75_score": None,
                    "p90_score": None,
                    "category_benchmarks": None
                }

            scores = sorted([float(r["fit_score"]) for r in rows])
            n = len(scores)

            # Percentile calculation
            less_count = sum(1 for s in scores if s < candidate_score)
            percentile = round((less_count / n) * 100.0, 1)

            def get_quantile(p: float) -> float:
                idx = int(p * (n - 1))
                return round(scores[idx], 1)

            median = get_quantile(0.50)
            p25 = get_quantile(0.25)
            p75 = get_quantile(0.75)
            p90 = get_quantile(0.90)

            # Anonymized category benchmarks
            must_haves = [float(r["must_have_score"] or 0) for r in rows]
            nice_haves = [float(r["nice_to_have_score"] or 0) for r in rows]

            cat_averages = {
                "must_have_average": round(sum(must_haves) / n, 1) if n else 0,
                "preferred_average": round(sum(nice_haves) / n, 1) if n else 0
            }

            return {
                "status": "ready",
                "sample_size": sample_size,
                "required_sample_size": 20,
                "percentile": percentile,
                "candidate_score": candidate_score,
                "median_score": median,
                "p25_score": p25,
                "p75_score": p75,
                "p90_score": p90,
                "category_benchmarks": cat_averages
            }

    # =========================================================================
    # HR EMAIL AUTO-MONITORING OPERATIONS
    # =========================================================================

    def get_email_monitor(self, hr_email: str) -> Optional[Dict[str, Any]]:
        """Retrieve the configured email monitor for a given HR email."""
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM email_monitors WHERE hr_email = ?", (hr_email.lower().strip(),)).fetchone()
            return dict(row) if row else None

    def upsert_email_monitor(self, hr_email: str, imap_host: str = "imap.gmail.com", imap_port: int = 993,
                             imap_user: str = "", imap_pass: str = "", use_ssl: bool = True,
                             is_active: bool = True, poll_interval_seconds: int = 30) -> Dict[str, Any]:
        """Create or update HR email monitor settings."""
        hr_clean = hr_email.lower().strip()
        existing = self.get_email_monitor(hr_clean)
        now_str = _now_iso()

        with self.get_connection() as conn:
            if existing:
                monitor_id = existing["id"]
                conn.execute("""
                    UPDATE email_monitors
                    SET imap_host = ?, imap_port = ?, imap_user = ?, imap_pass = ?,
                        use_ssl = ?, is_active = ?, poll_interval_seconds = ?, updated_at = ?
                    WHERE id = ?
                """, (imap_host, imap_port, imap_user or hr_clean, imap_pass,
                      1 if use_ssl else 0, 1 if is_active else 0, poll_interval_seconds, now_str, monitor_id))
            else:
                monitor_id = f"mon-{uuid.uuid4().hex[:8]}"
                conn.execute("""
                    INSERT INTO email_monitors (
                        id, hr_email, imap_host, imap_port, imap_user, imap_pass,
                        use_ssl, is_active, poll_interval_seconds, last_checked_at, total_processed,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    monitor_id, hr_clean, imap_host, imap_port, imap_user or hr_clean, imap_pass,
                    1 if use_ssl else 0, 1 if is_active else 0, poll_interval_seconds, now_str, 0,
                    now_str, now_str
                ))
            conn.commit()

        return self.get_email_monitor(hr_clean)

    def update_email_monitor_stats(self, hr_email: str, last_checked_at: Optional[str] = None, increment_processed: int = 0) -> None:
        """Update last checked timestamp and increment processed count for an HR monitor."""
        hr_clean = hr_email.lower().strip()
        now_str = last_checked_at or _now_iso()
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE email_monitors
                SET last_checked_at = ?, total_processed = total_processed + ?, updated_at = ?
                WHERE hr_email = ?
            """, (now_str, increment_processed, _now_iso(), hr_clean))
            conn.commit()

    def record_email_ingestion(self, hr_email: str, sender: str, subject: str,
                               candidate_id: str, candidate_name: str, fit_score: float, status: str = "processed") -> Dict[str, Any]:
        """Record an automatically ingested email application."""
        ingest_id = f"eml-{uuid.uuid4().hex[:8]}"
        now_str = _now_iso()
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO email_ingestion_logs (
                    id, hr_email, sender, subject, candidate_id, candidate_name, fit_score, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (ingest_id, hr_email.lower().strip(), sender, subject, candidate_id, candidate_name, fit_score, status, now_str))
            conn.commit()
        return {
            "id": ingest_id,
            "hr_email": hr_email,
            "sender": sender,
            "subject": subject,
            "candidate_id": candidate_id,
            "candidate_name": candidate_name,
            "fit_score": fit_score,
            "status": status,
            "created_at": now_str
        }

    def list_email_ingestions(self, hr_email: Optional[str] = None, limit: int = 25) -> List[Dict[str, Any]]:
        """List recent automatically ingested email applications."""
        with self.get_connection() as conn:
            if hr_email:
                rows = conn.execute("""
                    SELECT * FROM email_ingestion_logs
                    WHERE hr_email = ?
                    ORDER BY created_at DESC LIMIT ?
                """, (hr_email.lower().strip(), limit)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM email_ingestion_logs
                    ORDER BY created_at DESC LIMIT ?
                """, (limit,)).fetchall()
            return [dict(r) for r in rows]


# Singleton Database Instance
db = DatabaseManager()

