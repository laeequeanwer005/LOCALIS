from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
)

import torch
import re


# =========================================================
# MODEL CONFIGURATION
# =========================================================

MODEL_NAME = "Qwen/Qwen3-0.6B"

MAX_NEW_TOKENS = 64
MAX_CONTEXT_CHARS = 9000
MAX_INPUT_TOKENS = 3072


# =========================================================
# MODEL CACHE
# =========================================================

_tokenizer = None
_model = None


# =========================================================
# LOAD LOCAL MODEL
# =========================================================

def get_model():

    global _tokenizer
    global _model

    if _tokenizer is None or _model is None:

        print("=" * 70)
        print("Loading LOCALIS AI model...")
        print("Model:", MODEL_NAME)
        print("=" * 70)

        _tokenizer = AutoTokenizer.from_pretrained(
            MODEL_NAME
        )

        _model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            torch_dtype="auto"
        )

        _model.eval()

        if not torch.cuda.is_available():

            try:
                torch.set_num_threads(
                    max(
                        1,
                        min(
                            8,
                            torch.get_num_threads()
                        )
                    )
                )
            except Exception:
                pass

        print("LOCALIS AI model loaded.")
        print("LOCALIS AI is ready.")
        print("=" * 70)

    return _tokenizer, _model


# =========================================================
# TEXT NORMALIZATION
# =========================================================

def normalize_text(text: str) -> str:

    if not text:
        return ""

    text = text.replace("\u00a0", " ")
    text = text.replace("\u200b", "")
    text = text.replace("\ufeff", "")

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def normalize_line(text: str) -> str:

    if not text:
        return ""

    text = text.replace("\u00a0", " ")
    text = text.replace("\u200b", "")
    text = text.replace("\ufeff", "")

    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    return text.strip()


# =========================================================
# REMOVE LOCALIS RETRIEVAL HEADERS
# =========================================================

def remove_context_headers(text: str) -> str:

    if not text:
        return ""

    lines = text.splitlines()

    cleaned_lines = []

    for line in lines:

        line = normalize_line(line)

        if not line:
            continue

        # Remove retrieval metadata.
        #
        # Examples:
        # [PAGE 1 · CHUNK 2]
        # [PAGE None · CHUNK 1]
        # [PAGE ? · CHUNK 3]
        #
        if re.fullmatch(
            r"\[?\s*PAGE\s+[^]]+?\s*[·•\-]\s*CHUNK\s+\d+\s*\]?",
            line,
            flags=re.IGNORECASE
        ):
            continue

        # Remove standalone page/chunk metadata
        if re.fullmatch(
            r"PAGE\s+.*CHUNK\s+\d+",
            line,
            flags=re.IGNORECASE
        ):
            continue

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


# =========================================================
# CLEAN ANSWER
# =========================================================

def clean_answer(answer: str) -> str:

    if not answer:
        return ""

    answer = answer.strip()

    answer = re.sub(
        r"<think>.*?</think>",
        "",
        answer,
        flags=re.DOTALL
    )

    answer = re.sub(
        r"^(answer|final answer|response)\s*:\s*",
        "",
        answer,
        flags=re.IGNORECASE
    )

    answer = re.sub(
        r"\s+",
        " ",
        answer
    )

    return answer.strip()


# =========================================================
# BUILD EVIDENCE
# =========================================================

def build_evidence(context: str) -> str:

    if not context:
        return ""

    context = remove_context_headers(
        context
    )

    context = normalize_text(
        context
    )

    if len(context) <= MAX_CONTEXT_CHARS:
        return context

    return (
        context[:MAX_CONTEXT_CHARS]
        + " [Additional evidence omitted]"
    )


# =========================================================
# QUESTION TYPE
# =========================================================

