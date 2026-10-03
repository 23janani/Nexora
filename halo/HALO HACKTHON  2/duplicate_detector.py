"""
Duplicate Resume Detector
Uses multi-tiered content similarity (exact hash, word 3-gram Jaccard, and character shingles)
to detect identical or near-duplicate resumes across batches and historical database.
"""

import hashlib
import re
from typing import List, Dict, Any, Optional


class DuplicateDetector:
    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
        # In-memory repository of processed resumes: id -> {name, hash, shingles, text}
        self.repository: Dict[str, Dict[str, Any]] = {}

    def _get_hash(self, text: str) -> str:
        clean = re.sub(r"\s+", "", text.lower())
        return hashlib.sha256(clean.encode("utf-8")).hexdigest()

    def _get_shingles(self, text: str, k: int = 3) -> set:
        tokens = re.findall(r"\b\w+\b", text.lower())
        if len(tokens) < k:
            return set(tokens)
        return set(" ".join(tokens[i:i+k]) for i in range(len(tokens) - k + 1))

    def _jaccard_similarity(self, set_a: set, set_b: set) -> float:
        if not set_a or not set_b:
            return 0.0
        intersection = len(set_a.intersection(set_b))
        union = len(set_a.union(set_b))
        return intersection / union if union > 0 else 0.0

    def check_duplicate(self, candidate_id: str, candidate_name: str, text: str, existing_resumes: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Compare candidate against provided resumes or internal repository.
        Uses exact hash, token containment, Jaccard, and TF-IDF cosine similarity.
        """
        curr_hash = self._get_hash(text)
        curr_tokens = set(re.findall(r"\b\w{3,}\b", text.lower()))

        pool = []
        if existing_resumes:
            for item in existing_resumes:
                if item.get("id") != candidate_id:
                    pool.append(item)
        else:
            for c_id, data in self.repository.items():
                if c_id != candidate_id:
                    pool.append({"id": c_id, "name": data.get("name"), "text": data.get("text")})

        highest_sim = 0.0
        duplicate_of = None
        match_type = "None"

        for other in pool:
            other_text = other.get("text", "")
            other_id = other.get("id")
            other_name = other.get("name", "Unknown Candidate")

            # 1. Exact Hash
            other_hash = self._get_hash(other_text)
            if curr_hash == other_hash:
                highest_sim = 1.0
                duplicate_of = {"id": other_id, "name": other_name}
                match_type = "Exact Match (100% Content Hash)"
                break

            # 2. Token Containment & Jaccard
            other_tokens = set(re.findall(r"\b\w{3,}\b", other_text.lower()))
            if not curr_tokens or not other_tokens:
                continue

            intersection = len(curr_tokens.intersection(other_tokens))
            union = len(curr_tokens.union(other_tokens))
            jaccard = intersection / union if union > 0 else 0.0
            containment = intersection / min(len(curr_tokens), len(other_tokens))

            # 3. TF-IDF Cosine
            try:
                from sklearn.feature_extraction.text import TfidfVectorizer
                from sklearn.metrics.pairwise import cosine_similarity
                v = TfidfVectorizer()
                m = v.fit_transform([text, other_text])
                cos_sim = float(cosine_similarity(m[0:1], m[1:2])[0][0])
            except Exception:
                cos_sim = 0.0

            # Combined Metric: high containment strongly indicates duplicate/copied resume
            combined_sim = max(cos_sim, (0.3 * jaccard + 0.7 * containment))

            if combined_sim > highest_sim:
                highest_sim = combined_sim
                if combined_sim >= self.similarity_threshold:
                    duplicate_of = {"id": other_id, "name": other_name}
                    match_type = f"Near-Duplicate ({round(combined_sim * 100, 1)}% Content Overlap)"

        is_duplicate = highest_sim >= self.similarity_threshold

        # Store in repository
        self.repository[candidate_id] = {
            "name": candidate_name,
            "hash": curr_hash,
            "tokens": curr_tokens,
            "text": text
        }

        return {
            "is_duplicate": is_duplicate,
            "similarity_score": round(highest_sim * 100, 1),
            "match_type": match_type,
            "duplicate_of": duplicate_of,
            "details": f"Flagged as duplicate of {duplicate_of['name']} ({round(highest_sim*100, 1)}% similarity)." if is_duplicate else "No duplicate detected."
        }
