import json
import re
from pathlib import Path

from backend.app.services.embedding_service import (
    create_embedding,
    cosine_similarity,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]

STORAGE_DIR = (
    PROJECT_ROOT
    / "backend"
    / "data"
    / "documents"
)

# ---------------------------------------------------------
# TEXT UTILITIES
# ---------------------------------------------------------

def normalize_text(text: str) -> str:
    if not text:
        return ""

    text = text.lower()

    text = text.replace("\u00a0", " ")
    text = text.replace("\u200b", "")
    text = text.replace("\ufeff", "")

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def tokenize(text: str) -> list[str]:
    return re.findall(
        r"\b[a-zA-Z0-9]{2,}\b",
        normalize_text(text)
    )


# ---------------------------------------------------------
# KEYWORD MATCHING
# ---------------------------------------------------------

def keyword_score(query: str, text: str) -> float:

    query_tokens = set(tokenize(query))
    text_tokens = set(tokenize(text))

    if not query_tokens or not text_tokens:
        return 0.0

    matches = query_tokens.intersection(text_tokens)

    return len(matches) / len(query_tokens)


# ---------------------------------------------------------
# PHRASE MATCHING
# ---------------------------------------------------------

def phrase_score(query: str, text: str) -> float:

    query_normalized = normalize_text(query)
    text_normalized = normalize_text(text)

    if not query_normalized:
        return 0.0

    # Exact phrase
    if query_normalized in text_normalized:
        return 1.0

    query_tokens = tokenize(query_normalized)

    if len(query_tokens) < 2:
        return 0.0

    matched = 0

    for index in range(len(query_tokens) - 1):

        phrase = (
            query_tokens[index]
            + " "
            + query_tokens[index + 1]
        )

        if phrase in text_normalized:
            matched += 1

    return matched / max(
        1,
        len(query_tokens) - 1
    )


# ---------------------------------------------------------
# QUESTION INTENT
# ---------------------------------------------------------

def detect_question_intent(query: str) -> str:

    q = normalize_text(query)

    # Person / organization identity
    if re.search(
        r"\bwho\b|\bwhom\b|\bwhose\b",
        q
    ):
        return "identity"

    # Organization / institution
    if re.search(
        r"\bwhich organization\b"
        r"|\bwhich institution\b"
        r"|\bwhich company\b"
        r"|\bwhat organization\b"
        r"|\bwhat institution\b"
        r"|\bwhat company\b",
        q
    ):
        return "organization"

    # Date / time
    if re.search(
        r"\bwhen\b"
        r"|\bdate\b"
        r"|\bdated\b"
        r"|\bissued on\b"
        r"|\bstart date\b"
        r"|\bend date\b"
        r"|\bduration\b",
        q
    ):
        return "date"

    # Location
    if re.search(
        r"\bwhere\b"
        r"|\blocation\b"
        r"|\bplace\b"
        r"|\bcity\b"
        r"|\baddress\b",
        q
    ):
        return "location"

    # Numbers / amounts
    if re.search(
        r"\bhow many\b"
        r"|\bhow much\b"
        r"|\bamount\b"
        r"|\btotal\b"
        r"|\bnumber\b",
        q
    ):
        return "numeric"

    # Summary / broad questions
    if is_broad_question(q):
        return "broad"

    return "general"


# ---------------------------------------------------------
# GENERIC QUERY EXPANSION
# ---------------------------------------------------------

def expand_query(query: str) -> str:

    intent = detect_question_intent(query)

    expansions = {
        "identity": (
            "who person name identity "
            "issued by provided by awarded by "
            "certified by organization institution "
            "company authority"
        ),

        "organization": (
            "organization institution company "
            "issuer provider authority "
            "institution name"
        ),

        "date": (
            "date dated issued start end duration "
            "period time"
        ),

        "location": (
            "location place city address "
            "venue office institution"
        ),

        "numeric": (
            "number amount total count "
            "quantity value"
        ),

        "broad": (
            "document certificate report purpose "
            "subject title organization"
        ),

        "general": ""
    }

    expansion = expansions.get(
        intent,
        ""
    )

    if expansion:
        return query + " " + expansion

    return query