def get_question_type(question: str) -> str:

    question = normalize_text(
        question
    ).lower()

    # -----------------------------------------------------
    # TITLE
    # -----------------------------------------------------

    if re.search(
        r"\bwhat\s+is\s+the\s+title\b",
        question
    ):
        return "title"

    if re.search(
        r"\b(?:title|name)\b.*\b(?:book|document|paper|"
        r"report|article|story|project|file)\b",
        question
    ):
        return "title"

    if re.search(
        r"\bwhat\s+is\s+(?:this|the)\s+"
        r"(?:book|document|paper|report|article|story|project)"
        r"\s+(?:called|titled)\b",
        question
    ):
        return "title"

    # -----------------------------------------------------
    # WHO
    # -----------------------------------------------------

    if re.search(
        r"\bwho\b",
        question
    ):
        return "who"

    # -----------------------------------------------------
    # WHEN
    # -----------------------------------------------------

    if re.search(
        r"\bwhen\b",
        question
    ):
        return "when"

    # -----------------------------------------------------
    # WHERE
    # -----------------------------------------------------

    if re.search(
        r"\bwhere\b",
        question
    ):
        return "where"

    # -----------------------------------------------------
    # NUMBER
    # -----------------------------------------------------

    if re.search(
        r"\bhow\s+many\b",
        question
    ):
        return "number"

    if re.search(
        r"\bhow\s+much\b",
        question
    ):
        return "number"

    # -----------------------------------------------------
    # WHY
    # -----------------------------------------------------

    if re.search(
        r"\bwhy\b",
        question
    ):
        return "why"

    # -----------------------------------------------------
    # HOW
    # -----------------------------------------------------

    if re.search(
        r"\bhow\b",
        question
    ):
        return "how"

    return "general"


# =========================================================
# CLEAN EXTRACTED VALUE
# =========================================================

def clean_extracted_value(
    value: str
) -> str | None:

    if not value:
        return None

    value = normalize_text(
        value
    )

    value = value.strip(
        " ,:;.-\"'“”‘’"
    )

    if not value:
        return None

    # Never allow retrieval headers to become answers.
    if re.fullmatch(
        r"\[?\s*PAGE\s+.*?CHUNK\s+\d+\s*\]?",
        value,
        flags=re.IGNORECASE
    ):
        return None

    # Remove common sentence continuations.
    value = re.split(
        r"\s+(?:this|that|which|and\s+he|and\s+she|"
        r"followed\s+by|as\s+a\s+part\s+of|"
        r"for\s+the|during\s+the)\b",
        value,
        maxsplit=1,
        flags=re.IGNORECASE
    )[0]

    value = value.strip(
        " ,:;.-\"'“”‘’"
    )

    if not value:
        return None

    words = value.split()

    if len(words) > 25:
        value = " ".join(
            words[:25]
        )

    return value


# =========================================================
# IDENTIFIER CHECK
# =========================================================

def looks_like_identifier(
    value: str
) -> bool:

    if not value:
        return False

    value = normalize_text(
        value
    )

    # Pure number / date-like values.
    if re.fullmatch(
        r"[\d\s./_-]+",
        value
    ):
        return True

    # Code-like values.
    if re.fullmatch(
        r"[A-Za-z0-9]+(?:[/_-][A-Za-z0-9]+)+",
        value
    ):
        return True

    # Short mixed alphanumeric code.
    if (
        len(value) <= 25
        and re.search(r"\d", value)
        and re.search(r"[A-Za-z]", value)
        and len(value.split()) <= 3
    ):
        return True

    return False


# =========================================================
# PERSON / ORGANIZATION CHECK
# =========================================================

def looks_like_person_or_organization(
    value: str
) -> bool:

    if not value:
        return False

    value = normalize_text(
        value
    )

    if looks_like_identifier(value):
        return False

    words = value.split()

    if not words:
        return False

    if len(words) >= 2:
        return True

    if len(words) == 1 and value.isalpha():
        return True

    return False


# =========================================================
# TITLE EXTRACTION
# =========================================================

