import re


def clean_chunk_text(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\u00a0", " ")
    text = text.replace("\u200b", "")
    text = text.replace("\ufeff", "")

    # Normalize line endings
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Remove excessive spaces but preserve useful line structure
    text = re.sub(r"[ \t]+", " ", text)

    # Remove excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def split_text_into_units(text: str) -> list[str]:
    """
    Split document text into meaningful units.

    Works with:
    - normal paragraphs
    - certificate text
    - forms
    - resumes
    - notices
    - books
    - OCR text
    """

    text = clean_chunk_text(text)

    if not text:
        return []

    units = []

    # First preserve meaningful lines.
    lines = [
        line.strip()
        for line in text.split("\n")
        if line.strip()
    ]

    for line in lines:

        # If the line is short, keep it as one unit.
        if len(line) <= 350:
            units.append(line)
            continue

        # Long lines are further divided into sentences.
        sentences = re.split(
            r"(?<=[.!?])\s+(?=[A-Z0-9])",
            line
        )

        for sentence in sentences:
            sentence = sentence.strip()

            if sentence:
                units.append(sentence)

    return units


def split_long_unit(unit: str, max_words: int) -> list[str]:
    """
    Split an unusually long unit by words.
    """

    words = unit.split()

    if len(words) <= max_words:
        return [unit]

    pieces = []

    for start in range(0, len(words), max_words):
        piece = " ".join(
            words[start:start + max_words]
        ).strip()

        if piece:
            pieces.append(piece)

    return pieces


def create_chunks(
    pages: list,
    chunk_size: int = 450,
    overlap: int = 80
) -> list:
    """
    Create smaller, page-aware chunks.

    Smaller chunks improve retrieval because the model
    receives the specific part of the document that
    answers the question instead of an entire page.
    """

    chunks = []

    for page_data in pages:

        page_number = page_data.get("page", 1)

        page_text = page_data.get("text", "")
        page_text = clean_chunk_text(page_text)

        if not page_text:
            continue

        units = split_text_into_units(page_text)

        if not units:
            continue

        # Break extremely long units into manageable pieces.
        normalized_units = []

        for unit in units:
            normalized_units.extend(
                split_long_unit(
                    unit,
                    max_words=80
                )
            )

        current_units = []
        current_length = 0

        for unit in normalized_units:

            unit_length = len(unit)

            extra_length = (
                unit_length
                if not current_units
                else unit_length + 1
            )

            # Create a chunk when it reaches the target size.
            if (
                current_units
                and current_length + extra_length > chunk_size
            ):

                chunk_text = " ".join(
                    current_units
                ).strip()

                if chunk_text:
                    chunks.append({
                        "chunk_id": len(chunks) + 1,
                        "page": page_number,
                        "text": chunk_text
                    })

                # Keep a small overlap.
                overlap_units = []
                overlap_length = 0

                for previous in reversed(current_units):

                    previous_length = len(previous)

                    if (
                        overlap_length
                        + previous_length
                        + 1
                        > overlap
                    ):
                        break

                    overlap_units.insert(
                        0,
                        previous
                    )

                    overlap_length += (
                        previous_length + 1
                    )

                current_units = overlap_units

                current_length = sum(
                    len(item)
                    for item in current_units
                )

                if current_units:
                    current_length += (
                        len(current_units) - 1
                    )

            current_units.append(unit)
            current_length += extra_length

        # Save final chunk.
        if current_units:

            chunk_text = " ".join(
                current_units
            ).strip()

            if chunk_text:
                chunks.append({
                    "chunk_id": len(chunks) + 1,
                    "page": page_number,
                    "text": chunk_text
                })

    return chunks