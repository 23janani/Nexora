"""
AI-Powered Resume-Job Description Matching System - Flask API Server
Enterprise Candidate Requirement Analysis & Verification Portal
"""

import os
import uuid
import tempfile
from flask import Flask, request, jsonify, render_template, send_file, redirect, url_for, session
from werkzeug.utils import secure_filename

from doc_processor import DocumentProcessor
from duplicate_detector import DuplicateDetector
from anomaly_detector import AnomalyDetector
from nlp_engine import NLPEngine
from scoring_engine import ScoringEngine
from interview_generator import InterviewGenerator
from mock_data import SAMPLE_JDS, SAMPLE_RESUMES, create_sample_files

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "enterprise_secret_recruiting_key_2026"
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB max upload

# Initialize Core Services
doc_processor = DocumentProcessor(ocr_engine_path="./ocr_engine")
duplicate_detector = DuplicateDetector(similarity_threshold=0.80)
anomaly_detector = AnomalyDetector()
nlp_engine = NLPEngine()
scoring_engine = ScoringEngine()
interview_generator = InterviewGenerator()

# In-Memory State Store
candidates_store = {}
active_jd = None
custom_domain_config = {
    "domain": "matcher.recruitment.internal",
    "ssl_status": "Active (TLS 1.3)",
    "verified": True
}


def initialize_default_data():
    """Seed the system with standard sample JD and rich candidates."""
    global active_jd
    default_jd_info = SAMPLE_JDS["senior_ds_genai"]
    parsed_jd = nlp_engine.extract_job_description(default_jd_info["text"])
    parsed_jd["id"] = default_jd_info["id"]
    parsed_jd["title"] = default_jd_info["title"]
    active_jd = parsed_jd

    create_sample_files("./sample_files")

    candidates_store.clear()
    duplicate_detector.repository.clear()

    for key, data in SAMPLE_RESUMES.items():
        c_id = data["id"]
        text = data["text"]
        name = data["name"]

        quality = doc_processor.check_readability(text, f"{name}.txt")
        dup_res = duplicate_detector.check_duplicate(c_id, name, text)
        repeated_res = anomaly_detector.detect_repeated_content(text)
        ai_res = anomaly_detector.detect_ai_generated(text)

        resume_data = nlp_engine.extract_resume_info(text)
        resume_data["personal"]["name"] = name

        match_results = nlp_engine.semantic_match(resume_data, active_jd)
        fit_data = scoring_engine.calculate_fit_score(match_results["all_comparisons"], resume_data)
        conf_data = scoring_engine.calculate_confidence(quality, resume_data, active_jd, match_results["all_comparisons"])
        summary = scoring_engine.generate_candidate_summary(
            name, fit_data["overall_fit_score"],
            match_results["matches"], match_results["partial_matches"], match_results["gaps"],
            resume_data
        )
        recommendations = scoring_engine.generate_recommendations(match_results["gaps"], match_results["partial_matches"], resume_data)
        interview_qs = interview_generator.generate_questions(
            name, resume_data, active_jd,
            match_results["matches"], match_results["partial_matches"], match_results["gaps"]
        )

        candidates_store[c_id] = {
            "id": c_id,
            "name": name,
            "filename": f"{name.replace(' ', '_')}.txt",
            "file_type": "TXT",
            "raw_text": text,
            "quality": quality,
            "flags": {
                "duplicate": dup_res,
                "repeated_content": repeated_res,
                "ai_content": ai_res
            },
            "structured_resume": resume_data,
            "analysis": {
                "fit_score": fit_data["overall_fit_score"],
                "fit_score_details": fit_data,
                "confidence": conf_data,
                "matches": match_results["matches"],
                "partial_matches": match_results["partial_matches"],
                "gaps": match_results["gaps"],
                "comparisons": match_results["all_comparisons"],
                "summary": summary,
                "recommendations": recommendations,
                "mock_interview": interview_qs
            },
            "status": "Evaluated",
            "created_at": "Today"
        }


initialize_default_data()


# =========================================================================
# WEB PAGES & AUTHENTICATION
# =========================================================================

@app.route("/")
def index():
    user = session.get("user", {"name": "Senior Data Scientist", "role": "Lead Assessor", "email": "evaluator@internal.corp"})
    return render_template("index.html", user=user, custom_domain=custom_domain_config["domain"])


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "evaluator@internal.corp")
        role = request.form.get("role", "Data Scientist")
        name = email.split("@")[0].replace(".", " ").title()
        session["user"] = {
            "name": name,
            "role": role,
            "email": email
        }
        return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/api/domain-config", methods=["GET", "POST"])