def extract_title_answer(
    question: str,
    text: str
) -> str | None:

    if not text:
        return None

    # IMPORTANT:
    # Keep line structure. Titles are often headings.
    cleaned_text = remove_context_headers(
        text
    )

    lines = []

    for raw_line in cleaned_text.splitlines():

        line = normalize_line(
            raw_line
        )

        if not line:
            continue

        # Never use metadata as title.
        if re.search(
            r"\bPAGE\b.*\bCHUNK\b",
            line,
            flags=re.IGNORECASE
        ):
            continue

        lines.append(line)

    if not lines:
        return None

    # -----------------------------------------------------
    # EXPLICIT TITLE LABELS
    # -----------------------------------------------------

    patterns = [

        r"^\s*(?:document|book|paper|report|article|"
        r"story|project|file)?\s*title\s*[:\-]\s*(.+)$",

        r"^\s*title\s+of\s+(?:the\s+)?"
        r"(?:document|book|paper|report|article|"
        r"story|project)\s*[:\-]?\s*(.+)$",

        r"^\s*(?:document|book|paper|report|article|"
        r"story|project)\s+(?:is\s+)?titled\s+"
        r"[\"“]?(.+?)[\"”]?\s*$",

        r"^\s*(?:document|book|paper|report|article|"
        r"story|project)\s+(?:is\s+)?called\s+"
        r"[\"“]?(.+?)[\"”]?\s*$",

        r"^\s*(?:titled|entitled)\s+"
        r"[\"“](.+?)[\"”]\s*$",
    ]

    for line in lines:

        for pattern in patterns:

            match = re.search(
                pattern,
                line,
                flags=re.IGNORECASE
            )

            if match:

                value = clean_extracted_value(
                    match.group(1)
                )

                if value:
                    return value

    # -----------------------------------------------------
    # QUOTED TITLE
    # -----------------------------------------------------

    for line in lines[:15]:

        match = re.search(
            r"[\"“](.{3,180}?)[\"”]",
            line
        )

        if match:

            value = clean_extracted_value(
                match.group(1)
            )

            if value:
                return value

    # -----------------------------------------------------
    # HEADING-BASED TITLE DETECTION
    # -----------------------------------------------------

    ignored = {
        "author",
        "authors",
        "name",
        "date",
        "address",
        "email",
        "phone",
        "contents",
        "table of contents",
        "introduction",
        "abstract",
        "summary",
        "references",
        "chapter",
    }

    candidates = []

    # Look at the first part of the retrieved evidence.
    for index, line in enumerate(
        lines[:25]
    ):

        candidate = line.strip()

        if not candidate:
            continue

        lower = candidate.lower()

        if lower in ignored:
            continue

        # Metadata labels.
        if lower.startswith(
            (
                "author:",
                "authors:",
                "name:",
                "date:",
                "email:",
                "phone:",
                "address:",
            )
        ):
            continue

        # Skip URLs.
        if re.match(
            r"^(https?://|www\.)",
            candidate,
            flags=re.IGNORECASE
        ):
            continue

        # Skip email.
        if "@" in candidate:
            continue

        # Skip very long paragraph-like text.
        words = candidate.split()

        if len(words) > 18:
            continue

        if len(candidate) > 180:
            continue

        score = 0

        # Very strong title signal:
        # question-like title.
        if candidate.endswith("?"):
            score += 12

        # Uppercase heading.
        letters = re.sub(
            r"[^A-Za-z]",
            "",
            candidate
        )

        if (
            letters
            and letters.upper() == letters
            and len(letters) >= 5
        ):
            score += 10

        # Title Case.
        title_case_count = sum(
            1
            for word in words
            if (
                len(word) > 1
                and word[0].isupper()
                and any(
                    char.isalpha()
                    for char in word
                )
            )
        )

        if (
            len(words) >= 2
            and title_case_count >= max(
                2,
                int(len(words) * 0.6)
            )
        ):
            score += 6

        # Shorter headings are more likely.
        if 2 <= len(words) <= 12:
            score += 4

        # Titles often appear near the beginning.
        score += max(
            0,
            8 - index
        )

        # Paragraph-like lines get penalized.
        if len(words) > 12:
            score -= 5

        candidates.append(
            (
                score,
                index,
                candidate
            )
        )

    if candidates:

        candidates.sort(
            key=lambda item: (
                -item[0],
                item[1]
            )
        )

        best = candidates[0][2]

        best = clean_extracted_value(
            best
        )

        if best:
            return best

    return None


