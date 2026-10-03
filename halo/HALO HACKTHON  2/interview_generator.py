"""
Personalized Mock Interview Generator
Generates 7 to 10 tailored interview questions based specifically on:
- Job description requirements
- Candidate's specific skills and experience
- Candidate's project highlights
- Identified requirement gaps and partial matches
- Engineering architecture, scaling, reliability, and collaboration
Includes question category, why it is asked, and actionable evaluation hints for the recruiter.
"""

from typing import Dict, Any, List


class InterviewGenerator:
    def generate_questions(
        self,
        candidate_name: str,
        resume_data: Dict[str, Any],
        jd_data: Dict[str, Any],
        matches: List[Dict[str, Any]],
        partial_matches: List[Dict[str, Any]],
        gaps: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate 7 to 10 personalized interview questions covering:
        1. Core Technical Deep-Dive
        2. Applied Experience and Problem Solving
        3. Primary Project Architecture
        4. Secondary Project or Technical Implementation
        5. Target Role Alignment and Production Architecture
        6. Critical Gap Probing (Primary missing requirement)
        7. Secondary Gap or Partial Match Verification
        8. Pipeline Scalability, Memory and Data Optimization
        9. Production Reliability, Drift and Observability
        10. Cross-Functional Collaboration and Business Impact
        """
        questions = []
        skills_dict = resume_data.get("skills", {})
        prog_langs = skills_dict.get("programming_languages", [])
        ai_skills = skills_dict.get("ai_ml_skills", [])
        frameworks = skills_dict.get("frameworks", [])
        libraries = skills_dict.get("libraries", [])
        databases = skills_dict.get("databases", [])

        top_tech = prog_langs + ai_skills + frameworks + libraries
        primary_skill = top_tech[0] if top_tech else "Python"
        secondary_skill = top_tech[1] if len(top_tech) > 1 else (databases[0] if databases else "SQL")

        experiences = resume_data.get("experience", [])
        projects = resume_data.get("projects", [])
        job_title = jd_data.get("job_title", "Data Scientist")

        # -------------------------------------------------------------
        # Q1: Core Technical Deep-Dive
        # -------------------------------------------------------------
        questions.append({
            "id": 1,
            "category": "Technical Deep-Dive",
            "question": f"Given your work with {primary_skill}, can you walk us through how you design high-performance data processing pipelines and ensure computational efficiency under memory constraints?",
            "context": f"Anchored in candidate's demonstrated skill: {primary_skill}.",
            "evaluation_hint": "Look for depth in vectorization, memory management (chunking, generators, caching), algorithmic complexity, and profiling tools.",
            "source": "automated"
        })

        # -------------------------------------------------------------
        # Q2: Applied Experience and Real-World Problem Solving
        # -------------------------------------------------------------
        if experiences:
            role = experiences[0]
            role_title = role.get("title", "Practitioner")
            company = role.get("company", "previous organization")
            questions.append({
                "id": 2,
                "category": "Applied Experience",
                "question": f"In your role as {role_title} at {company}, how did you translate ambiguous business requirements into concrete technical milestones, and how did you quantify the resulting business impact?",
                "context": f"Drawn directly from candidate's background at {company}.",
                "evaluation_hint": "Evaluate stakeholder alignment, KPI definition, baseline establishment, and measurable outcome attribution.",
                "source": "automated"
            })
        else:
            questions.append({
                "id": 2,
                "category": "Applied Problem Solving",
                "question": "Can you describe a challenging technical bug or edge-case failure you encountered in your projects, and explain your step-by-step methodology for isolating the root cause and resolving it?",
                "context": "Assessing structured troubleshooting methodology, hypothesis generation, and technical perseverance.",
                "evaluation_hint": "Listen for methodical isolation (reproduction, logging, unit tests) rather than random trial-and-error.",
                "source": "automated"
            })

        # -------------------------------------------------------------
        # Q3: Primary Project Architecture Deep-Dive
        # -------------------------------------------------------------
        if projects and len(projects) > 0:
            proj1 = projects[0]
            p1_name = proj1.get("name", "Data Engineering Project")
            questions.append({
                "id": 3,
                "category": "Project Architecture",
                "question": f"In your project '{p1_name}', what were the primary architectural trade-offs you considered when choosing your data structures, libraries, and design patterns?",
                "context": f"Based on candidate's project portfolio: '{p1_name}'.",
                "evaluation_hint": "Listen for clear justification of technical choices, understanding of latency vs accuracy trade-offs, and maintainability considerations.",
                "source": "automated"
            })
        else:
            questions.append({
                "id": 3,
                "category": "System Design",
                "question": "Walk us through the complete end-to-end lifecycle of an analytics or machine learning pipeline you designed, from raw data extraction to validation and output generation.",
                "context": "Evaluating holistic architecture understanding and lifecycle mastery.",
                "evaluation_hint": "Candidate should address data ingestion, schema validation, transformation logic, testing, and deployment hygiene.",
                "source": "automated"
            })

        # -------------------------------------------------------------
        # Q4: Secondary Project or Secondary Technical Competency
        # -------------------------------------------------------------
        if projects and len(projects) > 1:
            proj2 = projects[1]
            p2_name = proj2.get("name", "Technical System")
            questions.append({
                "id": 4,
                "category": "Technical Implementation",
                "question": f"Regarding your project '{p2_name}', what was the most complex technical hurdle you encountered during implementation, and how did you architect a solution around it?",
                "context": f"Investigating hands-on depth in secondary portfolio project: '{p2_name}'.",
                "evaluation_hint": "Check whether the candidate genuinely built the system vs copied boilerplate code; ask for internal mechanics.",
                "source": "automated"
            })
        else:
            questions.append({
                "id": 4,
                "category": "Database and Storage Architecture",
                "question": f"When working with {secondary_skill}, how do you structure schemas, manage indexing, and optimize query latency when handling multi-table joins on larger datasets?",
                "context": f"Probing secondary database and manipulation proficiency: {secondary_skill}.",
                "evaluation_hint": "Look for query execution plan inspection (EXPLAIN), indexing strategies (B-Tree, Hash), normalization tradeoffs, and concurrency control.",
                "source": "automated"
            })

        # -------------------------------------------------------------
        # Q5: Target Role Core Alignment
        # -------------------------------------------------------------
        questions.append({
            "id": 5,
            "category": "Target Role Alignment",
            "question": f"This position as {job_title} requires delivering production-grade reliability. How do you ensure that your code is maintainable, modular, and readily deployable within an enterprise CI/CD workflow?",
            "context": f"Directly tied to target position responsibilities: {job_title}.",
            "evaluation_hint": "Assess automated testing practices (unit, integration, regression), code reviews, Docker containerization, and environment reproducibility.",
            "source": "automated"
        })

        # -------------------------------------------------------------
        # Q6: Critical Gap Probing #1 (Primary Missing Requirement)
        # -------------------------------------------------------------
        if gaps:
            gap1 = gaps[0]
            gap1_req = gap1.get("requirement", "")
            questions.append({
                "id": 6,
                "category": "Requirement Gap Verification",
                "question": f"The job description specifies a requirement for '{gap1_req[:75]}'. While this is not explicitly evidenced on your resume, how would you approach ramping up on this competency, and what adjacent technical foundations would you draw upon?",
                "context": f"Addresses primary requirement gap: '{gap1_req[:60]}...'.",
                "evaluation_hint": "Look for honesty about gaps combined with high learning velocity, concrete learning resources cited, and conceptual transferability.",
                "source": "automated"
            })
        else:
            questions.append({
                "id": 6,
                "category": "Advanced Specialization",
                "question": "What specialized sub-domain within your field do you consider your deepest area of expertise, and how do you mentor or elevate peers in that area?",
                "context": "Evaluating technical leadership and specialization.",
                "evaluation_hint": "Candidate should articulate clear mental models and demonstrate passion for technical knowledge sharing.",
                "source": "automated"
            })

        # -------------------------------------------------------------
        # Q7: Secondary Gap or Partial Match Probing
        # -------------------------------------------------------------
        if len(gaps) > 1:
            gap2 = gaps[1]
            gap2_req = gap2.get("requirement", "")
            questions.append({
                "id": 7,
                "category": "Secondary Gap Probing",
                "question": f"Another key criteria for this role is '{gap2_req[:75]}'. Can you describe any academic coursework, personal sandbox projects, or self-directed research where you explored this or related tools?",
                "context": f"Probing secondary requirement gap: '{gap2_req[:60]}...'.",
                "evaluation_hint": "Determine whether candidate possesses latent familiarity or requires comprehensive foundational onboarding.",
                "source": "automated"
            })
        elif partial_matches:
            part_item = partial_matches[0]
            part_req = part_item.get("requirement", "")
            questions.append({
                "id": 7,
                "category": "Partial Match Clarification",
                "question": f"Regarding '{part_req[:75]}', could you clarify the exact scope of your hands-on exposure to ensure alignment with our production standards?",
                "context": f"Clarifying depth of partially matched requirement: '{part_req[:60]}...'.",
                "evaluation_hint": "Confirm whether candidate's practical exposure meets the required depth for independent, unsupervised execution.",
                "source": "automated"
            })
        else:
            questions.append({
                "id": 7,
                "category": "Technology Evaluation",
                "question": "When deciding whether to adopt a new library or architectural pattern versus sticking with established standard tools, what framework do you use to evaluate risk and benefit?",
                "context": "Assessing pragmatic engineering judgement and vendor/library risk management.",
                "evaluation_hint": "Look for total cost of ownership awareness, community vitality checks, security auditing, and backward compatibility.",
                "source": "automated"
            })

        # -------------------------------------------------------------
        # Q8: Pipeline Scalability, Memory and Performance Optimization
        # -------------------------------------------------------------
        questions.append({
            "id": 8,
            "category": "Performance and Scalability",
            "question": "If your data processing workflow or service experiences a sudden 10x surge in data volume or concurrent request traffic, where would the primary bottlenecks occur, and how would you redesign the architecture for horizontal scalability?",
            "context": "Testing architectural foresight, scaling bottlenecks, and concurrent data handling.",
            "evaluation_hint": "Look for discussions of asynchronous processing, message queues, distributed compute (e.g. Spark, Dask, Ray), caching layers, and database connection pooling.",
            "source": "automated"
        })

        # -------------------------------------------------------------
        # Q9: Production Observability, Data Quality and Drift Monitoring
        # -------------------------------------------------------------
        questions.append({
            "id": 9,
            "category": "Production Observability",
            "question": "In a live environment, how do you continuously validate input data quality, detect distribution shift or concept drift, and establish alerting thresholds before downstream systems are impacted?",
            "context": "Probing operational rigor, automated data validation, and telemetry practices.",
            "evaluation_hint": "Assess understanding of statistical tests (e.g., KS test, Chi-square, PSI), schema assertion tools (Great Expectations, Pydantic), and observability tooling.",
            "source": "automated"
        })

        # -------------------------------------------------------------
        # Q10: Cross-Functional Collaboration and Trade-offs
        # -------------------------------------------------------------
        questions.append({
            "id": 10,
            "category": "Cross-Functional Execution",
            "question": "Describe a scenario where technical constraints conflicted with a product deadline or stakeholder expectation. How did you negotiate compromises while maintaining engineering integrity?",
            "context": "Evaluating stakeholder management, communication clarity, and pragmatic negotiation.",
            "evaluation_hint": "Look for constructive communication, risk transparency, staged delivery approaches, and collaborative prioritization.",
            "source": "automated"
        })

        return questions[:10]
