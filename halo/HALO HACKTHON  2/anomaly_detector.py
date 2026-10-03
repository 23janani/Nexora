"""
Anomaly & Integrity Detector:
1. Repeated / Unusual Content Detector (Keyword stuffing, duplicate sections, abnormal loops)
2. AI-Generated Content Signal (Lexical burstiness, sentence length variance, synthetic clichés)
Strict adherence: Flags are review signals only; candidate is NOT automatically rejected.
"""

import re
import math
from collections import Counter
from typing import Dict, Any, List


class AnomalyDetector:
    def __init__(self):
        # Known synthetic / generic AI resume clichés
        self.ai_markers = [
            r"\btestament to\b",
            r"\bspearheaded\b",
            r"\bleveraged cutting-edge\b",
            r"\bdelving into\b",
            r"\bplayed a pivotal role\b",
            r"\brobust and scalable\b",
            r"\bseamlessly integrated\b",
            r"\bmeticulously crafted\b",
            r"\bholistic approach\b",
            r"\bshowcasing a proven track record\b",
            r"\bfostered cross-functional collaboration\b",
            r"\bdriving impactful business outcomes\b"
        ]

    def detect_repeated_content(self, text: str) -> Dict[str, Any]:
        """
        Analyze resume for:
        - excessive repeated phrases or sentences
        - suspiciously repeated sections
        - keyword stuffing
        """
        sentences = [s.strip() for s in re.split(r"[.\n;•]+", text) if len(s.strip()) > 15]
        words = re.findall(r"\b[A-Za-z]{3,}\b", text.lower())

        issues = []
        repeated_phrases = []

        # 1. Exact or near-identical sentence repetition
        sentence_counts = Counter([re.sub(r"\s+", " ", s.lower()) for s in sentences])
        for sent, count in sentence_counts.items():
            if count >= 3:
                issues.append(f"Sentence or bullet repeated {count} times: \"{sent[:60]}...\"")
                repeated_phrases.append(sent[:50])

        # 2. N-gram phrase repetition (4-word sequences)
        if len(words) >= 4:
            four_grams = [" ".join(words[i:i+4]) for i in range(len(words) - 3)]
            ngram_counts = Counter(four_grams)
            for phrase, cnt in ngram_counts.items():
                if cnt >= 4:
                    issues.append(f"Unusual 4-word phrase repeated {cnt} times: \"{phrase}\"")
                    repeated_phrases.append(phrase)

        # 3. Keyword stuffing check (any single non-stopword exceeding 5% of total words)
        stopwords = {
            "and", "the", "with", "for", "that", "this", "from", "data", "experience",
            "worked", "using", "team", "project", "system", "development", "years"
        }
        filtered_words = [w for w in words if w not in stopwords]
        word_counts = Counter(filtered_words)
        total_filtered = len(filtered_words)

        stuffed_terms = []
        if total_filtered > 50:
            for term, count in word_counts.most_common(10):
                term_ratio = count / total_filtered
                if term_ratio > 0.06 and count >= 8:
                    stuffed_terms.append(f"'{term}' ({count}x, {round(term_ratio*100, 1)}% of text)")

        if stuffed_terms:
            issues.append(f"Potential keyword stuffing detected: {', '.join(stuffed_terms)}")

        # 4. Repeated section headers
        headers = re.findall(r"(?i)\b(experience|education|skills|projects|certifications)\b", text)
        header_counts = Counter([h.lower() for h in headers])
        for h, count in header_counts.items():
            if count >= 4:
                issues.append(f"Section header '{h.upper()}' appears unusually often ({count} times)")

        is_flagged = len(issues) > 0

        return {
            "is_flagged": is_flagged,
            "status": "Repeated / Unusual Content Flagged" if is_flagged else "Clean",
            "issue_count": len(issues),
            "issues": issues,
            "repeated_samples": repeated_phrases[:3],
            "severity": "High" if len(issues) >= 3 else ("Moderate" if len(issues) >= 1 else "Low"),
            "action_note": "Review flagged sections for accidental duplication or deliberate keyword inflation."
        }

    def detect_ai_generated(self, text: str) -> Dict[str, Any]:
        """
        Calculates heuristic signals for potentially AI-generated resume content:
        - Lexical burstiness / variance in sentence length
        - Prevalence of known AI transition and framing markers
        - Type-token vocabulary uniformity
        DISCLAIMER: Probabilistic review signal only. Never reject candidate based solely on AI flag.
        """
        sentences = [s.strip() for s in re.split(r"[.\n?!]+", text) if len(s.strip()) > 10]
        words = re.findall(r"\b[a-z]{2,}\b", text.lower())

        if len(sentences) < 3 or len(words) < 30:
            return {
                "is_flagged": False,
                "signal_level": "Insufficient Data",
                "display_text": "AI-content signal: Normal (Sparse text)",
                "confidence_score": 50,
                "markers_found": [],
                "disclaimer": "AI content detection is a probabilistic heuristic and not 100% accurate. Do not automatically reject."
            }

        # 1. AI marker density
        found_markers = []
        for pattern in self.ai_markers:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                found_markers.append(matches[0].lower())

        marker_density = len(found_markers)

        # 2. Sentence length variance (Burstiness)
        lengths = [len(s.split()) for s in sentences]
        avg_len = sum(lengths) / len(lengths)
        variance = sum((l - avg_len) ** 2 for l in lengths) / len(lengths)
        std_dev = math.sqrt(variance)

        # Human writing typically exhibits high variance (short bullets + long narrative).
        # Synthetic LLM resumes often exhibit uniform sentence lengths (std_dev < 4.5).
        low_burstiness = std_dev < 4.5 and len(sentences) >= 6

        # 3. Type-Token Ratio (TTR)
        unique_words = len(set(words))
        ttr = unique_words / len(words)

        # Composite score
        score = 0
        if marker_density >= 3:
            score += 45
        elif marker_density >= 2:
            score += 30
        elif marker_density >= 1:
            score += 15

        if low_burstiness:
            score += 30

        if 0.35 <= ttr <= 0.65 and len(words) >= 40:
            score += 15

        is_flagged = score >= 40 or marker_density >= 3

        return {
            "is_flagged": is_flagged,
            "signal_level": "High" if score >= 60 else ("Moderate" if is_flagged else "Low"),
            "display_text": "Possible AI-generated content detected" if is_flagged else "AI-content signal: Normal",
            "score": min(score, 95),
            "markers_found": list(set(found_markers))[:5],
            "low_burstiness": low_burstiness,
            "std_dev_sentence_length": round(std_dev, 2),
            "disclaimer": "Possible AI-generated content detected. Note: AI detection is a probabilistic heuristic and is NOT 100% accurate. Treat this purely as an informational review signal, not grounds for rejection."
        }