# =========================================================
# WHO EXTRACTION
# =========================================================

def extract_who_answer(
    question: str,
    text: str
) -> str | None:

    question_normalized = normalize_text(
        question
    ).lower()

    text = remove_context_headers(
        text
    )

    # -----------------------------------------------------
    # ISSUER / PROVIDER / CREATOR RELATIONSHIPS
    # -----------------------------------------------------

    issuer_patterns = [

        r"\bissued\s+by\s+"
        r"(.{2,150}?)(?=[.;]|$)",

        r"\bissued\s+from\s+"
        r"(.{2,150}?)(?=[.;]|$)",

        r"\bissuing\s+authority\s*[:\-]?\s*"
        r"(.{2,150}?)(?=[.;]|$)",

        r"\bissuing\s+organization\s*[:\-]?\s*"
        r"(.{2,150}?)(?=[.;]|$)",

        r"\bissuing\s+institution\s*[:\-]?\s*"
        r"(.{2,150}?)(?=[.;]|$)",

        r"\bissuer\s*[:\-]\s*"
        r"(.{2,150}?)(?=[.;]|$)",

        r"\bcertifying\s+authority\s*[:\-]?\s*"
        r"(.{2,150}?)(?=[.;]|$)",

        r"\bcertified\s+by\s+"
        r"(.{2,150}?)(?=[.;]|$)",

        r"\bprovided\s+by\s+"
        r"(.{2,150}?)(?=[.;]|$)",

        r"\bcreated\s+by\s+"
        r"(.{2,150}?)(?=[.;]|$)",

        r"\bauthored\s+by\s+"
        r"(.{2,150}?)(?=[.;]|$)",

        r"\bwritten\s+by\s+"
        r"(.{2,150}?)(?=[.;]|$)",

        r"\bprepared\s+by\s+"
        r"(.{2,150}?)(?=[.;]|$)",

        r"\bsubmitted\s+by\s+"
        r"(.{2,150}?)(?=[.;]|$)",

        r"\bpresented\s+by\s+"
        r"(.{2,150}?)(?=[.;]|$)",

        r"\bawarded\s+to\s+"
        r"(.{2,150}?)(?=[.;]|$)",

        r"\bgranted\s+to\s+"
        r"(.{2,150}?)(?=[.;]|$)",

        r"\brecipient\s*[:\-]\s*"
        r"(.{2,150}?)(?=[.;]|$)",

        r"\brecipient\s+is\s+"
        r"(.{2,150}?)(?=[.;]|$)",
    ]

    for pattern in issuer_patterns:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        if match:

            value = clean_extracted_value(
                match.group(1)
            )

            if (
                value
                and looks_like_person_or_organization(
                    value
                )
            ):
                return value

    # -----------------------------------------------------
    # FIELD-STYLE AUTHOR / CREATOR
    # -----------------------------------------------------

    field_patterns = [

        r"^\s*author\s*[:\-]\s*(.+)$",

        r"^\s*authors\s*[:\-]\s*(.+)$",

        r"^\s*creator\s*[:\-]\s*(.+)$",

        r"^\s*created\s+by\s*[:\-]\s*(.+)$",

        r"^\s*prepared\s+by\s*[:\-]\s*(.+)$",

        r"^\s*submitted\s+by\s*[:\-]\s*(.+)$",

        r"^\s*presented\s+by\s*[:\-]\s*(.+)$",

        r"^\s*issuer\s*[:\-]\s*(.+)$",
    ]

    for line in text.splitlines():

        line = normalize_line(
            line
        )

        if not line:
            continue

        for pattern in field_patterns:

            match = re.search(
                pattern,
                line,
                flags=re.IGNORECASE
            )

            if match:

                value = clean_extracted_value(
                    match.group(1)
                )

                if (
                    value
                    and looks_like_person_or_organization(
                        value
                    )
                ):
                    return value

    # -----------------------------------------------------
    # GENERIC NAME NEAR AUTHOR LABEL
    #
    # Example:
    #
    # Author
    # Mohammad Laeeque Anwar
    #
    # This does not depend on a particular document type.
    # -----------------------------------------------------

    lines = text.splitlines()

    for index, line in enumerate(lines):

        line = normalize_line(
            line
        )

        if not line:
            continue

        if re.fullmatch(
            r"(author|authors|creator|writer)",
            line,
            flags=re.IGNORECASE
        ):

            for next_line in lines[
                index + 1:index + 3
            ]:

                candidate = clean_extracted_value(
                    next_line
                )

                if (
                    candidate
                    and looks_like_person_or_organization(
                        candidate
                    )
                ):
                    return candidate

    return None


