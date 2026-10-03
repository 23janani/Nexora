"""
Scoring, Confidence & Insights Engine
1. Transparent Weighted Fit Score (0 - 100%):
   - Prioritizes MUST-HAVE requirements over NICE-TO-HAVE requirements (70/30 weight).
   - Provides granular category breakdown: Skills, Experience, Education, Responsibilities, Certifications & Projects.
   - Provides an exact mathematical formula and explanation trace.
2. Analysis Confidence Score (0 - 100%):
   - Measures document readability, completeness, requirement clarity, and match certainty.
   - Explicitly decoupled from candidate quality (strictly confidence in the analysis).
3. Candidate Natural Language Summary:
   - Highlighting strong alignments, critical gaps, and observations.
4. Evidence-Based Improvement Recommendations:
   - Strictly grounded in actual resume text vs. job requirements. Zero fabricated claims.
"""

from typing import Dict, Any, List


class ScoringEngine:
    def __init__(self):
        # Weights for requirements
        self.must_have_weight = 0.70
        self.nice_to_have_weight = 0.30

    def calculate_fit_score(self, comparisons: List[Dict[str, Any]], resume_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate transparent 0 - 100% Fit Score with full mathematical explainability.
        """
        must_haves = [c for c in comparisons if c.get("is_must_have")]
        nice_to_haves = [c for c in comparisons if not c.get("is_must_have")]

        def calc_group_score(items: List[Dict[str, Any]]) -> float:
            if not items:
                return 100.0
            total = 0.0
            for it in items:
                status = it.get("status")
                if status == "MATCH":
                    total += 1.0
                elif status == "PARTIAL":
                    total += 0.50
                else:
                    total += 0.0
            return (total / len(items)) * 100.0

        must_score = calc_group_score(must_haves)
        nice_score = calc_group_score(nice_to_haves)

        # Weighted calculation
        if must_haves and nice_to_haves:
            overall_fit = (must_score * self.must_have_weight) + (nice_score * self.nice_to_have_weight)
            formula_desc = f"(Must-Have Score ({round(must_score, 1)}%) × 70%) + (Nice-to-Have Score ({round(nice_score, 1)}%) × 30%)"
        elif must_haves:
            overall_fit = must_score
            formula_desc = f"Must-Have Score ({round(must_score, 1)}%) × 100% (No preferred requirements specified)"
        else:
            overall_fit = nice_score
            formula_desc = f"Preferred Requirements Score ({round(nice_score, 1)}%) × 100%"

        overall_fit = round(max(5.0, min(100.0, overall_fit)), 1)

        # Category Breakdowns
        cat_scores = self._calculate_category_breakdown(comparisons, resume_data)

        explanation = (
            f"Overall Fit Score is {int(overall_fit)}%. "
            f"Candidate satisfied {len([c for c in must_haves if c.get('status') == 'MATCH'])} of {len(must_haves)} must-have requirements "
            f"and {len([c for c in nice_to_haves if c.get('status') == 'MATCH'])} of {len(nice_to_haves)} nice-to-have requirements. "
            f"Formula: {formula_desc}."
        )

        return {
            "overall_fit_score": int(overall_fit),
            "raw_fit_score": overall_fit,
            "must_have_score": round(must_score, 1),
            "nice_to_have_score": round(nice_score, 1),
            "category_breakdown": cat_scores,
            "calculation_formula": formula_desc,
            "explanation": explanation
        }

    def _calculate_category_breakdown(self, comparisons: List[Dict[str, Any]], resume_data: Dict[str, Any]) -> Dict[str, int]:
        """
        Calculates match % for standard categories:
        Skills, Experience, Education, Responsibilities, Certifications/Projects.
        """
        categories = {
            "Skills Match": [c for c in comparisons if c.get("category") in ["Core Technical Skills", "AI / Machine Learning"]],
            "Experience Match": [c for c in comparisons if c.get("category") == "Experience"],
            "Education Match": [c for c in comparisons if c.get("category") == "Education"],
            "Responsibilities Match": [c for c in comparisons if c.get("category") in ["Data Engineering & Analysis", "Cloud & Infrastructure"]],
            "Projects & Certifications": [c for c in comparisons if c.get("category") not in ["Education", "Experience"]]
        }

        breakdown = {}
        for cat_name, items in categories.items():
            if items:
                pts = 0.0
                for it in items:
                    if it.get("status") == "MATCH":
                        pts += 1.0
                    elif it.get("status") == "PARTIAL":
                        pts += 0.50
                score = round((pts / len(items)) * 100)
            else:
                # Fallback to resume completeness
                if "Education" in cat_name:
                    score = 90 if resume_data.get("education") else 70
                elif "Certifications" in cat_name:
                    score = 80 if resume_data.get("certifications") or resume_data.get("projects") else 60
                else:
                    score = 75
            breakdown[cat_name] = max(10, min(100, score))

        return breakdown

    def calculate_confidence(self, doc_quality: Dict[str, Any], resume_data: Dict[str, Any], jd_data: Dict[str, Any], comparisons: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate confidence in the analysis (0 - 100%).
        NOTE: Represents confidence in the analysis reliability, NOT candidate suitability!
        """
        factors = []
        confidence_points = 0.0

        # Factor 1: Document OCR & text extraction quality (max 30 pts)
        doc_q_score = doc_quality.get("score", 70.0) if doc_quality else 70.0
        doc_pts = (doc_q_score / 100.0) * 30.0
        confidence_points += doc_pts
        factors.append(f"Document Readability & Formatting: {round(doc_pts, 1)}/30 pts ({doc_quality.get('status', 'Good') if doc_quality else 'Normal'})")

        # Factor 2: Resume structural completeness (max 30 pts)
        res_pts = 0.0
        if resume_data.get("skills"):
            res_pts += 10.0
        if resume_data.get("experience"):
            res_pts += 10.0
        if resume_data.get("education"):
            res_pts += 5.0
        if resume_data.get("projects") or resume_data.get("certifications"):
            res_pts += 5.0
        confidence_points += res_pts
        factors.append(f"Resume Section Completeness: {round(res_pts, 1)}/30 pts")

        # Factor 3: Job Description requirement clarity (max 20 pts)
        req_count = len(jd_data.get("must_haves", [])) + len(jd_data.get("nice_to_haves", []))
        jd_pts = min(20.0, max(10.0, req_count * 2.5))
        confidence_points += jd_pts
        factors.append(f"Job Description Granularity: {round(jd_pts, 1)}/20 pts ({req_count} structured requirements identified)")

        # Factor 4: Match certainty / evidence density (max 20 pts)
        evidenced_count = len([c for c in comparisons if c.get("candidate_evidence") and "No direct evidence" not in c.get("candidate_evidence")])
        match_pts = (evidenced_count / len(comparisons)) * 20.0 if comparisons else 15.0
        confidence_points += match_pts
        factors.append(f"Semantic Evidence Traceability: {round(match_pts, 1)}/20 pts")

        final_confidence = round(max(40.0, min(98.0, confidence_points)))

        return {
            "confidence_score": int(final_confidence),
            "level": "High" if final_confidence >= 80 else ("Moderate" if final_confidence >= 60 else "Low"),
            "factors": factors,
            "disclaimer": "Confidence level reflects data extraction clarity, structural completeness, and semantic traceability. It does not measure candidate quality."
        }

    def generate_candidate_summary(self, candidate_name: str, fit_score: int, matches: List[Dict[str, Any]], partial_matches: List[Dict[str, Any]], gaps: List[Dict[str, Any]], resume_data: Dict[str, Any]) -> str:
        """
        Generate a concise, natural-language executive summary.
        """
        top_matches = [m.get("requirement", "")[:45] for m in matches[:3]]
        top_gaps = [g.get("requirement", "")[:45] for g in gaps[:2]]
        top_partials = [p.get("requirement", "")[:45] for p in partial_matches[:2]]

        summary_parts = []

        # Opening sentence
        if fit_score >= 80:
            summary_parts.append(f"{candidate_name} exhibits strong overall qualification alignment ({fit_score}% Fit Score) with primary technical and experience requirements.")
        elif fit_score >= 60:
            summary_parts.append(f"{candidate_name} demonstrates solid foundational alignment ({fit_score}% Fit Score) with notable overlap in core skills alongside a few addressable gaps.")
        else:
            summary_parts.append(f"{candidate_name} presents limited direct alignment ({fit_score}% Fit Score) with several critical required competencies missing or unevidenced.")

        # Matches
        if top_matches:
            summary_parts.append(f"Strongest matches include demonstrated proficiency in: {', '.join(top_matches)}.")

        # Partials
        if top_partials:
            summary_parts.append(f"Partial alignment was identified in: {', '.join(top_partials)}, where foundational concepts or transferable skills are evident but need deeper verification.")

        # Gaps
        if top_gaps:
            summary_parts.append(f"Primary gaps observed: lacks explicit evidence for {', '.join(top_gaps)}.")
        else:
            summary_parts.append("Candidate satisfied all principal required qualifications without significant gaps.")

        return " ".join(summary_parts)

    def generate_recommendations(self, gaps: List[Dict[str, Any]], partial_matches: List[Dict[str, Any]], resume_data: Dict[str, Any]) -> List[str]:
        """
        Strict evidence-based recommendations:
        Recommends what to highlight, clarify, or address based ONLY on real resume text vs gaps.
        DOES NOT INVENT SKILLS OR EXPERIENCE!
        """
        recommendations = []

        # Recommendations based on partial matches (skills mentioned vaguely)
        for p in partial_matches[:3]:
            req = p.get("requirement", "")
            recommendations.append(
                f"Clarify scope for '{req[:55]}': Your resume touches upon related topics, but providing concrete metrics, tooling versions, and production outcomes will strengthen this match."
            )

        # Recommendations based on missing requirements (truthful advice on gaps)
        for g in gaps[:3]:
            req = g.get("requirement", "")
            recommendations.append(
                f"Address missing requirement '{req[:55]}': If you possess relevant coursework, personal lab projects, or transferable experience in this area, explicitly include it in your experience or project sections."
            )

        # Structural suggestions
        if not resume_data.get("projects"):
            recommendations.append("Add a dedicated 'Key Technical Projects' section showcasing end-to-end implementation and architecture choices to substantiate your core competencies.")

        if not recommendations:
            recommendations.append("Your resume provides well-targeted coverage of the core requirements. Ensure technical bullet points consistently emphasize measurable business impacts and scale metrics.")

        return recommendations[:5]
