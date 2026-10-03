"""
AI Career Roadmap & Role Benchmarking Engine
Synthesizes candidate requirement gaps into a 3-Phase structured roadmap:
  Phase 1: Foundational Core (Theory, syntax, primary frameworks)
  Phase 2: Applied Engineering (Production pipelines, deployment, integration)
  Phase 3: Interview-Ready Mastery (System design, trade-offs, mock drills)
Includes "Why this recommendation?" rationales, live readiness tracking,
anonymized role benchmarks with N >= 20 privacy gating, and "What-if" skill projection.
Strict compliance: zero emojis, zero em dashes, rectangular radii, corporate palette.
"""

import os
import re
import uuid
import json
import logging
from typing import Dict, Any, List, Optional
from database import db

logger = logging.getLogger("RoadmapEngine")


class RoadmapEngine:
    def __init__(self):
        pass

    def generate_roadmap(
        self,
        candidate_name: str,
        job_title: str,
        baseline_readiness: float,
        gaps: List[Dict[str, Any]],
        partial_matches: Optional[List[Dict[str, Any]]] = None,
        resume_data: Optional[Dict[str, Any]] = None,
        candidate_id: Optional[str] = None,
        evaluation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Synthesizes a 3-phase career roadmap from identified requirement gaps.
        Distributes missing competencies into Foundational, Applied, and Interview-Ready phases.
        """
        partial_matches = partial_matches or []
        resume_data = resume_data or {}

        items: List[Dict[str, Any]] = []
        roadmap_id = f"rdm_{uuid.uuid4().hex[:12]}"

        # Combine gaps and partial matches for comprehensive roadmap coverage
        targeted_needs: List[Dict[str, Any]] = []
        for g in gaps:
            targeted_needs.append({
                "requirement": g.get("requirement", "Technical Requirement"),
                "category": g.get("category", "Core Competency"),
                "importance": g.get("importance", "MUST-HAVE"),
                "is_partial": False
            })
        for p in partial_matches:
            targeted_needs.append({
                "requirement": p.get("requirement", "Technical Requirement"),
                "category": p.get("category", "Applied Competency"),
                "importance": p.get("importance", "PREFERRED"),
                "is_partial": True
            })

        # If no gaps recorded, provide mastery and high-scale architecture tracks
        if not targeted_needs:
            targeted_needs = [
                {"requirement": "High-Throughput Distributed System Scaling", "category": "Architecture", "importance": "MUST-HAVE", "is_partial": False},
                {"requirement": "Fault-Tolerant Enterprise MLOps Orchestration", "category": "DevOps", "importance": "PREFERRED", "is_partial": False}
            ]

        # Calculate readiness impact per item so completing all milestones bridges the gap to 95-100%
        remaining_points = max(10.0, 100.0 - baseline_readiness)
        count = len(targeted_needs)
        base_impact = round(remaining_points / (count * 3 if count <= 3 else count), 1)

        milestone_counter = 1

        for need in targeted_needs:
            req = need["requirement"]
            cat = need["category"]
            is_must_have = (need["importance"] == "MUST-HAVE")
            prio = "critical" if is_must_have else "high"

            # -------------------------------------------------------------
            # Phase 1: Foundational Core
            # -------------------------------------------------------------
            f_title = f"{req}: Foundational Principles & Architecture"
            f_desc = f"Master theoretical fundamentals, core APIs, and configuration schemas for {req}. Build isolated modular components."
            f_reason = (
                f"Your evaluation identified '{req}' as a {need['importance']} requirement for the {job_title} role. "
                f"Establishing solid foundational fluency ensures you can reason accurately about design primitives during technical screening."
            )
            items.append({
                "id": f"rmi_{uuid.uuid4().hex[:10]}",
                "phase": "foundational",
                "skill": req,
                "title": f_title,
                "description": f_desc,
                "recommendation_reason": f_reason,
                "priority": prio,
                "prerequisites": ["Python Core Syntax", "System CLI Navigation"],
                "estimated_hours": 12 if is_must_have else 8,
                "resource_types": ["Official Documentation", "Architectural Reference Guide", "Hands-on Lab"],
                "readiness_impact_pct": max(2.0, round(base_impact * 0.9, 1)),
                "is_completed": 0,
                "sort_order": milestone_counter
            })
            milestone_counter += 1

            # -------------------------------------------------------------
            # Phase 2: Applied Engineering
            # -------------------------------------------------------------
            a_title = f"{req}: End-to-End Production Pipeline Implementation"
            a_desc = f"Integrate {req} into a full CI/CD deployment or streaming pipeline with automated health checks, logging, and error recovery."
            a_reason = (
                f"Recruiters evaluate applied execution over theoretical knowledge. Building a functioning production project with {req} "
                f"provides verifiable evidence to discuss in the hiring manager interview."
            )
            items.append({
                "id": f"rmi_{uuid.uuid4().hex[:10]}",
                "phase": "applied",
                "skill": req,
                "title": a_title,
                "description": a_desc,
                "recommendation_reason": a_reason,
                "priority": "high",
                "prerequisites": [f"{req} Foundational Principles", "Docker Containerization"],
                "estimated_hours": 18 if is_must_have else 12,
                "resource_types": ["Open-Source Template Project", "Production Cloud Deployment", "Unit & Integration Tests"],
                "readiness_impact_pct": max(2.5, round(base_impact * 1.1, 1)),
                "is_completed": 0,
                "sort_order": milestone_counter
            })
            milestone_counter += 1

            # -------------------------------------------------------------
            # Phase 3: Interview-Ready Mastery
            # -------------------------------------------------------------
            i_title = f"{req}: System Design Trade-Offs & Mock Defense"
            i_desc = f"Practice defending architectural trade-offs, failure recovery scenarios, and scalability bottlenecks involving {req} under interview conditions."
            i_reason = (
                f"Senior-level technical assessors specifically test edge cases and alternative tooling trade-offs for {req}. "
                f"Structured mock drill prepares you to articulate concrete STAR-method rationales."
            )
            items.append({
                "id": f"rmi_{uuid.uuid4().hex[:10]}",
                "phase": "interview_ready",
                "skill": req,
                "title": i_title,
                "description": i_desc,
                "recommendation_reason": i_reason,
                "priority": "medium",
                "prerequisites": [f"{req} Applied Pipeline"],
                "estimated_hours": 8,
                "resource_types": ["System Design Architecture Interview Drill", "Failure Recovery Playbook"],
                "readiness_impact_pct": max(1.5, round(base_impact * 0.8, 1)),
                "is_completed": 0,
                "sort_order": milestone_counter
            })
            milestone_counter += 1

        summary = (
            f"Strategic 3-phase career readiness roadmap tailored for {candidate_name} targeting {job_title}. "
            f"Focuses on bridging {len(gaps)} primary requirement gaps through sequential theoretical foundations, "
            f"verifiable applied production engineering, and senior-level interview architectural defense."
        )

        # Persist to database
        saved_roadmap = db.create_roadmap(
            roadmap_id=roadmap_id,
            candidate_id=candidate_id,
            evaluation_id=evaluation_id,
            job_title=job_title,
            baseline_readiness=baseline_readiness,
            summary=summary,
            items=items,
            candidate_name=candidate_name
        )

        return saved_roadmap

    # =========================================================================
    # WHAT-IF SKILL IMPROVEMENT PROJECTION SIMULATOR
    # =========================================================================

    def simulate_skill_improvement(
        self,
        current_fit_score: float,
        target_skill: str,
        gaps: List[Dict[str, Any]],
        job_title: str = "Target Position"
    ) -> Dict[str, Any]:
        """
        Simulate candidate readiness if a specific missing requirement is bridged.
        Projects new fit score, gap status transition, and unlocked capabilities.
        """
        matching_gap = None
        for g in gaps:
            if target_skill.lower() in g.get("requirement", "").lower() or g.get("requirement", "").lower() in target_skill.lower():
                matching_gap = g
                break

        is_must_have = matching_gap.get("importance") == "MUST-HAVE" if matching_gap else True

        # Must-Have gap transition gives a larger percentage boost
        score_boost = round(12.0 if is_must_have else 6.0, 1)
        projected_score = min(100.0, round(current_fit_score + score_boost, 1))

        # Determine unlocked architectural capabilities
        capabilities = [
            f"Directly satisfies target job requirement for '{target_skill}'.",
            f"Elevates technical qualification tier from {current_fit_score}% to {projected_score}%.",
            f"Converts critical interview vulnerability into a demonstrable project strength during assessor probing.",
            f"Positions candidate favorably against role cohort benchmarks."
        ]

        return {
            "target_skill": target_skill,
            "baseline_score": current_fit_score,
            "projected_score": projected_score,
            "score_delta": score_boost,
            "importance": "MUST-HAVE" if is_must_have else "PREFERRED",
            "unlocked_capabilities": capabilities,
            "recommendation": f"Prioritize Phase 1 and Phase 2 roadmap milestones for {target_skill} to achieve immediate +{score_boost}% readiness impact."
        }


# Singleton Roadmap Engine Instance
roadmap_engine = RoadmapEngine()
