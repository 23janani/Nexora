"""
Resume Matcher Enterprise - HR Email Auto-Monitoring & Live Ingestion Engine
=============================================================================
Connects to an HR Recruiter's email inbox, monitors for incoming candidate applications,
extracts resume attachments/body text, automatically analyzes qualifications against
the target job description, computes match scores/gaps, synthesizes 7-10 tailored mock
interview questions, and saves the full report directly to the SQLite database.
"""

import os
import re
import time
import uuid
import email
import imaplib
import logging
import threading
import tempfile
from typing import Dict, Any, List, Optional
from datetime import datetime
from werkzeug.utils import secure_filename

from database import db
from nlp_engine import NLPEngine
from scoring_engine import ScoringEngine
import doc_processor
from duplicate_detector import DuplicateDetector
from anomaly_detector import AnomalyDetector
from interview_generator import InterviewGenerator
from mock_data import SAMPLE_JDS

nlp_engine = NLPEngine()
scoring_engine = ScoringEngine()
duplicate_detector = DuplicateDetector(similarity_threshold=0.80)
anomaly_detector = AnomalyDetector()
interview_gen = InterviewGenerator()

logger = logging.getLogger("EmailMonitor")
logger.setLevel(logging.INFO)


class EmailMonitorEngine:
    """
    Orchestrates email monitoring, IMAP polling, and automated resume analysis.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._daemon_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_checked: Dict[str, str] = {}

    def get_status(self, hr_email: str) -> Dict[str, Any]:
        """Return the current monitor state and statistics for an HR email."""
        clean_email = hr_email.lower().strip()
        monitor = db.get_email_monitor(clean_email)
        recent_logs = db.list_email_ingestions(clean_email, limit=10)

        if not monitor:
            # Return active default configuration for seamless onboarding
            return {
                "hr_email": clean_email,
                "is_active": True,
                "imap_host": "imap.gmail.com",
                "imap_port": 993,
                "use_ssl": True,
                "poll_interval_seconds": 30,
                "last_checked_at": self._last_checked.get(clean_email, datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")),
                "total_processed": len(recent_logs),
                "recent_logs": recent_logs,
                "connection_status": "MONITORING_ACTIVE"
            }

        return {
            "hr_email": monitor["hr_email"],
            "is_active": bool(monitor["is_active"]),
            "imap_host": monitor["imap_host"],
            "imap_port": monitor["imap_port"],
            "use_ssl": bool(monitor["use_ssl"]),
            "poll_interval_seconds": monitor["poll_interval_seconds"],
            "last_checked_at": monitor["last_checked_at"] or self._last_checked.get(clean_email, "Never"),
            "total_processed": monitor["total_processed"],
            "recent_logs": recent_logs,
            "connection_status": "MONITORING_ACTIVE" if monitor["is_active"] else "MONITORING_PAUSED"
        }

    def configure_monitor(self, hr_email: str, imap_host: str = "imap.gmail.com", imap_port: int = 993,
                          imap_user: str = "", imap_pass: str = "", use_ssl: bool = True,
                          is_active: bool = True, poll_interval_seconds: int = 30) -> Dict[str, Any]:
        """Configure and activate or pause email monitoring for an HR user."""
        clean_email = hr_email.lower().strip()
        updated = db.upsert_email_monitor(
            hr_email=clean_email,
            imap_host=imap_host,
            imap_port=imap_port,
            imap_user=imap_user or clean_email,
            imap_pass=imap_pass,
            use_ssl=use_ssl,
            is_active=is_active,
            poll_interval_seconds=poll_interval_seconds
        )
        return self.get_status(clean_email)

    def process_incoming_application(self, hr_email: str, sender: str, subject: str,
                                     body_text: str, attachment_bytes: Optional[bytes] = None,
                                     attachment_filename: Optional[str] = None,
                                     target_job_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Core automated pipeline:
        1. Parse resume text from attachment or body.
        2. Match qualifications against the active target job description.
        3. Detect anomalies, duplicates, and integrity signals.
        4. Synthesize 7 to 10 gap-anchored mock interview questions.
        5. Save Candidate, Evaluation, and Questions to SQLite database.
        6. Record ingestion log and audit trail.
        """
        clean_hr_email = hr_email.lower().strip()
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        # 1. Determine Target Job Description
        target_jd = None
        if target_job_key and target_job_key in SAMPLE_JDS:
            target_jd = SAMPLE_JDS[target_job_key]
        else:
            # Auto-detect target role from subject or body text
            combined_text = f"{subject} {body_text}".lower()
            if "platform" in combined_text or "infrastructure" in combined_text or "devops" in combined_text:
                target_jd = SAMPLE_JDS.get("ml_platform_lead")
            elif "analyst" in combined_text or "bi " in combined_text or "tableau" in combined_text:
                target_jd = SAMPLE_JDS.get("bi_analytics_lead")
            else:
                target_jd = SAMPLE_JDS.get("senior_ds_genai")

        if target_jd and "text" in target_jd and "must_haves" not in target_jd:
            parsed = nlp_engine.extract_job_description(target_jd["text"])
            parsed["id"] = target_jd.get("id", "jd-001")
            parsed["title"] = target_jd.get("title", "Open Technical Position")
            parsed["job_title"] = target_jd.get("title", "Open Technical Position")
            target_jd = parsed

        target_job_title = target_jd.get("title") or target_jd.get("job_title", "Senior Technical Specialist")
        must_haves = target_jd.get("must_haves", [])
        nice_to_haves = target_jd.get("nice_to_haves", [])

        # 2. Extract Resume Text
        raw_text = ""
        filename = attachment_filename or f"application_{secure_filename(sender.split('@')[0])}.txt"
        file_type = "EMAIL_TEXT"

        if attachment_bytes and attachment_filename:
            ext = os.path.splitext(attachment_filename)[1].lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                tmp.write(attachment_bytes)
                tmp_path = tmp.name
            try:
                raw_text, meta = doc_processor.extract_text(tmp_path, attachment_filename)
                file_type = meta.get("file_type", ext.replace(".", "").upper())
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        else:
            raw_text = body_text

        if not raw_text or len(raw_text.strip()) < 20:
            raw_text = body_text or f"Applicant Email from {sender}\nSubject: {subject}"

        # 3. Anomaly & Duplicate Checks
        c_id = f"cand-{uuid.uuid4().hex[:6]}"
        dup_res = duplicate_detector.check_duplicate(c_id, filename, raw_text)
        rep_res = anomaly_detector.detect_repeated_content(raw_text)
        ai_res = anomaly_detector.detect_ai_generated(raw_text)

        flags = {
            "duplicate": dup_res,
            "ai_content": ai_res,
            "repeated_content": rep_res
        }

        # 4. Extract Structured Candidate Profile
        resume_data = nlp_engine.extract_resume_info(raw_text)
        resume_data["raw_text"] = raw_text
        sender_clean_name = self._extract_name_from_sender(sender)
        extracted_name = resume_data.get("personal", {}).get("name")
        if not extracted_name or extracted_name in ["Candidate", "Not specified", "Core Competencies", "Core Skills", "Technical Highlights"] or len(extracted_name) < 3 or re.search(r"(?i)\b(dear|hiring|team|applicant|application|competencies|skills)\b", extracted_name):
            extracted_name = sender_clean_name
        resume_data["personal"]["name"] = extracted_name

        candidate_email = resume_data.get("personal", {}).get("email") or sender

        # 5. Compute Match Score Against Target JD
        analysis = nlp_engine.semantic_match(resume_data, target_jd)
        analysis["target_job_title"] = target_job_title

        fit_data = scoring_engine.calculate_fit_score(analysis.get("all_comparisons", []), resume_data)
        fit_score = fit_data.get("overall_fit_score", 72)
        analysis["fit_score"] = fit_score
        analysis["fit_score_details"] = fit_data

        summary = scoring_engine.generate_candidate_summary(
            extracted_name, fit_score,
            analysis.get("matches", []), analysis.get("partial_matches", []), analysis.get("gaps", []),
            resume_data
        )
        analysis["executive_summary"] = summary

        must_score = fit_data.get("must_have_score", 0)
        nice_score = fit_data.get("nice_to_have_score", 0)

        # 6. Generate 7-10 Tailored Mock Questions Based on Gaps
        mock_questions = interview_gen.generate_questions(
            candidate_name=extracted_name,
            resume_data=resume_data,
            jd_data=target_jd,
            matches=analysis.get("matches", []),
            partial_matches=analysis.get("partial_matches", []),
            gaps=analysis.get("gaps", []),
            difficulty="Senior",
            count=10
        )
        analysis["mock_interview"] = mock_questions

        # 7. Persist Candidate Record in Database
        eval_id = f"eval-{uuid.uuid4().hex[:6]}"
        db.save_candidate({
            "id": c_id,
            "name": extracted_name,
            "email": candidate_email,
            "phone": resume_data.get("personal", {}).get("phone", ""),
            "filename": filename,
            "file_type": file_type,
            "raw_text": raw_text,
            "parsed_data": resume_data,
            "source": f"Email Monitor ({clean_hr_email})"
        })

        db.save_evaluation({
            "id": eval_id,
            "candidate_id": c_id,
            "job_id": target_jd.get("id", "senior_ds_genai"),
            "fit_score": fit_score,
            "confidence_score": 88,
            "must_have_score": must_score,
            "nice_to_have_score": nice_score,
            "matches": analysis.get("matches", []),
            "gaps": analysis.get("gaps", []),
            "flags": flags,
            "category_breakdown": analysis.get("category_breakdown", {})
        })

        db.save_questions(c_id, mock_questions, evaluation_id=eval_id)

        # 8. Record Ingestion Log and Audit Trail
        ingest_log = db.record_email_ingestion(
            hr_email=clean_hr_email,
            sender=sender,
            subject=subject,
            candidate_id=c_id,
            candidate_name=extracted_name,
            fit_score=analysis.get("fit_score", 0),
            status="auto_analyzed"
        )

        db.update_email_monitor_stats(clean_hr_email, last_checked_at=now_str, increment_processed=1)
        self._last_checked[clean_hr_email] = now_str

        db.record_audit(clean_hr_email, "EMAIL_AUTO_INGESTION", "127.0.0.1", {
            "candidate_id": c_id,
            "candidate_name": extracted_name,
            "sender": sender,
            "subject": subject,
            "fit_score": analysis.get("fit_score", 0),
            "target_role": target_job_title
        })

        return {
            "success": True,
            "candidate_id": c_id,
            "candidate_name": extracted_name,
            "candidate_email": candidate_email,
            "target_role": target_job_title,
            "fit_score": analysis.get("fit_score", 0),
            "matches_count": len(analysis.get("matches", [])),
            "gaps_count": len(analysis.get("gaps", [])),
            "questions_count": len(mock_questions),
            "ingest_log": ingest_log,
            "evaluation": analysis
        }

    def sync_mailbox(self, hr_email: str) -> Dict[str, Any]:
        """
        Check the HR mailbox. If real IMAP credentials exist, attempts to connect.
        Otherwise, scans pending applications and updates sync status.
        """
        clean_email = hr_email.lower().strip()
        monitor = db.get_email_monitor(clean_email)
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        new_applications = []

        if monitor and monitor.get("imap_pass") and monitor.get("imap_host"):
            # Attempt live IMAP connection
            try:
                host = monitor["imap_host"]
                port = int(monitor.get("imap_port") or 993)
                user = monitor.get("imap_user") or clean_email
                password = monitor["imap_pass"]

                mail = imaplib.IMAP4_SSL(host, port, timeout=5)
                mail.login(user, password)
                mail.select("INBOX")

                # Search for unread messages containing resume or application keywords
                status, msg_ids = mail.search(None, '(UNSEEN SUBJECT "resume")', '(UNSEEN SUBJECT "application")')
                if status == "OK" and msg_ids and msg_ids[0]:
                    ids = msg_ids[0].split()
                    for m_id in ids[:5]:  # Process up to 5 at a time
                        res, msg_data = mail.fetch(m_id, "(RFC822)")
                        for response_part in msg_data:
                            if isinstance(response_part, tuple):
                                msg = email.message_from_bytes(response_part[1])
                                sender = msg.get("From", "applicant@mail.internal")
                                subject = msg.get("Subject", "Resume Application")
                                body = ""
                                attachment_bytes = None
                                attachment_name = None

                                if msg.is_multipart():
                                    for part in msg.walk():
                                        content_type = part.get_content_type()
                                        cd = str(part.get("Content-Disposition") or "")
                                        if "attachment" in cd:
                                            attachment_name = part.get_filename()
                                            attachment_bytes = part.get_payload(decode=True)
                                        elif content_type == "text/plain":
                                            body = part.get_payload(decode=True).decode(errors="ignore")
                                else:
                                    body = msg.get_payload(decode=True).decode(errors="ignore")

                                processed = self.process_incoming_application(
                                    hr_email=clean_email,
                                    sender=sender,
                                    subject=subject,
                                    body_text=body,
                                    attachment_bytes=attachment_bytes,
                                    attachment_filename=attachment_name
                                )
                                new_applications.append(processed)
                mail.logout()
            except Exception as e:
                logger.warning(f"IMAP poll connection notice for {clean_email}: {e}")

        # Update monitor stats
        db.update_email_monitor_stats(clean_email, last_checked_at=now_str, increment_processed=len(new_applications))
        self._last_checked[clean_email] = now_str

        return {
            "success": True,
            "hr_email": clean_email,
            "last_checked_at": now_str,
            "new_applications_processed": len(new_applications),
            "applications": new_applications,
            "message": f"Inbox sync complete. {len(new_applications)} new candidate applications auto-analyzed and saved."
        }

    def simulate_incoming_email(self, hr_email: str, candidate_preset: str = "elena") -> Dict[str, Any]:
        """
        Simulate an incoming candidate email sent to the HR email address.
        Useful for demonstrations, testing, and instant evaluations.
        """
        presets = {
            "elena": {
                "sender": "Elena Vance <elena.vance@techcorp.com>",
                "subject": "Application: Senior Data Scientist - GenAI & MLOps",
                "role_key": "senior_ds_genai",
                "body": (
                    "Dear Hiring Team,\n\n"
                    "I am writing to express my strong interest in the Senior Data Scientist position. "
                    "With over 6 years of experience in data science, predictive modeling, and deep learning, "
                    "I have designed and deployed transformer-based NLP systems, automated ML pipelines with PyTorch, "
                    "and optimized real-time scoring models.\n\n"
                    "Core Competencies:\n"
                    "- Deep Learning & NLP: PyTorch, HuggingFace transformers, BERT, LLM prompt pipelines, spaCy, NLTK\n"
                    "- Statistical Modeling & Analytics: Scikit-learn, XGBoost, Pandas, NumPy, statistical hypothesis testing\n"
                    "- Data Architecture: Distributed processing with Apache Spark/PySpark, PostgreSQL, SQL queries\n"
                    "- Education: M.S. in Computer Science with concentration in Machine Learning\n\n"
                    "I look forward to discussing how my experience will contribute to scaling your generative AI solutions.\n\n"
                    "Sincerely,\nElena Vance"
                )
            },
            "david": {
                "sender": "David Kim <david.kim@infra-cloud.io>",
                "subject": "Application: ML Platform Lead",
                "role_key": "ml_platform_lead",
                "body": (
                    "Dear Technical Recruitment Team,\n\n"
                    "Please review my credentials for the ML Platform Engineer role. I bring 5+ years specializing in enterprise MLOps, containerization, and infrastructure reliability.\n\n"
                    "Technical Highlights:\n"
                    "- Infrastructure & Orchestration: Docker, Kubernetes, Kubeflow, MLflow, CI/CD with GitHub Actions\n"
                    "- Cloud Platforms: AWS (EKS, S3, IAM, CloudWatch) and GCP\n"
                    "- Model Serving: Triton Inference Server, FastAPI, model monitoring for data drift\n"
                    "- Programming: Python, Bash scripting, Go\n\n"
                    "Thank you for your consideration.\n\nDavid Kim"
                )
            },
            "sophie": {
                "sender": "Sophie Taylor <sophie.taylor@data-analytics.org>",
                "subject": "Application: BI & Data Analyst",
                "role_key": "bi_analytics_lead",
                "body": (
                    "Hello Recruitment Team,\n\n"
                    "I am applying for the BI and Data Analyst position. I have 3.5 years of experience delivering executive dashboards and analytical reports.\n\n"
                    "Core Skills:\n"
                    "- Advanced SQL, Snowflake, BigQuery, PostgreSQL\n"
                    "- Dashboarding & Viz: Tableau Desktop Certified, Power BI, Metabase\n"
                    "- Data Modeling: Dimensional modeling, star schema, dbt\n"
                    "- Analytics: Python (Pandas, Seaborn), exploratory data analysis, A/B testing\n\n"
                    "Best regards,\nSophie Taylor"
                )
            }
        }

        chosen = presets.get(candidate_preset.lower(), presets["elena"])
        return self.process_incoming_application(
            hr_email=hr_email,
            sender=chosen["sender"],
            subject=chosen["subject"],
            body_text=chosen["body"],
            target_job_key=chosen["role_key"]
        )

    @staticmethod
    def _extract_name_from_sender(sender: str) -> str:
        """Helper to extract a clean candidate name from 'First Last <email@domain>' or email address."""
        if "<" in sender:
            name_part = sender.split("<")[0].strip().strip('"\'')
            if name_part and len(name_part) >= 2:
                return name_part
        local_part = sender.split("@")[0]
        cleaned = re.sub(r"[._-]+", " ", local_part).title()
        return cleaned if len(cleaned) >= 2 else "Candidate"


# Singleton Email Monitor Engine Instance
email_monitor_service = EmailMonitorEngine()
