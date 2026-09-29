import json
import hashlib

from pathlib import Path
from uuid import uuid4


# =========================================================
# STORAGE
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

STORAGE_DIR = (
    PROJECT_ROOT
    / "backend"
    / "data"
    / "documents"
)

STORAGE_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# =========================================================
# PDF HASH
# =========================================================

def calculate_document_hash(
    pdf_bytes: bytes
) -> str:

    return hashlib.sha256(
        pdf_bytes
    ).hexdigest()


# =========================================================
# FIND EXACT UPLOAD DUPLICATE
# =========================================================

def find_duplicate_document(
    pdf_bytes: bytes
) -> dict | None:

    document_hash = (
        calculate_document_hash(
            pdf_bytes
        )
    )

    for file_path in STORAGE_DIR.glob(
        "*.json"
    ):

        try:

            with open(
                file_path,
                "r",
                encoding="utf-8"
            ) as file:

                document = json.load(file)

            if (
                document.get(
                    "document_hash"
                )
                == document_hash
            ):

                return document

        except Exception as error:

            print(
                f"Could not check {file_path.name}: {error}"
            )

    return None


# =========================================================
# LOAD DOCUMENT
# =========================================================

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


# =========================================================
# SAVE DOCUMENT
# =========================================================

def save_document(
    filename: str,
    extracted_text: str,
    pages: list,
    chunks: list,
    pdf_bytes: bytes
) -> dict:

    document_id = str(
        uuid4()
    )

    document_hash = (
        calculate_document_hash(
            pdf_bytes
        )
    )

    document = {

        "document_id":
            document_id,

        "filename":
            filename,

        "document_hash":
            document_hash,

        "text":
            extracted_text,

        "pages":
            pages,

        "chunks":
            chunks
    }

    file_path = (
        STORAGE_DIR
        / f"{document_id}.json"
    )

    with open(
        file_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            document,
            file,
            ensure_ascii=False,
            indent=2
        )

    return {

        "document_id":
            document_id,

        "filename":
            filename,

        "storage_path":
            str(file_path),

        "duplicate":
            False
    }