# =========================================================
# WHEN EXTRACTION
# =========================================================

def extract_when_answer(
    question: str,
    text: str
) -> str | None:

    text = remove_context_headers(
        text
    )

    patterns = [

        r"\bdate\s*[:\-]\s*"
        r"([0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4})",

        r"\bissued\s+on\s+"
        r"([0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4})",

        r"\bdated\s+"
        r"([0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4})",

        r"\bpublished\s+on\s+"
        r"([0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4})",

        r"\bpublished\s+in\s+"
        r"([0-9]{4})",

        r"\b([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4})\b",

        r"\b([0-9]{1,2}\s+"
        r"(?:January|February|March|April|May|June|July|"
        r"August|September|October|November|December)"
        r"\s+[0-9]{4})\b",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        if match:

            value = clean_extracted_value(
                match.group(1)
            )

            if value:
                return value

    return None


# =========================================================
# WHERE EXTRACTION
# =========================================================

def extract_where_answer(
    question: str,
    text: str
) -> str | None:

    text = remove_context_headers(
        text
    )

    patterns = [

        r"\blocation\s*[:\-]\s*"
        r"(.{2,150}?)(?=[.;]|$)",

        r"\bvenue\s*[:\-]\s*"
        r"(.{2,150}?)(?=[.;]|$)",

        r"\baddress\s*[:\-]\s*"
        r"(.{2,150}?)(?=[.;]|$)",

        r"\bplace\s*[:\-]\s*"
        r"(.{2,150}?)(?=[.;]|$)",

        r"\blocated\s+at\s+"
        r"(.{2,150}?)(?=[.;]|$)",

        r"\blocated\s+in\s+"
        r"(.{2,150}?)(?=[.;]|$)",

        r"\bbased\s+at\s+"
        r"(.{2,150}?)(?=[.;]|$)",

        r"\bbased\s+in\s+"
        r"(.{2,150}?)(?=[.;]|$)",

        r"\bheld\s+at\s+"
        r"(.{2,150}?)(?=[.;]|$)",

        r"\bheld\s+in\s+"
        r"(.{2,150}?)(?=[.;]|$)",

        r"\bconducted\s+at\s+"
        r"(.{2,150}?)(?=[.;]|$)",

        r"\bconducted\s+in\s+"
        r"(.{2,150}?)(?=[.;]|$)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        if match:

            value = clean_extracted_value(
                match.group(1)
            )

            if value:
                return value

    return None


# =========================================================
# STRUCTURED EXTRACTION
# =========================================================

def extract_structured_answer(
    question: str,
    context: str
) -> str | None:

    question_type = get_question_type(
        question
    )

    if not context:
        return None

    if question_type == "title":

        return extract_title_answer(
            question,
            context
        )

    if question_type == "who":

        return extract_who_answer(
            question,
            context
        )

    if question_type == "when":

        return extract_when_answer(
            question,
            context
        )

    if question_type == "where":

        return extract_where_answer(
            question,
            context
        )

    return None


# =========================================================
# GENERATE ANSWER
# =========================================================

def generate_answer(
    question: str,
    context: str,
    max_new_tokens: int = MAX_NEW_TOKENS
) -> str:

    question = normalize_text(
        question
    )

    if not question:

        return (
            "Please enter a question."
        )

    if not context.strip():

        return (
            "I could not find that information "
            "in the document."
        )

    # -----------------------------------------------------
    # CLEAN RETRIEVED CONTEXT FIRST
    # -----------------------------------------------------

    evidence = build_evidence(
        context
    )

    if not evidence:

        return (
            "I could not find that information "
            "in the document."
        )

    # =====================================================
    # FAST STRUCTURED EXTRACTION
    # =====================================================

    structured_answer = extract_structured_answer(
        question,
        evidence
    )

    if structured_answer:

        print(
            "Structured document extraction:",
            structured_answer
        )

        return structured_answer

    # =====================================================
    # LOCAL QWEN FALLBACK
    # =====================================================

    tokenizer, model = get_model()

    # =====================================================
    # SYSTEM PROMPT
    # =====================================================

    system_prompt = """
You are LOCALIS, a private local document
intelligence assistant.

Use ONLY the supplied DOCUMENT EVIDENCE.

Rules:

1. Do not use outside knowledge.
2. Do not guess.
3. Do not invent facts.
4. Answer the exact user question.
5. Preserve names exactly as they appear.
6. Preserve dates exactly as they appear.
7. Preserve important numbers and codes exactly.
8. For WHO questions, identify the relevant
   person or organization from the evidence.
9. For WHEN questions, identify the relevant
   date or time from the evidence.
10. For WHERE questions, identify the relevant
    location from the evidence.
11. If the evidence does not contain the answer,
    say:
    I could not find that information in the document.
12. Do not use information outside the evidence.
13. Do not explain your reasoning.
14. Do not repeat the question.
15. Return only the final answer.
""".strip()

    # =====================================================
    # USER PROMPT
    # =====================================================

    user_prompt = f"""
DOCUMENT EVIDENCE:

{evidence}

QUESTION:

{question}

Answer the question directly using only the
document evidence.

If the requested information is not present,
say:

I could not find that information in the document.
""".strip()

    # =====================================================
    # CHAT TEMPLATE
    # =====================================================

    text = tokenizer.apply_chat_template(
        [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False
    )

    # =====================================================
    # TOKENIZATION
    # =====================================================

    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=MAX_INPUT_TOKENS
    )

    # =====================================================
    # DEVICE
    # =====================================================

    inputs = {
        key: value.to(
            model.device
        )
        for key, value in inputs.items()
    }

    # =====================================================
    # INFERENCE
    # =====================================================

    with torch.inference_mode():

        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            use_cache=True,
            repetition_penalty=1.02,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id
        )

    # =====================================================
    # REMOVE PROMPT TOKENS
    # =====================================================

    input_length = (
        inputs["input_ids"].shape[1]
    )

    generated_tokens = (
        outputs[
            0,
            input_length:
        ]
    )

    # =====================================================
    # DECODE
    # =====================================================

    answer = tokenizer.decode(
        generated_tokens,
        skip_special_tokens=True
    )

    answer = clean_answer(
        answer
    )

    # =====================================================
    # VALIDATION
    # =====================================================

    if not answer:

        return (
            "I could not find enough information "
            "in the document to answer that."
        )

    return answer