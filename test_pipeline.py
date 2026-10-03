"""
Comprehensive Automated Test Suite for Resume-JD Matching System
Tests document extraction, OCR, duplicate detection, anomaly signals,
semantic matching, fit score explainability, and Flask REST endpoints.
"""

import os
import unittest
from app import app, candidates_store, active_jd
from doc_processor import DocumentProcessor
from duplicate_detector import DuplicateDetector
from anomaly_detector import AnomalyDetector
from nlp_engine import NLPEngine
from scoring_engine import ScoringEngine
from interview_generator import InterviewGenerator


class TestResumeJDSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dp = DocumentProcessor(ocr_engine_path="./ocr_engine")
        cls.dup = DuplicateDetector()
        cls.anomaly = AnomalyDetector()
        cls.nlp = NLPEngine()
        cls.scoring = ScoringEngine()
        cls.interview = InterviewGenerator()
        cls.client = app.test_client()

    def test_01_document_extraction_and_readability(self):
        # Test PDF extraction
        pdf_text, pdf_meta = self.dp.extract_text("sample_files/Resume_Elena_Vance.pdf")
        self.assertTrue(len(pdf_text) > 100)
        self.assertTrue(pdf_meta["quality"]["readable"])

        # Test DOCX extraction
        docx_text, docx_meta = self.dp.extract_text("sample_files/Resume_Elena_Vance.docx")
        self.assertTrue(len(docx_text) > 100)
        self.assertTrue(docx_meta["quality"]["readable"])

        # Test PNG OCR extraction
        png_text, png_meta = self.dp.extract_text("sample_files/Resume_Marcus_Chen.png")
        self.assertTrue(len(png_text) > 50)
        self.assertTrue(png_meta["quality"]["readable"])

        # Test unreadable garbage check
        bad_text = "???\x00\x01\x02" * 20
        bad_res = self.dp.check_readability(bad_text, "corrupt.pdf")
        self.assertFalse(bad_res["readable"])
        self.assertIn("could not be reliably read", bad_res["status"])

    def test_02_duplicate_detection(self):
        txt_a = "Senior Machine Learning Engineer with experience in PyTorch and AWS deployments."
        txt_b = "Senior Machine Learning Engineer with experience in PyTorch and AWS deployments."
        txt_c = "Frontend React developer building web interfaces."

        d1 = self.dup.check_duplicate("1", "Dev A", txt_a)
        self.assertFalse(d1["is_duplicate"])  # First one in repo

        d2 = self.dup.check_duplicate("2", "Dev B", txt_b)
        self.assertTrue(d2["is_duplicate"])
        self.assertGreaterEqual(d2["similarity_score"], 90.0)

        d3 = self.dup.check_duplicate("3", "Dev C", txt_c)
        self.assertFalse(d3["is_duplicate"])

    def test_03_anomaly_and_ai_signals(self):
        spam_text = "Machine learning " * 30 + "Python Python Python " * 20
        spam_res = self.anomaly.detect_repeated_content(spam_text)
        self.assertTrue(spam_res["is_flagged"])

        ai_text = (
            "A results-driven professional showcasing a proven track record of driving impactful business outcomes. "
            "Spearheaded the development of robust and scalable machine learning pipelines that seamlessly integrated with cutting-edge cloud infrastructure. "
            "A testament to innovation, delivering a holistic approach toward predictive analytics. "
            "Played a pivotal role in facilitating cross-functional collaboration across stakeholders."
        )
        ai_res = self.anomaly.detect_ai_generated(ai_text)
        self.assertTrue(ai_res["is_flagged"])
        self.assertIn("Possible AI-generated", ai_res["display_text"])

    def test_04_semantic_matching_not_keyword(self):
        # Resume has 'scikit-learn', JD asks for 'Experience with machine learning model development'
        resume_data = {
            "raw_text": "Built predictive models using scikit-learn for customer risk scoring. Experience with Python, Pandas, NumPy.",
            "skills": {"programming_languages": ["Python"], "ai_ml_skills": ["Machine Learning"]},
            "experience": [{"title": "Data Scientist", "company": "Tech Corp"}],
            "education": [{"degree": "Master's Degree"}],
            "projects": [],
            "certifications": []
        }
        jd_data = {
            "job_title": "Machine Learning Engineer",
            "must_haves": [
                "Experience with machine learning model development and evaluation",
                "Strong Python-based data analysis experience"
            ],
            "nice_to_haves": [
                "Experience with AWS cloud deployment"
            ]
        }
        match_res = self.nlp.semantic_match(resume_data, jd_data)
        matches = match_res["matches"]
        gaps = match_res["gaps"]

        # Ensure scikit-learn semantically matched machine learning model development
        req_texts = [m["requirement"] for m in matches]
        self.assertTrue(any("machine learning model development" in r for r in req_texts))

        # Ensure missing AWS is flagged as GAP
        gap_texts = [g["requirement"] for g in gaps]
        self.assertTrue(any("AWS" in g for g in gap_texts))

    def test_05_scoring_and_confidence(self):
        comparisons = [
            {"requirement": "Python", "is_must_have": True, "category": "Core Technical Skills", "status": "MATCH", "candidate_evidence": "Python expert"},
            {"requirement": "ML", "is_must_have": True, "category": "AI / Machine Learning", "status": "MATCH", "candidate_evidence": "ML expert"},
            {"requirement": "AWS", "is_must_have": True, "category": "Cloud & Infrastructure", "status": "MISSING", "candidate_evidence": ""},
            {"requirement": "Docker", "is_must_have": False, "category": "Cloud & Infrastructure", "status": "PARTIAL", "candidate_evidence": "Basic container knowledge"}
        ]
        resume_data = {
            "skills": {"programming_languages": ["Python"]},
            "experience": [{"title": "Data Scientist"}],
            "education": [{"degree": "M.S."}],
            "projects": [{"name": "Churn Model"}],
            "certifications": []
        }
        fit = self.scoring.calculate_fit_score(comparisons, resume_data)
        self.assertGreater(fit["overall_fit_score"], 0)
        self.assertLessEqual(fit["overall_fit_score"], 100)
        self.assertIn("category_breakdown", fit)

        conf = self.scoring.calculate_confidence({"score": 90, "readable": True}, resume_data, {"must_haves": ["a", "b"], "nice_to_haves": ["c"]}, comparisons)
        self.assertGreaterEqual(conf["confidence_score"], 50)
        self.assertIn("factors", conf)

    def test_06_mock_interview_generation(self):
        qs = self.interview.generate_questions(
            "Dr. Elena Vance",
            {"skills": {"programming_languages": ["Python"]}, "experience": [{"title": "Data Scientist", "company": "Apex Labs"}], "projects": [{"name": "Churn Predictor"}]},
            {"job_title": "Senior Data Scientist"},
            [{"requirement": "Python"}],
            [],
            [{"requirement": "AWS Cloud Deployment"}]
        )
        self.assertGreaterEqual(len(qs), 4)
        for q in qs:
            self.assertIn("question", q)
            self.assertIn("category", q)
            self.assertIn("candidate_coaching", q)
        categories = [q["category"] for q in qs]
        self.assertTrue(any("Missing Skill" in cat or "Gap" in cat for cat in categories))

    def test_07_flask_endpoints(self):
        # Stats
        res = self.client.get("/api/stats")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("total_resumes_processed", data)
        self.assertIn("duplicate_count", data)

        # Candidates list
        res = self.client.get("/api/candidates")
        self.assertEqual(res.status_code, 200)
        candidates = res.get_json()
        self.assertGreaterEqual(len(candidates), 5)

        # Elena Vance candidate detail
        first_id = candidates[0]["id"]
        res = self.client.get(f"/api/candidate/{first_id}")
        self.assertEqual(res.status_code, 200)
        cand_data = res.get_json()
        self.assertIn("analysis", cand_data)
        self.assertIn("fit_score", cand_data["analysis"])
        self.assertIn("mock_interview", cand_data["analysis"])

    def test_08_new_pages_and_governance(self):
        # 1. Terms & Conditions page
        res = self.client.get("/terms")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Terms and Conditions", res.data)

        # 2. Privacy Policy page
        res = self.client.get("/privacy")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Privacy Policy", res.data)

        # 3. Dual-Portal Login (HR and Candidate)
        res_get = self.client.get("/login")
        self.assertEqual(res_get.status_code, 200)
        self.assertIn(b"Enterprise Assessor Sign In", res_get.data)
        self.assertIn(b"HR / Recruiter Portal", res_get.data)
        self.assertIn(b"Candidate / User Portal", res_get.data)

        # Test HR Login
        res_post_hr = self.client.post("/login", data={"portal_type": "hr", "email": "hr.evaluator@recruitment.internal", "role": "Lead Data Scientist"})
        self.assertEqual(res_post_hr.status_code, 302)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["user"]["user_type"], "hr")

        # Test Candidate Login
        res_post_cand = self.client.post("/login", data={"portal_type": "candidate", "name": "Elena Vance", "email": "elena.vance@mit.edu", "track": "GenAI & MLOps"})
        self.assertEqual(res_post_cand.status_code, 302)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["user"]["user_type"], "candidate")
            self.assertEqual(sess["user"]["name"], "Elena Vance")

        # 4. Custom domain config
        res_domain = self.client.get("/api/domain-config")
        self.assertEqual(res_domain.status_code, 200)
        self.assertIn("domain", res_domain.get_json())

        res_update = self.client.post("/api/domain-config", json={"domain": "talent.corp.internal"})
        self.assertEqual(res_update.status_code, 200)
        self.assertEqual(res_update.get_json()["domain"], "talent.corp.internal")

        # 5. Favicon exists
        res_favicon = self.client.get("/static/favicon.svg")
        self.assertEqual(res_favicon.status_code, 200)

    def test_09_incoming_email_processing(self):
        # 1. Email with text body
        res = self.client.post("/api/incoming-email", data={
            "sender": "Arun Kumar <arun.kumar@gmail.com>",
            "subject": "Application for Senior Data Scientist - GenAI & MLOps",
            "body": (
                "Dear Hiring Manager,\n"
                "I am applying for the Senior Data Scientist position. I have 4 years of experience "
                "in Python, Pandas, Scikit-learn, SQL, and building predictive models."
            ),
            "job_id": "senior_ds_genai"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        cand = data["candidate"]
        self.assertEqual(cand["name"], "Arun Kumar")
        self.assertEqual(cand["source"], "Email Application")
        self.assertGreater(cand["fit_score"], 0)

        # 2. Email with attachment file
        if os.path.exists("sample_files/Resume_Marcus_Chen.txt"):
            with open("sample_files/Resume_Marcus_Chen.txt", "rb") as f:
                res_file = self.client.post("/api/incoming-email", data={
                    "sender": "marcus.chen@email.com",
                    "subject": "Application: ML Platform Lead",
                    "resume": (f, "Resume_Marcus_Chen.txt")
                })
            self.assertEqual(res_file.status_code, 200)
            data_file = res_file.get_json()
            self.assertTrue(data_file["success"])
            self.assertIn("Marcus Chen", data_file["candidate"]["name"])

    def test_10_user_mode_gap_based_questions(self):
        # 1. Candidate / User mode analysis
        sample_resume_text = (
            "MARCUS CHEN\n"
            "Data Scientist with 4 years industry experience in Python, Pandas, Scikit-learn, SQL.\n"
            "Built classification models, regression, clustering, exploratory data analysis.\n"
            "B.S. in Statistics, UC Berkeley."
        )
        res = self.client.post("/api/user-analyze", data={
            "resume_text": sample_resume_text,
            "preset_role": "senior_ds_genai"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("Marcus Chen", data["candidate_name"])
        self.assertGreater(data["fit_score"], 0)
        self.assertGreater(len(data["gaps"]), 0)

        # Verify 7 to 10 Questions formulated from gaps
        questions = data["questions"]
        self.assertGreaterEqual(len(questions), 7)
        self.assertLessEqual(len(questions), 10)

        for q in questions:
            self.assertIn("question", q)
            self.assertIn("category", q)
            self.assertIn("evaluation_hint", q)
            self.assertIn("candidate_coaching", q)
            self.assertTrue(len(q["candidate_coaching"]) > 10)

        # 2. Export Candidate Interview Prep PDF
        res_pdf = self.client.post("/api/export-user-prep", json=data)
        self.assertEqual(res_pdf.status_code, 200)
        self.assertEqual(res_pdf.mimetype, "application/pdf")
        self.assertTrue(res_pdf.data.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()

