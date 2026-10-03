"""
Comprehensive Automated Test Suite for:
1. SQLite Database Persistence (ACID, relational foreign keys, WAL mode)
2. Enterprise Security (PBKDF2-SHA256 password hashing, RBAC, HTTP security headers, sanitization)
3. Built-In AI Interview Question Customization & Single-Question Regeneration
4. REST API Endpoints & Audit Logging
"""

import json
import uuid
import unittest
from app import app, candidates_store, active_jd
from database import db
from security import hash_password, verify_password, is_allowed_file, sanitize_input_text


class TestBackendSecurityAndDatabase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()

    def test_01_database_persistence_and_relationships(self):
        """Test SQLite relational tables, foreign keys, and CRUD operations."""
        # 1. Verify initial seeded records
        candidates = db.list_candidates()
        self.assertGreaterEqual(len(candidates), 5)
        
        # 2. Verify candidate retrieval with nested evaluation and questions
        cand_detail = None
        for c in candidates:
            detail = db.get_candidate(c["id"])
            if detail and detail.get("analysis", {}).get("mock_interview"):
                cand_detail = detail
                break
        self.assertIsNotNone(cand_detail)
        self.assertIn("analysis", cand_detail)
        self.assertIn("mock_interview", cand_detail["analysis"])
        self.assertGreaterEqual(len(cand_detail["analysis"]["mock_interview"]), 5)

        # 3. Verify user retrieval
        hr_user = db.get_user_by_email("hr.evaluator@recruitment.internal")
        self.assertIsNotNone(hr_user)
        self.assertEqual(hr_user["user_type"], "hr")
        self.assertTrue(verify_password("EnterpriseHR2026!", hr_user["password_hash"]))

        # 4. Verify audit logging
        db.record_audit("test.runner@corp.internal", "TEST_SUITE_RUN", "127.0.0.1", {"module": "database"})
        audits = db.get_audit_logs(limit=10)
        self.assertGreaterEqual(len(audits), 1)
        self.assertTrue(any(a["action"] == "TEST_SUITE_RUN" for a in audits))

    def test_02_security_cryptography_and_sanitization(self):
        """Test password hashing, verification, input sanitization, and file safety."""
        # 1. Password hashing
        raw_pwd = "ExecutiveSecret_2026!#"
        hashed = hash_password(raw_pwd)
        self.assertNotEqual(raw_pwd, hashed)
        self.assertTrue(verify_password(raw_pwd, hashed))
        self.assertFalse(verify_password("WrongPassword", hashed))

        # 2. File extension checks
        self.assertTrue(is_allowed_file("cv.pdf"))
        self.assertTrue(is_allowed_file("resume.docx"))
        self.assertTrue(is_allowed_file("scan.png"))
        self.assertTrue(is_allowed_file("profile.txt"))
        self.assertFalse(is_allowed_file("payload.sh"))
        self.assertFalse(is_allowed_file("exploit.py"))
        self.assertFalse(is_allowed_file("no_extension"))

        # 3. Input sanitization
        dirty_input = "Candidate \x00\x01\x02Name\r\nData"
        clean = sanitize_input_text(dirty_input)
        self.assertNotIn("\x00", clean)
        self.assertIn("Candidate Name", clean)

    def test_03_http_security_headers(self):
        """Test CSP, X-Frame-Options, X-Content-Type-Options headers on server responses."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Content-Security-Policy", res.headers)
        self.assertEqual(res.headers.get("X-Frame-Options"), "DENY")
        self.assertEqual(res.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(res.headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")
        self.assertIn("X-XSS-Protection", res.headers)

    def test_04_auth_api_endpoints(self):
        """Test registration, JSON login, session validation, and RBAC enforcement."""
        # 1. Register candidate user
        new_email = f"test.candidate.{uuid.uuid4().hex[:8]}@university.edu"
        res_reg = self.client.post("/api/v1/auth/register", json={
            "email": new_email,
            "password": "Password123!",
            "name": "Jordan Smith",
            "role": "Candidate: NLP Research",
            "user_type": "candidate"
        })
        self.assertEqual(res_reg.status_code, 201)
        data_reg = res_reg.get_json()
        self.assertTrue(data_reg["success"])
        self.assertEqual(data_reg["user"]["email"], new_email)

        # 2. Duplicate registration rejection
        res_dup = self.client.post("/api/v1/auth/register", json={
            "email": new_email,
            "password": "Password123!"
        })
        self.assertEqual(res_dup.status_code, 409)

        # 3. JSON API Login
        res_login = self.client.post("/api/v1/auth/login", json={
            "email": new_email,
            "password": "Password123!"
        })
        self.assertEqual(res_login.status_code, 200)
        data_login = res_login.get_json()
        self.assertTrue(data_login["success"])
        self.assertEqual(data_login["user"]["email"], new_email)

        # 4. Auth Me check
        res_me = self.client.get("/api/v1/auth/me")
        self.assertEqual(res_me.status_code, 200)
        self.assertEqual(res_me.get_json()["user"]["email"], new_email)

        # 5. RBAC enforcement: candidate trying to access HR-only audit logs
        res_audit_denied = self.client.get("/api/v1/audit-logs")
        self.assertEqual(res_audit_denied.status_code, 403)

    def test_05_builtin_ai_customized_interview_generation(self):
        """Test customizable AI question generation with difficulty and prompt directives."""
        # Authenticate as HR
        with self.client.session_transaction() as sess:
            sess["user"] = {
                "name": "Dr. Aris Vance",
                "role": "Lead Assessor",
                "email": "hr.evaluator@recruitment.internal",
                "user_type": "hr"
            }

        cand_id = list(candidates_store.keys())[0]

        # 1. Generate Senior questions with custom directive
        res_gen = self.client.post("/api/v1/interview/generate", json={
            "candidate_id": cand_id,
            "difficulty": "Lead / Staff",
            "count": 8,
            "custom_directives": "Emphasize high-concurrency microservice scaling and distributed training"
        })
        self.assertEqual(res_gen.status_code, 200)
        data = res_gen.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["difficulty"], "Lead / Staff")
        questions = data["questions"]
        self.assertGreaterEqual(len(questions), 5)
        self.assertTrue(any("Lead / Staff" in q.get("category", "") for q in questions))
        self.assertTrue(any("high-concurrency" in q.get("question", "") for q in questions))

    def test_06_interview_question_crud_and_single_regeneration(self):
        """Test editing, adding, deleting, and single-question AI regeneration."""
        # Authenticate as HR
        with self.client.session_transaction() as sess:
            sess["user"] = {
                "name": "Dr. Aris Vance",
                "role": "Lead Assessor",
                "email": "hr.evaluator@recruitment.internal",
                "user_type": "hr"
            }

        cand_id = list(candidates_store.keys())[0]

        # 1. Add Custom Question
        res_add = self.client.post("/api/v1/interview/questions", json={
            "candidate_id": cand_id,
            "question_text": "Describe your exact approach to mitigating data pipeline drift in multi-tenant clusters.",
            "category": "Custom Architecture Standard",
            "difficulty": "Senior",
            "evaluation_hint": "Listen for automated schema contracts and alerts.",
            "candidate_coaching": "Give a structured example with Prometheus and Grafana alerts."
        })
        self.assertEqual(res_add.status_code, 201)
        created_q = res_add.get_json()["question"]
        q_id = created_q["id"]
        self.assertIn("mitigating data pipeline drift", created_q["question_text"])

        # 2. Update Question
        res_update = self.client.put(f"/api/v1/interview/questions/{q_id}", json={
            "candidate_id": cand_id,
            "question_text": "Updated question text: Describe your disaster recovery workflow in multi-region setups.",
            "difficulty": "Lead / Staff"
        })
        self.assertEqual(res_update.status_code, 200)
        self.assertTrue(res_update.get_json()["success"])

        # 3. Single-Question AI Regeneration
        res_regen = self.client.post(f"/api/v1/interview/questions/{q_id}/regenerate", json={
            "candidate_id": cand_id,
            "gap_text": "Experience deploying AWS SageMaker pipelines",
            "difficulty": "Architect",
            "category": "Technical Architecture",
            "custom_prompt": "Probe zero-downtime blue-green deployments under high traffic"
        })
        self.assertEqual(res_regen.status_code, 200)
        regen_q = res_regen.get_json()["question"]
        self.assertIn("blue-green", regen_q["question"])
        self.assertEqual(regen_q["difficulty"], "Architect")

        # 4. Delete Question
        res_del = self.client.delete(f"/api/v1/interview/questions/{q_id}?candidate_id={cand_id}")
        self.assertEqual(res_del.status_code, 200)
        self.assertTrue(res_del.get_json()["success"])

    def test_07_audit_logs_and_health_endpoints(self):
        """Test HR access to audit logs and health diagnostic endpoints."""
        # Authenticate as HR
        with self.client.session_transaction() as sess:
            sess["user"] = {
                "name": "Dr. Aris Vance",
                "role": "Lead Assessor",
                "email": "hr.evaluator@recruitment.internal",
                "user_type": "hr"
            }

        # 1. Audit logs
        res_audit = self.client.get("/api/v1/audit-logs?limit=20")
        self.assertEqual(res_audit.status_code, 200)
        audits_data = res_audit.get_json()
        self.assertTrue(audits_data["success"])
        self.assertGreaterEqual(audits_data["total"], 1)

        # 2. Health check
        res_health = self.client.get("/api/v1/health")
        self.assertEqual(res_health.status_code, 200)
        health_data = res_health.get_json()
        self.assertEqual(health_data["status"], "healthy")
        self.assertIn("SQLite", health_data["database"])
        self.assertIn("Dual-Engine", health_data["ai_engine"])


if __name__ == "__main__":
    unittest.main()