# ---------------------------------------------------------
# GENERIC ENTITY / ORGANIZATION EVIDENCE
# ---------------------------------------------------------

def organization_evidence_score(
    text: str,
    intent: str
) -> float:

    if intent not in {
        "identity",
        "organization"
    }:
        return 0.0

    normalized = normalize_text(text)

    score = 0.0

    # Generic phrases commonly associated with
    # document issuers/providers.
    issuer_phrases = [
        "issued by",
        "provided by",
        "awarded by",
        "certified by",
        "presented by",
        "granted by",
        "authorized by",
        "on behalf of",
        "this is to certify",
        "certificate of",
        "certify that",
    ]

    for phrase in issuer_phrases:

        if phrase in normalized:
            score += 0.18

    # Generic organizational indicators.
    organization_words = [
        "limited",
        "ltd",
        "private",
        "pvt",
        "llp",
        "inc",
        "corporation",
        "company",
        "institute",
        "institution",
        "university",
        "college",
        "school",
        "department",
        "organization",
        "technologies",
        "technology",
        "services",
        "systems",
        "foundation",
        "authority",
        "office",
        "center",
        "centre",
    ]

    organization_matches = 0

    for word in organization_words:

        if re.search(
            r"\b" + re.escape(word) + r"\b",
            normalized
        ):
            organization_matches += 1

    if organization_matches:
        score += min(
            0.35,
            organization_matches * 0.07
        )

    return min(
        score,
        1.0
    )


# ---------------------------------------------------------
# IDENTITY EVIDENCE
# ---------------------------------------------------------

def identity_evidence_score(
    text: str,
    intent: str
) -> float:

    if intent != "identity":
        return 0.0

    normalized = normalize_text(text)

    score = 0.0

    identity_phrases = [
        "name of",
        "named",
        "recipient",
        "candidate",
        "applicant",
        "student",
        "author",
        "issued by",
        "provided by",
        "awarded by",
        "certified by",
        "head",
        "director",
        "manager",
        "coordinator",
        "founder",
        "signatory",
    ]

    for phrase in identity_phrases:

        if phrase in normalized:
            score += 0.08

    return min(
        score,
        0.5
    )


# ---------------------------------------------------------
# DATE EVIDENCE
# ---------------------------------------------------------

def date_evidence_score(
    text: str,
    intent: str
) -> float:

    if intent != "date":
        return 0.0

    normalized = normalize_text(text)

    score = 0.0

    date_patterns = [
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        r"\b\d{1,2}\s+"
        r"(?:january|february|march|april|may|june|"
        r"july|august|september|october|november|december)"
        r"\s+\d{2,4}\b",
        r"\b(?:january|february|march|april|may|june|"
        r"july|august|september|october|november|december)"
        r"\s+\d{1,2},?\s+\d{2,4}\b",
    ]

    for pattern in date_patterns:

        if re.search(pattern, normalized):
            score += 0.2

    return min(
        score,
        0.5
    )


# ---------------------------------------------------------
# LOCATION EVIDENCE
# ---------------------------------------------------------

def location_evidence_score(
    text: str,
    intent: str
) -> float:

    if intent != "location":
        return 0.0

    normalized = normalize_text(text)

    location_words = [
        "located",
        "location",
        "address",
        "office",
        "campus",
        "city",
        "district",
        "state",
        "country",
        "place",
        "venue",
        "at",
        "in",
    ]

    matches = 0

    for word in location_words:

        if re.search(
            r"\b" + re.escape(word) + r"\b",
            normalized
        ):
            matches += 1

    return min(
        matches * 0.06,
        0.35
    )


# ---------------------------------------------------------
# BROAD QUESTIONS
# ---------------------------------------------------------

def is_broad_question(query: str) -> bool:

    normalized = normalize_text(query)

    broad_patterns = [

        r"\bwhat is this\b",

        r"\bwhat is this pdf\b",

        r"\bwhat is this document\b",

        r"\bwhat does this document\b",

        r"\bwhat does this pdf\b",

        r"\bwhat is the document about\b",

        r"\bwhat is the pdf about\b",

        r"\bwhat is this about\b",

        r"\bsummarize\b",

        r"\bsummary\b",

        r"\bmain idea\b",

        r"\bpurpose of this document\b",
    ]

    return any(
        re.search(
            pattern,
            normalized
        )
        for pattern in broad_patterns
    )


