import re

import pymupdf

from backend.app.services.ocr_service import (
    ocr_pdf_page
)


# =========================================================
# TEXT CLEANING
# =========================================================

def clean_text(
    text: str
) -> str:

    if not text:
        return ""

    text = text.replace(
        "\u00a0",
        " "
    )

    text = text.replace(
        "\u200b",
        ""
    )

    text = text.replace(
        "\ufeff",
        ""
    )

    text = text.replace(
        "\r\n",
        "\n"
    )

    text = text.replace(
        "\r",
        "\n"
    )

    # Remove spaces before punctuation
    text = re.sub(
        r"\s+([,.!?;:%])",
        r"\1",
        text
    )

    # Add missing space after punctuation
    text = re.sub(
        r"([,.!?;:%])([A-Za-z])",
        r"\1 \2",
        text
    )

    # Normalize spaces
    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    # Normalize excessive line breaks
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


# =========================================================
# STANDARD PDF TEXT
# =========================================================

def extract_standard_text(
    page
) -> str:

    text = page.get_text(
        "text",
        sort=True
    )

    return clean_text(
        text
    )


# =========================================================
# WORD EXTRACTION
# =========================================================

def extract_words_text(
    page
) -> str:

    words = page.get_text(
        "words",
        sort=True
    )

    if not words:
        return ""

    lines = {}

    for word in words:

        if len(word) < 5:
            continue

        (
            x0,
            y0,
            x1,
            y1,
            text,
            block_no,
            line_no,
            word_no
        ) = word[:8]

        if not text:
            continue

        key = (
            block_no,
            line_no
        )

        if key not in lines:

            lines[key] = []

        lines[key].append({
            "x0": x0,
            "x1": x1,
            "text": text
        })


    output_lines = []


    for key in sorted(
        lines.keys(),
        key=lambda item: (
            item[0],
            item[1]
        )
    ):

        line_words = lines[key]

        line_words.sort(
            key=lambda item:
            item["x0"]
        )

        if not line_words:
            continue


        parts = []

        for item in line_words:

            value = item[
                "text"
            ].strip()

            if value:

                parts.append(
                    value
                )


        line = " ".join(
            parts
        )

        output_lines.append(
            line
        )


    return "\n".join(
        output_lines
    )


# =========================================================
# DETECT BROKEN EXTRACTION
# =========================================================

def extraction_looks_broken(
    text: str
) -> bool:

    if not text:

        return True


    cleaned = text.strip()


    if len(cleaned) < 20:

        return True


    # -----------------------------------------------------
    # Detect very long words.
    #
    # Example:
    #
    # WHATHAPPENSWHENGUILTEATSAWAYATAPERSON
    # -----------------------------------------------------

    long_words = re.findall(
        r"\b[A-Za-z]{25,}\b",
        cleaned
    )

    if len(long_words) >= 1:

        return True


    # -----------------------------------------------------
    # Detect low whitespace ratio.
    # -----------------------------------------------------

    letters = re.sub(
        r"[^A-Za-z]",
        "",
        cleaned
    )

    if len(letters) > 100:

        spaces = cleaned.count(
            " "
        )

        space_ratio = (
            spaces
            / len(letters)
        )

        if space_ratio < 0.035:

            return True


    # -----------------------------------------------------
    # Detect repeated concatenated uppercase text.
    # -----------------------------------------------------

    uppercase_words = re.findall(
        r"\b[A-Z]{20,}\b",
        cleaned
    )

    if uppercase_words:

        return True


    return False


# =========================================================
# OCR
# =========================================================

def run_ocr(
    page
) -> str:

    try:

        print(
            "Running OCR on page..."
        )

        ocr_text = ocr_pdf_page(
            page
        )

        ocr_text = clean_text(
            ocr_text
        )

        return ocr_text


    except Exception as error:

        print(
            f"OCR failed: {error}"
        )

        return ""


# =========================================================
# CHOOSE BEST EXTRACTION
# =========================================================

def choose_page_text(
    page,
    native_text: str
) -> str:

    native_text = clean_text(
        native_text
    )


    # -----------------------------------------------------
    # If native extraction looks healthy,
    # use it directly.
    # -----------------------------------------------------

    if (
        native_text
        and not extraction_looks_broken(
            native_text
        )
    ):

        return native_text


    # -----------------------------------------------------
    # Native extraction looks suspicious.
    #
    # Use OCR instead.
    # -----------------------------------------------------

    print(
        "Native PDF extraction looks broken."
    )

    ocr_text = run_ocr(
        page
    )


    # -----------------------------------------------------
    # If OCR produced usable text,
    # prefer OCR.
    # -----------------------------------------------------

    if ocr_text:

        if not extraction_looks_broken(
            ocr_text
        ):

            return ocr_text


        # Even if OCR has some imperfections,
        # prefer it over severely broken native text.
        if len(ocr_text) >= 20:

            return ocr_text


    # -----------------------------------------------------
    # OCR failed.
    # Fall back to native extraction.
    # -----------------------------------------------------

    return native_text


# =========================================================
# MAIN PDF EXTRACTION
# =========================================================

def extract_pdf_text(
    pdf_bytes: bytes
) -> dict:

    document = pymupdf.open(
        stream=pdf_bytes,
        filetype="pdf"
    )

    pages = []

    full_text = []


    try:

        for page_number, page in enumerate(
            document,
            start=1
        ):

            print(
                f"Processing page {page_number}..."
            )


            # ---------------------------------------------
            # Native standard extraction
            # ---------------------------------------------

            standard_text = (
                extract_standard_text(
                    page
                )
            )


            # ---------------------------------------------
            # Word-based extraction
            # ---------------------------------------------

            word_text = clean_text(
                extract_words_text(
                    page
                )
            )


            # ---------------------------------------------
            # Choose native extraction
            # ---------------------------------------------

            if (
                len(word_text)
                > len(standard_text)
            ):

                native_text = word_text

            else:

                native_text = standard_text


            # ---------------------------------------------
            # Final extraction decision
            # ---------------------------------------------

            page_text = choose_page_text(
                page,
                native_text
            )


            page_text = clean_text(
                page_text
            )


            pages.append({

                "page":
                    page_number,

                "text":
                    page_text
            })


            if page_text:

                full_text.append(
                    page_text
                )


    finally:

        document.close()


    final_text = "\n\n".join(
        full_text
    ).strip()


    return {

        "page_count":
            len(pages),

        "text":
            final_text,

        "pages":
            pages
    }