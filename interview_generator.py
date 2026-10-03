"""
Built-In AI Interview Question Generator & Customization Engine
Supports dynamic question synthesis based on candidate skill gaps, target requirements,
and customizable parameters (Seniority/Difficulty, Focus Tracks, Custom Directives).
Operates via a Triple-Engine architecture:
  1. OpenRouter AI Engine: Primary — uses OpenAI-compatible API (sk-or-v1-...) for best results.
  2. Gemini AI Engine: Fallback — powered by google.generativeai when a Gemini key is configured.
  3. Local Built-in AI Engine: Final fallback — deep semantic graph, zero external dependencies.
Strict compliance: zero emojis, zero em dashes, rectangular radii, corporate palette.
"""

import os
import re
import json
import logging
import requests
from typing import Dict, Any, List, Optional, Tuple

# Load environment variables from .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger("InterviewGenerator")

# OpenRouter — primary AI engine (OpenAI-compatible endpoint)
OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL    = "meta-llama/llama-3.3-70b-instruct"   # best free/cheap model on OpenRouter

# Check for Gemini availability (fallback)
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class InterviewGenerator:
    def __init__(self, default_api_key: Optional[str] = None):
        # OpenRouter key (primary)
        self.openrouter_key = (
            os.environ.get("OPENROUTER_API_KEY") or default_api_key
            if (default_api_key or "").startswith("sk-or-") else None
        ) or os.environ.get("OPENROUTER_API_KEY")

        # Gemini key (fallback)
        self.api_key = (
            (default_api_key if default_api_key and not (default_api_key or "").startswith("sk-or-") else None)
            or os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
        )

        if self.openrouter_key:
            logger.info("OpenRouter AI engine active (primary).")
        elif self.api_key and GEMINI_AVAILABLE:
            try:
                genai.configure(api_key=self.api_key)
                logger.info("Gemini AI API Key initialized (fallback engine).")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini with API key: {e}")
        else:
            logger.info("Using built-in local AI engine (no external API keys found).")

    def generate_questions(
        self,
        candidate_name: str,
        resume_data: Dict[str, Any],
        jd_data: Dict[str, Any],
        matches: List[Dict[str, Any]],
        partial_matches: List[Dict[str, Any]],
        gaps: List[Dict[str, Any]],
        difficulty: str = "Senior",
        focus_areas: Optional[List[str]] = None,
        custom_directives: str = "",
        count: int = 10,
        api_key: Optional[str] = None,
        local_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Synthesizes 7 to 10+ tailored interview questions based on missing skills and requirement gaps.
        Priority: OpenRouter -> Gemini -> Local Built-in AI.
        Set local_only=True to skip cloud AI (e.g., during startup seeding).
        """
        target_count = max(5, min(15, count))

        # Resolve runtime key overrides
        runtime_or_key  = (api_key if api_key and api_key.startswith("sk-or-") else None) or self.openrouter_key
        runtime_gem_key = (api_key if api_key and not api_key.startswith("sk-or-") else None) or self.api_key

        # ── Engine 1: OpenRouter (primary) ─────────────────────
        if runtime_or_key and not local_only:
            try:
                or_questions = self._generate_with_openrouter(
                    candidate_name, resume_data, jd_data, gaps, partial_matches,
                    difficulty, focus_areas, custom_directives, target_count, runtime_or_key
                )
                if or_questions and len(or_questions) >= 5:
                    logger.info(f"OpenRouter generated {len(or_questions)} questions successfully.")
                    return or_questions[:target_count]
            except Exception as e:
                logger.warning(f"OpenRouter generation failed, trying fallback: {e}")

        # ── Engine 2: Gemini (fallback) ─────────────────────────
        if runtime_gem_key and GEMINI_AVAILABLE and not local_only:
            try:
                gemini_questions = self._generate_with_gemini(
                    candidate_name, resume_data, jd_data, gaps, partial_matches,
                    difficulty, focus_areas, custom_directives, target_count, runtime_gem_key
                )
                if gemini_questions and len(gemini_questions) >= 5:
                    return gemini_questions[:target_count]
            except Exception as e:
                logger.warning(f"Gemini generation fallback to Built-in Local AI Engine: {e}")

        # ── Engine 3: Local Built-in AI (final fallback) ────────
        return self._generate_with_builtin_ai(
            candidate_name, resume_data, jd_data, matches, partial_matches, gaps,
            difficulty, focus_areas, custom_directives, target_count
        )

    def regenerate_single_question(
        self,
        question_id: str,
        gap_text: str,
        candidate_name: str,
        difficulty: str = "Senior",
        category: str = "Technical Architecture",
        custom_prompt: str = "",
        known_skills: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Regenerate a single interview question with built-in AI."""
        terms = self._extract_key_terms(gap_text)
        terms_str = ", ".join(terms[:3]) if terms else gap_text[:40]
        skill_ref = ", ".join(known_skills[:3]) if known_skills else "established core competencies"

        # Difficulty prefixes and calibration
        diff_calibrations = {
            "Junior": {
                "prefix": "From a foundational perspective",
                "depth": "basic syntax, core workflows, and step-by-step setup",
                "eval": "Verify baseline conceptual comprehension and structured learning methodology."
            },
            "Mid": {
                "prefix": "In a standard production feature cycle",
                "depth": "hands-on implementation, error handling, and unit test coverage",
                "eval": "Assess ability to independently write, test, and ship code without supervision."
            },
            "Senior": {
                "prefix": "Considering high-scale enterprise production",
                "depth": "architectural trade-offs, latency optimization, and automated failover",
                "eval": "Assess deep systems design, performance profiling, and operational resilience."
            },
            "Lead / Staff": {
                "prefix": "From an organization-wide architectural standpoint",
                "depth": "distributed scalability, multi-team boundaries, technical debt, and cross-cutting standards",
                "eval": "Look for strategic technical vision, consensus building, and distributed failure mitigation."
            },
            "Architect": {
                "prefix": "Evaluating end-to-end system topology and CAP trade-offs",
                "depth": "consistency models, disaster recovery, cloud cost economics, and technology lifecycle",
                "eval": "Evaluate enterprise architectural governance, long-term evolvability, and risk mitigation."
            }
        }

        cal = diff_calibrations.get(difficulty, diff_calibrations["Senior"])

        # Build fresh question
        if custom_prompt.strip():
            q_text = f"{cal['prefix']}, addressing the missing requirement '{gap_text[:75]}': {custom_prompt.strip()} How would you architect this solution using '{terms_str}'?"
        elif "Architecture" in category:
            q_text = f"{cal['prefix']}, walk us through how you would architect a resilient production subsystem that requires '{terms_str}' (which is missing from your profile). How do you ensure high availability and monitor its runtime telemetry?"
        elif "Debugging" in category or "Scenario" in category:
            q_text = f"Suppose a service utilizing '{terms_str}' experiences a severe memory leak or silent data corruption under heavy concurrent load. Given your experience in {skill_ref}, what step-by-step diagnostic workflow would you employ to identify the root cause?"
        elif "Trade-offs" in category:
            q_text = f"When evaluating solutions that require '{terms_str}', what are the critical trade-offs between execution speed, operational maintenance overhead, and developer velocity that inform your technical choice?"
        else:
            q_text = f"The job specification demands expertise in '{gap_text[:80]}'. How will you translate your background in {skill_ref} to master '{terms_str}' and meet production standards within your first 30 days?"

        return {
            "id": question_id,
            "question": q_text,
            "category": f"{category} ({difficulty})",
            "difficulty": difficulty,
            "evaluation_hint": f"{cal['eval']} Probe specific familiarity with {terms_str} operational realities.",
            "candidate_coaching": f"Frame your answer using the STAR format. Highlight conceptual parallels from {skill_ref} to bridge the gap in {terms_str}.",
            "missing_skill_focus": terms_str,
            "is_custom": 1,
            "source": "builtin_ai_regenerator"
        }

    # =========================================================================
    # LOCAL BUILT-IN AI ENGINE (ZERO EXTERNAL DEPENDENCY)
    # =========================================================================

    def _generate_with_builtin_ai(
        self,
        candidate_name: str,
        resume_data: Dict[str, Any],
        jd_data: Dict[str, Any],
        matches: List[Dict[str, Any]],
        partial_matches: List[Dict[str, Any]],
        gaps: List[Dict[str, Any]],
        difficulty: str,
        focus_areas: Optional[List[str]],
        custom_directives: str,
        count: int
    ) -> List[Dict[str, Any]]:
        questions = []
        q_id = 1

        probing_items = []
        for g in gaps:
            probing_items.append({"item": g, "type": "GAP"})
        for p in partial_matches:
            probing_items.append({"item": p, "type": "PARTIAL"})

        candidate_skills = resume_data.get("skills", {})
        top_known_skills = (
            candidate_skills.get("programming_languages", []) +
            candidate_skills.get("frameworks", []) +
            candidate_skills.get("libraries", []) +
            candidate_skills.get("databases", [])
        )
        known_skill_str = ", ".join(top_known_skills[:3]) if top_known_skills else "your core foundational skills"

        # Calibration map
        diff_prefix = {
            "Junior": "As a developing practitioner",
            "Mid": "From an implementation perspective",
            "Senior": "In an enterprise production setting",
            "Lead / Staff": "From a principal systems architecture perspective",
            "Architect": "At an enterprise architecture and scalability level"
        }.get(difficulty, "In an enterprise production setting")

        eval_bias = {
            "Junior": "Assess foundational grasp and eagerness to adopt best practices.",
            "Mid": "Assess hands-on coding quality, test assertions, and independent execution.",
            "Senior": "Assess deep architectural trade-offs, scalability bottlenecks, and defensive design.",
            "Lead / Staff": "Assess cross-cutting architectural standards, technical leadership, and resilience.",
            "Architect": "Assess systemic boundaries, fault domains, and technology lifecycle strategy."
        }.get(difficulty, "Assess technical depth and production readiness.")

        # If custom directives provided, create a primary directive question first
        if custom_directives.strip() and probing_items:
            first_gap = probing_items[0]["item"].get("requirement", "the target qualification")
            terms = self._extract_key_terms(first_gap)
            terms_str = ", ".join(terms[:3]) if terms else first_gap[:40]
            questions.append({
                "id": f"q_{q_id}",
                "category": f"Custom Directive: Technical Architecture ({difficulty})",
                "difficulty": difficulty,
                "missing_skill": first_gap,
                "target_concept": terms_str,
                "missing_skill_focus": terms_str,
                "importance": "CRITICAL",
                "question": f"{diff_prefix}, reflecting our custom criteria '{custom_directives.strip()}': How would you architect and deploy '{terms_str}' into our pipeline to address this directive?",
                "context": f"Generated from custom directive: '{custom_directives[:70]}'",
                "evaluation_hint": f"{eval_bias} Verify that the candidate directly tackles '{custom_directives[:50]}'.",
                "candidate_coaching": f"Directly address the interviewer's specific objective, citing tangible design decisions and architectural trade-offs.",
                "source": "builtin_ai_custom"
            })
            q_id += 1

        # Probing strategy generation across gaps
        if probing_items:
            for probe in probing_items:
                if len(questions) >= count:
                    break

                item = probe["item"]
                item_type = probe["type"]
                req_text = item.get("requirement", "")
                cat = item.get("category", "Technical Competency")
                importance = item.get("importance", "MUST-HAVE")
                terms = self._extract_key_terms(req_text)
                terms_str = ", ".join(terms[:3]) if terms else req_text[:40]

                # Strategy 1: Core Architecture on Missing Skill
                q_text = self._build_architecture_question(req_text, terms_str, item_type, diff_prefix)
                questions.append({
                    "id": f"q_{q_id}",
                    "category": f"Technical Architecture ({difficulty}): {cat}",
                    "difficulty": difficulty,
                    "missing_skill": req_text,
                    "target_concept": terms_str,
                    "missing_skill_focus": terms_str,
                    "importance": importance,
                    "question": q_text,
                    "context": f"Anchored directly in missing requirement ({importance}): '{req_text[:70]}...'",
                    "evaluation_hint": f"{eval_bias} Assess whether candidate grasps the core principles of {terms_str} without needing prior resume exposure.",
                    "candidate_coaching": f"Acknowledge the gap transparently, then demonstrate conceptual fluency in {terms_str} by connecting it to your experience in {known_skill_str}.",
                    "source": "builtin_ai_gap"
                })
                q_id += 1

                # Strategy 2: Scenario-Based Problem Solving & Debugging
                if len(questions) < count:
                    scenario_q = self._build_scenario_question(req_text, terms_str, diff_prefix)
                    questions.append({
                        "id": f"q_{q_id}",
                        "category": f"Live Debugging & Edge Cases ({difficulty}): {cat}",
                        "difficulty": difficulty,
                        "missing_skill": req_text,
                        "target_concept": terms_str,
                        "missing_skill_focus": terms_str,
                        "importance": importance,
                        "question": scenario_q,
                        "context": f"Probing real-world problem solving around missing qualification: '{req_text[:70]}...'",
                        "evaluation_hint": f"{eval_bias} Look for methodical isolation of root cause and defensive automated assertions.",
                        "candidate_coaching": "Structure your response using the STAR framework. Emphasize hypotheses generation and verification logs.",
                        "source": "builtin_ai_gap"
                    })
                    q_id += 1

                # Strategy 3: Transferable Skills & Ramp-Up Velocity
                if len(questions) < count:
                    transfer_q = self._build_transferable_question(req_text, terms_str, known_skill_str, diff_prefix)
                    questions.append({
                        "id": f"q_{q_id}",
                        "category": f"Missing Skill Remediation & Ramp-Up ({difficulty}): {cat}",
                        "difficulty": difficulty,
                        "missing_skill": req_text,
                        "target_concept": terms_str,
                        "missing_skill_focus": terms_str,
                        "importance": importance,
                        "question": transfer_q,
                        "context": f"Evaluating candidate learning agility for technical requirement: '{req_text[:70]}...'",
                        "evaluation_hint": "Assess intellectual curiosity, specific technical learning roadmaps cited, and realistic time-to-productivity.",
                        "candidate_coaching": "Cite concrete technical documentation, sandbox projects, or parallel past technologies you mastered quickly.",
                        "source": "builtin_ai_gap"
                    })
                    q_id += 1

        # Additional depth generation if still below target count
        if probing_items and len(questions) < count:
            for probe in probing_items:
                if len(questions) >= count:
                    break
                item = probe["item"]
                req_text = item.get("requirement", "")
                cat = item.get("category", "Technical Competency")
                terms = self._extract_key_terms(req_text)
                terms_str = ", ".join(terms[:3]) if terms else req_text[:40]

                tradeoff_q = f"{diff_prefix}, when designing services that depend on '{terms_str}', what are the critical trade-offs between computational latency, cloud operational cost, and maintenance overhead that inform your technical choice?"
                questions.append({
                    "id": f"q_{q_id}",
                    "category": f"Architectural Trade-Offs ({difficulty}): {cat}",
                    "difficulty": difficulty,
                    "missing_skill": req_text,
                    "target_concept": terms_str,
                    "missing_skill_focus": terms_str,
                    "importance": "DESIRABLE",
                    "question": tradeoff_q,
                    "context": f"Probing critical evaluation and technical judgement for missing requirement: '{req_text[:70]}...'",
                    "evaluation_hint": f"{eval_bias} Evaluate whether candidate can objectively critique {terms_str} versus alternative architectures.",
                    "candidate_coaching": f"Discuss why a team might choose or avoid {terms_str}, demonstrating mature architectural perspective.",
                    "source": "builtin_ai_gap"
                })
                q_id += 1

        # Fallback if literally zero gaps exist (100% match)
        if not questions and matches:
            for idx, match_item in enumerate(matches[:count], 1):
                m_req = match_item.get("requirement", "")
                m_terms = self._extract_key_terms(m_req)
                m_str = ", ".join(m_terms[:2]) if m_terms else m_req[:40]
                questions.append({
                    "id": f"q_{q_id}",
                    "category": f"Advanced Scaling ({difficulty}): {match_item.get('category', 'Technical')}",
                    "difficulty": difficulty,
                    "missing_skill": "Advanced scaling & multi-region deployment",
                    "target_concept": m_str,
                    "missing_skill_focus": m_str,
                    "importance": "MUST-HAVE",
                    "question": f"{diff_prefix}, while your resume confirms capability in '{m_str}', how do you manage high-load distributed scaling, memory profiling, and automated edge-case failover in enterprise production?",
                    "context": f"Probing advanced operational depth for matched qualification: '{m_req[:70]}...'",
                    "evaluation_hint": f"{eval_bias} Verify whether candidate's knowledge is senior and production-tested rather than superficial.",
                    "candidate_coaching": "Provide specific production metrics, throughput numbers, and concrete architectural decisions you made under constraints.",
                    "source": "builtin_ai_gap"
                })
                q_id += 1

        return questions[:count]

    # =========================================================================
    # GOOGLE GEMINI AI ENGINE (WHEN KEY IS PROVIDED)
    # =========================================================================

    def _generate_with_openrouter(
        self,
        candidate_name: str,
        resume_data: Dict[str, Any],
        jd_data: Dict[str, Any],
        gaps: List[Dict[str, Any]],
        partial_matches: List[Dict[str, Any]],
        difficulty: str,
        focus_areas: Optional[List[str]],
        custom_directives: str,
        count: int,
        api_key: str
    ) -> List[Dict[str, Any]]:
        """Generate interview questions via OpenRouter (OpenAI-compatible API)."""
        gap_descriptions = "\n".join(
            [f"- Gap {i+1}: {g.get('requirement', '')} (Category: {g.get('category', 'General')})" for i, g in enumerate(gaps)]
        ) or "None noted."
        partial_descriptions = "\n".join(
            [f"- Partial {i+1}: {p.get('requirement', '')} (Evidence: {p.get('candidate_evidence', '')})" for i, p in enumerate(partial_matches)]
        ) or "None noted."
        focus_str = ", ".join(focus_areas) if focus_areas else "Technical depth, system design, gap probing"

        prompt = f"""You are an executive enterprise hiring assessor conducting a rigorous interview.
Candidate Name: {candidate_name}
Target Job Title: {jd_data.get('job_title', 'Enterprise Technical Lead')}
Seniority Level: {difficulty}
Focus Areas: {focus_str}
Custom Directives: {custom_directives or 'Strictly probe missing technical skills and requirement gaps.'}
Number of Questions Required: {count}

Candidate Requirement Gaps (skills they are missing or weak in):
{gap_descriptions}

Candidate Partial Matches (skills they partially demonstrated):
{partial_descriptions}

Task:
Generate exactly {count} personalized, rigorous interview questions that probe the candidate's gaps and partial skills.
Do NOT use generic questions. Do NOT use emojis. Do NOT use em dashes.
Return ONLY a valid JSON array with NO extra text, markdown, or explanation:
[
  {{
    "id": "q_1",
    "category": "Technical Architecture ({difficulty})",
    "difficulty": "{difficulty}",
    "missing_skill_focus": "Name of the missing skill or gap",
    "question": "The interview question text...",
    "evaluation_hint": "What the interviewer should listen for in a strong response...",
    "candidate_coaching": "How the candidate should structure their answer..."
  }}
]"""

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://resume-matcher.enterprise.internal",
            "X-Title": "Resume Matcher Enterprise",
        }
        payload = {
            "model": OPENROUTER_MODEL,
            "messages": [
                {"role": "system", "content": "You are a precise JSON-only response AI. Return only valid JSON arrays, no markdown fences."},
                {"role": "user",   "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 4096,
        }

        resp = requests.post(
            f"{OPENROUTER_API_BASE}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        resp.raise_for_status()
        result = resp.json()
        text = result["choices"][0]["message"]["content"].strip()
        data = self._parse_ai_json(text)
        if isinstance(data, list) and len(data) >= 5:
            for idx, q in enumerate(data, 1):
                q["id"] = f"q_{idx}"
                q["source"] = "openrouter_ai"
                q["difficulty"] = difficulty
            return data
        raise ValueError(f"OpenRouter returned insufficient questions: {len(data) if isinstance(data, list) else type(data)}")

    def _generate_with_gemini(
        self,
        candidate_name: str,
        resume_data: Dict[str, Any],
        jd_data: Dict[str, Any],
        gaps: List[Dict[str, Any]],
        partial_matches: List[Dict[str, Any]],
        difficulty: str,
        focus_areas: Optional[List[str]],
        custom_directives: str,
        count: int,
        api_key: str
    ) -> List[Dict[str, Any]]:
        genai.configure(api_key=api_key)
        model = None
        for candidate_model in ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro", "gemini-pro"]:
            try:
                model = genai.GenerativeModel(candidate_model)
                break
            except Exception:
                continue
        if not model:
            model = genai.GenerativeModel("gemini-1.5-flash")

        gap_descriptions = "\n".join([f"- Gap {i+1}: {g.get('requirement', '')} (Category: {g.get('category', 'General')})" for i, g in enumerate(gaps)])
        partial_descriptions = "\n".join([f"- Partial {i+1}: {p.get('requirement', '')} (Evidence: {p.get('candidate_evidence', '')})" for i, p in enumerate(partial_matches)])
        prompt = f"""
You are an executive enterprise hiring assessor.
Candidate Name: {candidate_name}
Target Job Title: {jd_data.get('job_title', 'Enterprise Technical Lead')}
Target Seniority Level: {difficulty}
Custom Directives: {custom_directives or 'Strictly probe missing technical skills and requirement gaps.'}
Desired Number of Questions: {count}

Candidate Requirement Gaps:
{gap_descriptions or 'None noted.'}

Candidate Partial Matches:
{partial_descriptions or 'None noted.'}

Task:
Generate exactly {count} personalized, rigorous interview questions formulated specifically to probe the candidate's missing skills, requirement gaps, and trade-offs.
Do NOT use generic or cliché questions. Do NOT use emojis. Do NOT use em dashes.
Return ONLY valid JSON array with the following schema:
[
  {{
    "id": "q_1",
    "category": "Technical Architecture ({difficulty})",
    "difficulty": "{difficulty}",
    "missing_skill_focus": "Name of missing tool or skill",
    "question": "Question text here...",
    "evaluation_hint": "What the interviewer should listen for in a top response...",
    "candidate_coaching": "Coaching advice for candidate on how to structure their answer..."
  }}
]
"""
        response = model.generate_content(prompt)
        text = response.text.strip()
        data = self._parse_ai_json(text)
        if isinstance(data, list) and len(data) >= 5:
            for idx, q in enumerate(data, 1):
                q["id"] = f"q_{idx}"
                q["source"] = "gemini_ai"
                q["difficulty"] = difficulty
            return data
        raise ValueError("Invalid JSON format received from Gemini.")

    # =========================================================================
    # JSON PARSING HELPER  (robust multi-strategy parser)
    # =========================================================================

    def _parse_ai_json(self, text: str) -> Any:
        """Parse LLM output into Python objects, handling common AI formatting issues.

        Strategies applied in order:
        1. Strip markdown fences (```json ... ```).
        2. Extract the first JSON array found via regex.
        3. Repair common issues: trailing commas, JS comments, single-quoted strings.
        4. Fall back to a line-by-line object extraction if all else fails.
        """
        # ─ Step 1: strip markdown fences ───────────────────────
        t = text.strip()
        for fence in ("```json", "```JSON", "```"):
            if t.startswith(fence):
                t = t[len(fence):]
                break
        if t.endswith("```"):
            t = t[:-3]
        t = t.strip()

        # ─ Step 2: try straight parse first ─────────────────────
        try:
            return json.loads(t)
        except json.JSONDecodeError:
            pass

        # ─ Step 3: extract first [...] block ──────────────────
        array_match = re.search(r'(\[.*\])', t, re.DOTALL)
        if array_match:
            candidate = array_match.group(1)
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                t = candidate  # use the extracted block for further repair

        # ─ Step 4: repair common issues ──────────────────────
        repaired = t
        # Remove single-line JS comments (// ...)
        repaired = re.sub(r'//[^\n]*', '', repaired)
        # Remove block comments (/* ... */)
        repaired = re.sub(r'/\*.*?\*/', '', repaired, flags=re.DOTALL)
        # Remove trailing commas before ] or }
        repaired = re.sub(r',\s*([\]\}])', r'\1', repaired)
        # Replace smart/curly quotes with straight quotes
        for old, new in [('\u201c', '"'), ('\u201d', '"'), ('\u2018', "'"), ('\u2019', "'")]:
            repaired = repaired.replace(old, new)
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            pass

        # ─ Step 5: partial recovery — collect complete {...} objects ───
        objects = []
        depth, start = 0, -1
        for i, ch in enumerate(repaired):
            if ch == '{':
                if depth == 0:
                    start = i
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0 and start != -1:
                    try:
                        obj_text = repaired[start:i+1]
                        # Quick trailing-comma fix for this object too
                        obj_text = re.sub(r',\s*([\]\}])', r'\1', obj_text)
                        objects.append(json.loads(obj_text))
                    except json.JSONDecodeError:
                        pass
                    start = -1
        if objects:
            logger.warning(f"_parse_ai_json: partial recovery extracted {len(objects)} objects from malformed JSON.")
            return objects

        raise json.JSONDecodeError("_parse_ai_json: all parse strategies failed.", t, 0)

    # =========================================================================
    # HELPER EXTRACTION & STRING BUILDERS
    # =========================================================================

    def _extract_key_terms(self, text: str) -> List[str]:
        patterns = [
            r"\b(AWS|GCP|Azure|SageMaker|EC2|S3|Lambda|CloudWatch|Glue|Athena)\b",
            r"\b(Docker|Kubernetes|K8s|Helm|Terraform|Ansible|CI/CD|GitLab|Jenkins|GitHub Actions)\b",
            r"\b(PyTorch|TensorFlow|Keras|LangChain|LlamaIndex|Hugging Face|Transformers|LLM|RAG|vLLM|Deep Learning)\b",
            r"\b(Spark|Hadoop|Kafka|Flink|Airflow|dbt|Snowflake|BigQuery|PostgreSQL|MySQL|Redis|MongoDB|Cassandra)\b",
            r"\b(Pandas|NumPy|Scikit-learn|SciPy|XGBoost|LightGBM|CatBoost|Statsmodels)\b",
            r"\b(\d+\+?\s*years?(\s+of)?\s+(professional|industry)?\s*experience)\b",
            r"\b(Master\x27s|Ph\.?D\.?|Bachelor\x27s|degree)\b",
            r"\b(statistics|probability|experimentation|A/B testing|causal inference|predictive modeling)\b",
            r"\b(MLOps|model monitoring|drift detection|feature store|model registry|Triton|TorchServe)\b"
        ]
        found = []
        for pat in patterns:
            matches = re.findall(pat, text, re.IGNORECASE)
            for item in matches:
                val = item[0] if isinstance(item, tuple) else item
                if val and val.lower() not in [f.lower() for f in found]:
                    found.append(val)

        if not found:
            stopwords = {"experience", "required", "preferred", "including", "working", "knowledge", "ability", "strong", "seeking", "experienced", "proficient", "proficiency", "responsibilities"}
            words = [w for w in re.split(r"[^A-Za-z0-9\-+]", text) if len(w) >= 4 and w.lower() not in stopwords]
            found = words[:3]

        return found

    def _build_architecture_question(self, req_text: str, terms_str: str, item_type: str, diff_prefix: str) -> str:
        if "year" in terms_str.lower() or "experience" in terms_str.lower():
            return f"{diff_prefix}, the role requires '{req_text[:85]}'. Since your resume does not explicitly document this tenure, how have your hands-on projects or academic milestones prepared you to deliver production-grade results independently from day one?"
        if any(w in terms_str.lower() for w in ["degree", "master", "phd", "bachelor"]):
            return f"{diff_prefix}, the criteria highlights '{req_text[:85]}'. While this exact credential is not evidenced, how have your practical software implementations and self-directed coursework equipped you with equivalent quantitative and algorithmic depth?"
        if any(w in terms_str.lower() for w in ["aws", "gcp", "azure", "cloud", "docker", "kubernetes"]):
            return f"{diff_prefix}, the job demands hands-on capability in '{terms_str}', which is missing from your profile. If required to deploy and maintain our services using '{terms_str}', how would you design the deployment architecture and secure its resources?"
        if any(w in terms_str.lower() for w in ["pytorch", "tensorflow", "llm", "langchain", "deep learning"]):
            return f"{diff_prefix}, a core requirement is '{req_text[:85]}', which is not evidenced in your background. Walk us through how you would architect a model training or inference pipeline using '{terms_str}', and how you would evaluate its performance."
        return f"{diff_prefix}, the target position requires '{req_text[:85]}'. Although this is a missing qualification in your profile, can you explain the architectural principles of '{terms_str}', and how you would apply them to our production environment?"

    def _build_scenario_question(self, req_text: str, terms_str: str, diff_prefix: str) -> str:
        return f"{diff_prefix}, suppose you are assigned a critical sprint task requiring '{terms_str}' and you encounter an unexpected system bottleneck or latency spike. What diagnostic tools and methodical troubleshooting steps would you take to isolate and resolve the issue?"

    def _build_transferable_question(self, req_text: str, terms_str: str, known_skill_str: str, diff_prefix: str) -> str:
        return f"{diff_prefix}, regarding the missing requirement '{req_text[:85]}', what adjacent technologies or frameworks in your background (such as {known_skill_str}) share foundational concepts with '{terms_str}', and what is your concrete timeline to ramp up to production proficiency?"