# ---------------------------------------------------------
# LOAD DOCUMENT
# ---------------------------------------------------------

def load_document(
    document_id: str
) -> dict:

    file_path = (
        STORAGE_DIR
        / f"{document_id}.json"
    )

    if not file_path.exists():

        raise FileNotFoundError(
            f"Document not found: {document_id}"
        )

    with open(
        file_path,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


# ---------------------------------------------------------
# MAIN SEARCH
# ---------------------------------------------------------

def search_document(
    document_id: str,
    query: str,
    top_k: int = 5
) -> list[dict]:

    document = load_document(
        document_id
    )

    chunks = document.get(
        "chunks",
        []
    )

    if not chunks:
        return []

    query = query.strip()

    if not query:
        return []

    # Detect question type.
    intent = detect_question_intent(
        query
    )

    # Expanded query improves semantic retrieval
    # without knowing anything about the document.
    expanded_query = expand_query(
        query
    )

    broad_question = is_broad_question(
        query
    )

    # Create embedding once.
    query_embedding = create_embedding(
        expanded_query
    )

    results = []

    for chunk in chunks:

        chunk_text = (
            chunk.get("text", "")
            .strip()
        )

        if not chunk_text:
            continue

        # -------------------------------------------------
        # SEMANTIC SCORE
        # -------------------------------------------------

        chunk_embedding = chunk.get(
            "embedding"
        )

        semantic_score = 0.0

        if chunk_embedding:

            try:

                semantic_score = (
                    cosine_similarity(
                        query_embedding,
                        chunk_embedding
                    )
                )

            except Exception:

                semantic_score = 0.0

        # -------------------------------------------------
        # LEXICAL SCORE
        # -------------------------------------------------

        lexical_score = keyword_score(
            query,
            chunk_text
        )

        # -------------------------------------------------
        # PHRASE SCORE
        # -------------------------------------------------

        exact_phrase_score = phrase_score(
            query,
            chunk_text
        )

        # -------------------------------------------------
        # GENERIC QUESTION-AWARE EVIDENCE
        # -------------------------------------------------

        organization_score = (
            organization_evidence_score(
                chunk_text,
                intent
            )
        )

        identity_score = (
            identity_evidence_score(
                chunk_text,
                intent
            )
        )

        date_score = (
            date_evidence_score(
                chunk_text,
                intent
            )
        )

        location_score = (
            location_evidence_score(
                chunk_text,
                intent
            )
        )

        # -------------------------------------------------
        # FINAL SCORE
        # -------------------------------------------------

        final_score = (
            semantic_score * 0.42
            + lexical_score * 0.20
            + exact_phrase_score * 0.10
            + organization_score * 0.13
            + identity_score * 0.07
            + date_score * 0.04
            + location_score * 0.04
        )

        results.append({

            "chunk_id": chunk.get(
                "chunk_id"
            ),

            "page": chunk.get(
                "page"
            ),

            "text": chunk_text,

            "semantic_score": round(
                float(semantic_score),
                4
            ),

            "keyword_score": round(
                float(lexical_score),
                4
            ),

            "phrase_score": round(
                float(exact_phrase_score),
                4
            ),

            "organization_score": round(
                float(organization_score),
                4
            ),

            "identity_score": round(
                float(identity_score),
                4
            ),

            "date_score": round(
                float(date_score),
                4
            ),

            "location_score": round(
                float(location_score),
                4
            ),

            "score": round(
                float(final_score),
                4
            )
        })

    # Highest relevance first.
    results.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    # -------------------------------------------------
    # RETURN MORE EVIDENCE FOR IDENTITY QUESTIONS
    # -------------------------------------------------

    if intent in {
        "identity",
        "organization"
    }:

        return results[
            :max(
                3,
                min(
                    top_k,
                    6
                )
            )
        ]

    # Broad questions need several pieces of evidence.
    if broad_question:

        return results[
            :max(
                3,
                min(
                    top_k,
                    6
                )
            )
        ]

    return results[
        :max(
            1,
            top_k
        )
    ]