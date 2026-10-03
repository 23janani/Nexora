#!/usr/bin/env python3
"""
Automated End-to-End Verification Test Suite for:
FEATURE 1 - Smart Interview Scheduling (Google Calendar / Meet / Slots / AI Summary / RBAC)
FEATURE 2 - AI Career Roadmap & Role Benchmarks (3-Phase Milestones / Live Gauge / What-If Simulator / N>=20 Privacy / PDF Export)
"""

import sys
import json
import unittest
from datetime import datetime, timedelta
import app as flask_app
from database import db

class TestFeatures1And2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = flask_app.app.test_client()
        db.save_candidate({
            'id': 'cand-elena',
            'name': 'Elena Vance',
            'email': 'elena.vance@example.com'
        })
        db.save_candidate({
            'id': 'cand-marcus',
            'name': 'Marcus Chen',
            'email': 'marcus.chen@example.com'
        })

    def set_hr_session(self):
        with self.client.session_transaction() as sess:
            sess['user'] = {
                'id': 'hr_eval_01',
                'email': 'recruiter@enterprise.com',
                'name': 'Enterprise Recruiter',
                'role': 'Recruiter',
                'user_type': 'hr'
            }

    def set_candidate_session(self):
        with self.client.session_transaction() as sess:
            sess['user'] = {
                'id': 'cand_eval_01',
                'email': 'candidate@test.com',
                'name': 'Candidate User',
                'role': 'Candidate',
                'user_type': 'candidate'
            }

    def clear_session(self):
        with self.client.session_transaction() as sess:
            sess.clear()

    def test_01_calendar_status_and_sandbox_connect(self):
        """Feature 1: Test Google Calendar OAuth status & sandbox connection."""
        self.set_hr_session()
        res = self.client.get('/api/v1/calendar/status')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('connected', data)

        # Connect sandbox calendar
        conn_res = self.client.post('/api/v1/calendar/sandbox-connect')
        self.assertEqual(conn_res.status_code, 200)
        conn_data = conn_res.get_json()
        self.assertTrue(conn_data.get('success'))
        self.assertIn('details', conn_data)

    def test_02_available_slots_suggestion(self):
        """Feature 1: Test available slot query with duration."""
        self.set_hr_session()
        target_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        res = self.client.get(f'/api/v1/interviews/available-slots?date={target_date}&duration=45')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))
        self.assertGreater(len(data.get('slots', [])), 0)
        first_slot = data['slots'][0]
        self.assertIn('start_iso', first_slot)
        self.assertIn('meet_preview', first_slot)
        self.assertTrue(first_slot['meet_preview'].startswith('https://meet.google.com/'))

    def test_03_interview_rbac_protection(self):
        """Feature 1: Ensure @role_required(['hr']) blocks candidate users with 403 Forbidden."""
        self.set_candidate_session()
        slot_time = (datetime.now() + timedelta(days=2)).isoformat()
        res = self.client.post('/api/v1/interviews', json={
            'candidate_id': 'cand-elena',
            'scheduled_at': slot_time,
            'duration_minutes': 45
        })
        self.assertEqual(res.status_code, 403)
        data = res.get_json()
        self.assertIn('Access denied', data.get('error', ''))

    def test_04_schedule_interview_and_auto_embed_questions(self):
        """Feature 1: Recruiter schedules interview with auto-embedded AI questions."""
        self.set_hr_session()
        slot_time = (datetime.now() + timedelta(days=2)).replace(hour=14, minute=0, second=0).isoformat()
        res = self.client.post('/api/v1/interviews', json={
            'candidate_id': 'cand-elena',
            'scheduled_at': slot_time,
            'duration_minutes': 45,
            'notes': 'Deep dive on PyTorch transformer architectures and distributed GPU training.',
            'include_ai_questions': True
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))
        interview = data['interview']
        self.assertEqual(interview['status'], 'scheduled')
        self.assertTrue(interview['meeting_link'].startswith('https://meet.google.com/'))
        self.assertIn('questions', interview)
        self.assertGreater(len(interview['questions']), 0)

        # Store interview ID for subsequent tests
        TestFeatures1And2.interview_id = interview['id']

    def test_05_interview_reschedule_cancel_and_reminder(self):
        """Feature 1: Test reschedule, reminder dispatch, and cancel."""
        self.set_hr_session()
        int_id = getattr(TestFeatures1And2, 'interview_id', None)
        self.assertIsNotNone(int_id)

        # Reschedule
        new_time = (datetime.now() + timedelta(days=3)).replace(hour=10, minute=0).isoformat()
        res_resched = self.client.put(f'/api/v1/interviews/{int_id}/reschedule', json={
            'scheduled_at': new_time,
            'duration_minutes': 60
        })
        self.assertEqual(res_resched.status_code, 200)
        self.assertEqual(res_resched.get_json()['interview']['status'], 'rescheduled')

        # Send reminder
        res_remind = self.client.post(f'/api/v1/interviews/{int_id}/reminder')
        self.assertEqual(res_remind.status_code, 200)
        self.assertTrue(res_remind.get_json()['success'])

        # Cancel
        res_cancel = self.client.post(f'/api/v1/interviews/{int_id}/cancel', json={
            'reason': 'Candidate requested rescheduled date.'
        })
        self.assertEqual(res_cancel.status_code, 200)
        self.assertEqual(res_cancel.get_json()['interview']['status'], 'cancelled')

    def test_06_interview_feedback_and_ai_summary(self):
        """Feature 1: Test post-interview evaluator rating and AI summary synthesis."""
        self.set_hr_session()
        slot_time = (datetime.now() + timedelta(days=1)).isoformat()
        res_create = self.client.post('/api/v1/interviews', json={
            'candidate_id': 'cand-marcus',
            'scheduled_at': slot_time,
            'duration_minutes': 45,
            'include_ai_questions': True
        })
        self.assertEqual(res_create.status_code, 200)
        int_id = res_create.get_json()['interview']['id']

        # Submit feedback
        res_fb = self.client.post(f'/api/v1/interviews/{int_id}/feedback', json={
            'rating': 4.5,
            'notes': 'Candidate clearly explained distributed data pipelines and database indexing tradeoffs. Addressed machine learning gaps with sound theoretical logic.'
        })
        self.assertEqual(res_fb.status_code, 200)
        data = res_fb.get_json()
        self.assertTrue(data.get('success'))
        self.assertIn('ai_summary', data)
        self.assertTrue(len(data['ai_summary']) > 20)
        self.assertIn('recommendation', data['ai_summary'].lower())

    def test_07_roadmap_generation_3_phases(self):
        """Feature 2: Generate 3-phase Career Roadmap with foundational, applied, and mastery items."""
        sample_gaps = [
            {'requirement': 'Production PyTorch Distributed Training (DDP)', 'reason': 'Resume exhibits Scikit-learn and LightGBM only.'},
            {'requirement': 'Kubernetes & Docker Container Orchestration', 'reason': 'Basic Docker usage noted, no Kubernetes cluster operations.'},
            {'requirement': 'Real-time Vector Databases & RAG Pipelines', 'reason': 'Relational SQL experience present, no vector store integration.'}
        ]

        res = self.client.post('/api/v1/roadmaps/generate', json={
            'candidate_id': 'cand_test_candidate',
            'job_title': 'Senior Generative AI & Data Platform Engineer',
            'fit_score': 62.0,
            'gaps': sample_gaps
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))
        roadmap = data['roadmap']
        items = data['items']

        self.assertEqual(roadmap['target_role'], 'Senior Generative AI & Data Platform Engineer')
        self.assertEqual(roadmap['baseline_score'], 62.0)
        self.assertGreaterEqual(roadmap['current_readiness'], 62.0)

        # Verify phases exist
        phases = set(it['phase'] for it in items)
        self.assertTrue({'foundational', 'applied', 'interview_ready'}.issubset(phases))

        # Verify milestone attributes: priority, estimated hours, rationales
        for it in items:
            self.assertIn('title', it)
            self.assertIn(it['priority'], ['critical', 'high', 'medium'])
            self.assertGreater(it['estimated_hours'], 0)
            self.assertIn('recommendation_reason', it)

        TestFeatures1And2.roadmap_id = roadmap['id']
        TestFeatures1And2.roadmap_items = items

    def test_08_milestone_toggle_and_live_readiness_recalculation(self):
        """Feature 2: Toggle milestone item completion and verify dynamic readiness gauge."""
        items = getattr(TestFeatures1And2, 'roadmap_items', [])
        self.assertGreater(len(items), 0)
        first_item = items[0]

        # Toggle to completed
        res_toggle = self.client.patch(f'/api/v1/roadmaps/items/{first_item["id"]}/toggle')
        self.assertEqual(res_toggle.status_code, 200)
        data_toggle = res_toggle.get_json()
        self.assertTrue(data_toggle.get('success'))
        self.assertEqual(data_toggle.get('is_completed'), 1)
        self.assertGreater(data_toggle.get('current_readiness'), 62.0)

        # Toggle back to uncompleted
        res_untoggle = self.client.patch(f'/api/v1/roadmaps/items/{first_item["id"]}/toggle')
        self.assertEqual(res_untoggle.status_code, 200)
        data_untoggle = res_untoggle.get_json()
        self.assertEqual(data_untoggle.get('is_completed'), 0)
        self.assertEqual(data_untoggle.get('current_readiness'), 62.0)

    def test_09_what_if_skill_simulation(self):
        """Feature 2: Test Interactive Simulator 'What if I improve this skill?'."""
        roadmap_id = getattr(TestFeatures1And2, 'roadmap_id', None)
        res = self.client.post('/api/v1/roadmaps/simulate-skill', json={
            'baseline_score': 62.0,
            'target_skill': 'Production PyTorch Distributed Training (DDP)',
            'roadmap_id': roadmap_id
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))
        self.assertGreater(data.get('projected_score'), 62.0)
        self.assertGreater(data.get('readiness_boost'), 0)
        self.assertIn('recommended_action', data)

    def test_10_role_benchmarks_privacy_gating(self):
        """Feature 2: Test anonymized role benchmarks with strict N >= 20 privacy gating."""
        # 1. Test role with fewer than 20 candidates (insufficient data)
        res_sparse = self.client.get('/api/v1/benchmarks?job_title=Quantum Computing Research Architect&candidate_score=75')
        self.assertEqual(res_sparse.status_code, 200)
        data_sparse = res_sparse.get_json()
        self.assertEqual(data_sparse.get('status'), 'insufficient_data')
        self.assertLess(data_sparse.get('sample_size'), 20)
        self.assertIn('minimum 20 candidates required', data_sparse.get('message', '').lower())

        # 2. Seed 25 benchmark evaluations to test active cohort calculation (N >= 20)
        benchmark_job_id = 'job_bench_role_ds'
        benchmark_role = 'Benchmark Senior Data Scientist'
        db.save_job(
            job_id=benchmark_job_id,
            title=benchmark_role,
            department='Engineering',
            experience_level='Senior',
            must_haves=['Python', 'SQL', 'PyTorch'],
            nice_to_haves=['Docker', 'AWS']
        )

        for i in range(25):
            c_id = f'cand_bench_{i}'
            db.save_candidate({
                'id': c_id,
                'name': f'Benchmark Candidate {i}',
                'email': f'bench_{i}@example.com'
            })
            score = 50.0 + (i * 1.8)
            db.save_evaluation({
                'id': f'eval_bench_{i}',
                'candidate_id': c_id,
                'job_id': benchmark_job_id,
                'fit_score': score,
                'confidence_score': 88.0,
                'must_have_score': score * 0.8,
                'nice_to_have_score': score * 0.9,
                'category_breakdown': {'Core ML': score, 'NLP': score * 0.9}
            })

        res_active = self.client.get(f'/api/v1/benchmarks?job_title={benchmark_role}&candidate_score=78.0')
        self.assertEqual(res_active.status_code, 200)
        data_active = res_active.get_json()
        self.assertIn(data_active.get('status'), ['active', 'ready'])
        self.assertGreaterEqual(data_active.get('sample_size'), 20)
        self.assertIn('percentile', data_active)
        self.assertIn('median_score', data_active)
        self.assertIn('p75_score', data_active)
        # Ensure zero candidate PII / names are exposed in benchmarks output
        self.assertNotIn('Benchmark Candidate', str(data_active))
        self.assertNotIn('bench_', str(data_active))

    def test_11_roadmap_pdf_export(self):
        """Feature 2: Test ReportLab vector PDF export for the Career Roadmap."""
        roadmap_id = getattr(TestFeatures1And2, 'roadmap_id', None)
        self.assertIsNotNone(roadmap_id)

        res = self.client.get(f'/api/v1/roadmaps/{roadmap_id}/export-pdf')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content_type, 'application/pdf')
        self.assertTrue(res.data.startswith(b'%PDF-'))
        self.assertGreater(len(res.data), 1000)

if __name__ == '__main__':
    unittest.main()