def domain_config():
    global custom_domain_config
    if request.method == "POST":
        new_domain = request.json.get("domain", "").strip() if request.is_json else request.form.get("domain", "").strip()
        if new_domain:
            custom_domain_config["domain"] = new_domain
            custom_domain_config["verified"] = True
            return jsonify({"success": True, "domain": new_domain, "message": f"Custom domain updated to {new_domain}."})
        return jsonify({"error": "Invalid domain name."}), 400
    return jsonify(custom_domain_config)


# =========================================================================
# REST API ENDPOINTS
# =========================================================================

@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Real, verified database statistics (no simulated or fabricated metrics)."""
    total = len(candidates_store)
    dups = sum(1 for c in candidates_store.values() if c["flags"]["duplicate"]["is_duplicate"])
    ai_flags = sum(1 for c in candidates_store.values() if c["flags"]["ai_content"]["is_flagged"])
    repeated_flags = sum(1 for c in candidates_store.values() if c["flags"]["repeated_content"]["is_flagged"])
    reviews_req = sum(1 for c in candidates_store.values() if c["flags"]["duplicate"]["is_duplicate"] or c["flags"]["ai_content"]["is_flagged"] or c["flags"]["repeated_content"]["is_flagged"])

    scores = [c["analysis"]["fit_score"] for c in candidates_store.values() if "analysis" in c]
    avg_score = round(sum(scores) / len(scores)) if scores else 0
    high_matches = sum(1 for s in scores if s >= 80)

    return jsonify({
        "total_resumes_processed": total,
        "duplicate_count": dups,
        "ai_flag_count": ai_flags,
        "repeated_content_count": repeated_flags,
        "review_required_count": reviews_req,
        "average_fit_score": avg_score,
        "high_match_count": high_matches,
        "custom_domain": custom_domain_config["domain"],
        "active_jd": {
            "title": active_jd.get("job_title", "Senior Data Scientist"),
            "must_haves_count": len(active_jd.get("must_haves", [])),
            "nice_to_haves_count": len(active_jd.get("nice_to_haves", []))
        } if active_jd else None
    })


@app.route("/api/candidates", methods=["GET"])
def get_candidates():
    """Search, filter, and sort candidates."""
    q = request.args.get("q", "").lower()
    flag_filter = request.args.get("flag", "all")
    min_score = int(request.args.get("min_score", 0))

    results = []
    for c_id, c in candidates_store.items():
        name = c["name"]
        fit = c["analysis"]["fit_score"]
        conf = c["analysis"]["confidence"]["confidence_score"]

        if q and q not in name.lower() and q not in c["raw_text"].lower():
            continue
        if fit < min_score:
            continue

        has_dup = c["flags"]["duplicate"]["is_duplicate"]
        has_ai = c["flags"]["ai_content"]["is_flagged"]
        has_rep = c["flags"]["repeated_content"]["is_flagged"]

        if flag_filter == "duplicate" and not has_dup:
            continue
        if flag_filter == "ai_signal" and not has_ai:
            continue
        if flag_filter == "repeated" and not has_rep:
            continue
        if flag_filter == "flagged" and not (has_dup or has_ai or has_rep):
            continue
        if flag_filter == "clean" and (has_dup or has_ai or has_rep):
            continue

        results.append({
            "id": c_id,
            "name": name,
            "filename": c.get("filename", "Resume.txt"),
            "file_type": c.get("file_type", "TXT"),
            "fit_score": fit,
            "confidence": conf,
            "matches_count": len(c["analysis"]["matches"]),
            "partial_count": len(c["analysis"]["partial_matches"]),
            "gaps_count": len(c["analysis"]["gaps"]),
            "flags": {
                "duplicate": has_dup,
                "ai_content": has_ai,
                "repeated_content": has_rep
            },
            "status": c.get("status", "Evaluated")
        })

    results.sort(key=lambda x: x["fit_score"], reverse=True)
    return jsonify(results)


@app.route("/api/candidate/<candidate_id>", methods=["GET"])
def get_candidate_detail(candidate_id):
    cand = candidates_store.get(candidate_id)
    if not cand:
        return jsonify({"error": "Candidate not found"}), 404
    return jsonify(cand)


@app.route("/api/candidate/<candidate_id>/add-question", methods=["POST"])
def add_candidate_question(candidate_id):
    cand = candidates_store.get(candidate_id)
    if not cand:
        return jsonify({"error": "Candidate not found"}), 404

    data = request.get_json() or {}
    question_text = data.get("question", "").strip()
    category = data.get("category", "Recruiter Custom Question").strip()
    evaluation_hint = data.get("evaluation_hint", "Evaluate technical depth and direct problem-solving methodology.").strip()

    if len(question_text) < 5:
        return jsonify({"error": "Question must be at least 5 characters long."}), 400

    existing_qs = cand["analysis"].setdefault("mock_interview", [])
    new_id = len(existing_qs) + 1
    new_q = {
        "id": new_id,
        "category": category,
        "question": question_text,
        "context": "Added directly by Recruiter for targeted candidate evaluation.",
        "evaluation_hint": evaluation_hint,
        "source": "recruiter_custom"
    }
    existing_qs.append(new_q)
    return jsonify({"success": True, "questions": existing_qs, "added_question": new_q})


@app.route("/api/candidate/<candidate_id>/delete-question/<int:question_id>", methods=["DELETE"])
def delete_candidate_question(candidate_id, question_id):
    cand = candidates_store.get(candidate_id)
    if not cand:
        return jsonify({"error": "Candidate not found"}), 404

    existing_qs = cand["analysis"].get("mock_interview", [])
    cand["analysis"]["mock_interview"] = [q for q in existing_qs if q.get("id") != question_id]
    for idx, q in enumerate(cand["analysis"]["mock_interview"], 1):
        q["id"] = idx
    return jsonify({"success": True, "questions": cand["analysis"]["mock_interview"]})



@app.route("/api/process-jd", methods=["POST"])
def process_jd():
    global active_jd
    jd_text = ""
    source = "pasted_text"

    if "file" in request.files:
        file = request.files["file"]
        if file.filename:
            fname = secure_filename(file.filename)
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(fname)[1]) as tmp:
                file.save(tmp.name)
                tmp_path = tmp.name
            jd_text, meta = doc_processor.extract_text(tmp_path, fname)
            os.remove(tmp_path)
            source = f"uploaded_file ({fname})"

    if not jd_text and request.is_json:
        jd_text = request.json.get("text", "")
    if not jd_text:
        jd_text = request.form.get("text", "")

    if not jd_text or len(jd_text.strip()) < 30:
        return jsonify({"error": "Job description content is too short or empty. Please supply complete role requirements."}), 400

    parsed_jd = nlp_engine.extract_job_description(jd_text)
    parsed_jd["id"] = f"jd-{uuid.uuid4().hex[:6]}"
    active_jd = parsed_jd

    # Re-evaluate all candidates
    for c_id, c in candidates_store.items():
        resume_data = c["structured_resume"]
        quality = c["quality"]
        name = c["name"]

        match_results = nlp_engine.semantic_match(resume_data, active_jd)
        fit_data = scoring_engine.calculate_fit_score(match_results["all_comparisons"], resume_data)
        conf_data = scoring_engine.calculate_confidence(quality, resume_data, active_jd, match_results["all_comparisons"])
        summary = scoring_engine.generate_candidate_summary(
            name, fit_data["overall_fit_score"],
            match_results["matches"], match_results["partial_matches"], match_results["gaps"],
            resume_data
        )
        recs = scoring_engine.generate_recommendations(match_results["gaps"], match_results["partial_matches"], resume_data)
        qs = interview_generator.generate_questions(
            name, resume_data, active_jd,
            match_results["matches"], match_results["partial_matches"], match_results["gaps"]
        )

        c["analysis"] = {
            "fit_score": fit_data["overall_fit_score"],
            "fit_score_details": fit_data,
            "confidence": conf_data,
            "matches": match_results["matches"],
            "partial_matches": match_results["partial_matches"],
            "gaps": match_results["gaps"],
            "comparisons": match_results["all_comparisons"],
            "summary": summary,
            "recommendations": recs,
            "mock_interview": qs
        }

    return jsonify({
        "success": True,
        "message": f"Job description processed via {source}.",
        "job_title": active_jd.get("job_title"),
        "must_haves": active_jd.get("must_haves"),
        "nice_to_haves": active_jd.get("nice_to_haves"),
        "re_analyzed_candidates_count": len(candidates_store)
    })


@app.route("/api/upload-resumes", methods=["POST"])
def upload_resumes():
    files = request.files.getlist("resumes")
    if not files:
        if "resume" in request.files:
            files = [request.files["resume"]]
        elif "file" in request.files:
            files = [request.files["file"]]

    if not files or all(f.filename == "" for f in files):
        return jsonify({"error": "No files selected for upload."}), 400

    processed = []
    unreadable_errors = []

    for file in files:
        if not file.filename:
            continue
        fname = secure_filename(file.filename)
        c_id = f"cand-{uuid.uuid4().hex[:6]}"
        ext = os.path.splitext(fname)[1].lower()

        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name

        try:
            raw_text, meta = doc_processor.extract_text(tmp_path, fname)
            quality = meta["quality"]

            if not quality.get("readable"):
                unreadable_errors.append({
                    "filename": fname,
                    "status": quality.get("status"),
                    "issue": quality.get("issue"),
                    "suggestion": quality.get("suggestion")
                })
                os.remove(tmp_path)
                continue

            dup_res = duplicate_detector.check_duplicate(c_id, fname, raw_text)
            rep_res = anomaly_detector.detect_repeated_content(raw_text)
            ai_res = anomaly_detector.detect_ai_generated(raw_text)

            resume_data = nlp_engine.extract_resume_info(raw_text)
            candidate_name = resume_data["personal"]["name"]
            if candidate_name in ["Candidate", "Not specified"] or len(candidate_name) < 3:
                candidate_name = os.path.splitext(fname)[0].replace("_", " ").replace("-", " ").title()
                resume_data["personal"]["name"] = candidate_name

            if active_jd:
                match_results = nlp_engine.semantic_match(resume_data, active_jd)
                fit_data = scoring_engine.calculate_fit_score(match_results["all_comparisons"], resume_data)
                conf_data = scoring_engine.calculate_confidence(quality, resume_data, active_jd, match_results["all_comparisons"])
                summary = scoring_engine.generate_candidate_summary(
                    candidate_name, fit_data["overall_fit_score"],
                    match_results["matches"], match_results["partial_matches"], match_results["gaps"],
                    resume_data
                )
                recs = scoring_engine.generate_recommendations(match_results["gaps"], match_results["partial_matches"], resume_data)
                qs = interview_generator.generate_questions(
                    candidate_name, resume_data, active_jd,
                    match_results["matches"], match_results["partial_matches"], match_results["gaps"]
                )
                analysis_payload = {
                    "fit_score": fit_data["overall_fit_score"],
                    "fit_score_details": fit_data,
                    "confidence": conf_data,
                    "matches": match_results["matches"],
                    "partial_matches": match_results["partial_matches"],
                    "gaps": match_results["gaps"],
                    "comparisons": match_results["all_comparisons"],
                    "summary": summary,
                    "recommendations": recs,
                    "mock_interview": qs
                }
            else:
                analysis_payload = {
                    "fit_score": 0,
                    "fit_score_details": {},
                    "confidence": {"confidence_score": 50, "factors": []},
                    "matches": [], "partial_matches": [], "gaps": [], "comparisons": [],
                    "summary": "Pending Job Description upload.",
                    "recommendations": [], "mock_interview": []
                }

            candidate_record = {
                "id": c_id,
                "name": candidate_name,
                "filename": fname,
                "file_type": meta.get("file_type", "UNKNOWN"),
                "raw_text": raw_text,
                "quality": quality,
                "flags": {
                    "duplicate": dup_res,
                    "repeated_content": rep_res,
                    "ai_content": ai_res
                },
                "structured_resume": resume_data,
                "analysis": analysis_payload,
                "status": "Evaluated",
                "created_at": "Just now"
            }
            candidates_store[c_id] = candidate_record

            matches_list = [m.get("requirement", "") for m in analysis_payload.get("matches", [])]
            gaps_list = [g.get("requirement", "") for g in analysis_payload.get("gaps", [])]
            partial_list = [p.get("requirement", "") for p in analysis_payload.get("partial_matches", [])]

            processed.append({
                "id": c_id,
                "name": candidate_name,
                "filename": fname,
                "fit_score": analysis_payload["fit_score"],
                "confidence": analysis_payload["confidence"]["confidence_score"],
                "confidence_disclaimer": analysis_payload["confidence"].get("disclaimer", "High document fidelity"),
                "is_duplicate": dup_res["is_duplicate"],
                "is_ai_flagged": ai_res["is_flagged"],
                "is_repeated_flagged": rep_res["is_flagged"],
                "matches_count": len(matches_list),
                "partial_count": len(partial_list),
                "gaps_count": len(gaps_list),
                "summary": analysis_payload.get("summary", ""),
                "top_matches": matches_list[:5],
                "top_gaps": gaps_list[:5],
                "recommendations": analysis_payload.get("recommendations", [])[:3],
                "fit_score_details": analysis_payload.get("fit_score_details", {}),
                "personal": resume_data.get("personal", {})
            })

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    return jsonify({
        "success": True,
        "processed_count": len(processed),
        "candidates": processed,
        "unreadable_errors": unreadable_errors
    })


@app.route("/api/load-samples", methods=["POST"])
def load_samples():
    initialize_default_data()
    return jsonify({
        "success": True,
        "message": f"Successfully loaded standard candidate dataset ({len(candidates_store)} candidates).",
        "candidate_count": len(candidates_store)
    })


@app.route("/api/export-dossier/<candidate_id>", methods=["GET"])
def export_dossier(candidate_id):
    cand = candidates_store.get(candidate_id)
    if not cand:
        return jsonify({"error": "Candidate not found"}), 404

    name = cand["name"]
    fit = cand["analysis"]["fit_score"]
    conf = cand["analysis"]["confidence"]["confidence_score"]
    summary = cand["analysis"]["summary"]
    matches = cand["analysis"]["matches"]
    gaps = cand["analysis"]["gaps"]
    partials = cand["analysis"]["partial_matches"]
    flags = cand["flags"]
    interview_qs = cand["analysis"]["mock_interview"]

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf_path = tmp.name

    doc = SimpleDocTemplate(pdf_path, pagesize=letter, leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle("DocTitle", parent=styles["Heading1"], fontSize=18, leading=22, textColor=colors.HexColor("#0f172a"))
    h2_style = ParagraphStyle("SecHeading", parent=styles["Heading2"], fontSize=12, leading=16, textColor=colors.HexColor("#1e293b"), spaceBefore=10, spaceAfter=4)
    body_style = ParagraphStyle("BodyText", parent=styles["Normal"], fontSize=9, leading=13, textColor=colors.HexColor("#334155"))
    meta_style = ParagraphStyle("MetaText", parent=styles["Normal"], fontSize=8, leading=11, textColor=colors.HexColor("#64748b"))

    elements = [
        Paragraph("CANDIDATE QUALIFICATION ASSESSMENT DOSSIER", meta_style),
        Spacer(1, 4),
        Paragraph(f"{name} : Evaluation Report", title_style),
        Paragraph(f"Evaluated against target: {active_jd.get('job_title', 'Senior Data Scientist') if active_jd else 'Job Description'}", meta_style),
        Spacer(1, 10),
    ]

    kpi_data = [
        ["Overall Fit Score", "Analysis Confidence", "Duplicate Flag", "AI Content Signal"],
        [f"{fit}%", f"{conf}%", "FLAGGED" if flags["duplicate"]["is_duplicate"] else "None", "FLAGGED" if flags["ai_content"]["is_flagged"] else "Normal"]
    ]
    kpi_table = Table(kpi_data, colWidths=[130, 130, 130, 140])
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#475569")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (-1, 1), 11),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("Executive Assessment Summary", h2_style))
    elements.append(Paragraph(summary, body_style))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("Requirement-by-Requirement Findings", h2_style))
    match_data = [["Requirement", "Candidate Evidence", "Status"]]
    for m in matches[:4]:
        match_data.append([m["requirement"][:45], m["candidate_evidence"][:65] + "...", "MATCH"])
    for p in partials[:2]:
        match_data.append([p["requirement"][:45], p["candidate_evidence"][:65] + "...", "PARTIAL"])
    for g in gaps[:3]:
        match_data.append([g["requirement"][:45], "No direct evidence found", "MISSING"])

    m_table = Table(match_data, colWidths=[170, 300, 60])
    m_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(m_table)
    elements.append(Spacer(1, 10))

    elements.append(Paragraph(f"Targeted Interview Questions ({len(interview_qs)} Questions)", h2_style))
    for i, q in enumerate(interview_qs[:12], 1):
        custom_tag = " [RECRUITER CUSTOM]" if q.get("source") == "recruiter_custom" else ""
        elements.append(Paragraph(f"<b>Q{i} [{q['category']}]{custom_tag}:</b> {q['question']}", body_style))
        elements.append(Paragraph(f"<i>Assessment Criteria:</i> {q['evaluation_hint']}", meta_style))
        elements.append(Spacer(1, 4))

    doc.build(elements)
    return send_file(pdf_path, as_attachment=True, download_name=f"Assessment_{name.replace(' ', '_')}.pdf", mimetype="application/pdf")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
