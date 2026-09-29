from pathlib import Path
import json
import re
from difflib import SequenceMatcher


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


# =========================================================
# LOAD COMPLETE DOCUMENT
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
# NORMALIZE TEXT FOR DUPLICATE CHECKING
# =========================================================

def normalize_for_duplicate(
    text: str
) -> str:

    if not text:
        return ""

    text = text.lower()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    text = re.sub(
        r"[^a-z0-9 ]",
        "",
        text
    )

    return text.strip()


# =========================================================
# DOCUMENT METADATA
# =========================================================

def read_document_metadata(
    file_path: Path
) -> dict | None:

    try:

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        return {

            "document_id":
                data.get(
                    "document_id"
                ),

            "filename":
                data.get(
                    "filename",
                    file_path.stem
                ),

            "pages":
                len(
                    data.get(
                        "pages",
                        []
                    )
                ),

            "chunks":
                len(
                    data.get(
                        "chunks",
                        []
                    )
                )
        }

    except Exception as error:

        print(
            f"Could not read "
            f"{file_path.name}: {error}"
        )

        return None


# =========================================================
# LIST DOCUMENTS
# =========================================================

def list_documents() -> list[dict]:

    documents = []

    if not STORAGE_DIR.exists():

        return documents

    for file_path in STORAGE_DIR.glob(
        "*.json"
    ):

        metadata = (
            read_document_metadata(
                file_path
            )
        )

        if metadata:

            documents.append(
                metadata
            )

    documents.sort(
        key=lambda document:
        document["filename"].lower()
    )

    return documents


# =========================================================
# DELETE DOCUMENT
# =========================================================

def delete_document(
    document_id: str
) -> bool:

    file_path = (
        STORAGE_DIR
        / f"{document_id}.json"
    )

    if not file_path.exists():

        return False

    file_path.unlink()

    print(
        f"LOCALIS: Deleted document "
        f"{document_id}"
    )

    return True


# =========================================================
# FIND DUPLICATES
# =========================================================

def find_duplicate_documents() -> list[dict]:

    documents = []

    if not STORAGE_DIR.exists():

        return []


    # -----------------------------------------------------
    # Load documents
    # -----------------------------------------------------

    for file_path in STORAGE_DIR.glob(
        "*.json"
    ):

        try:

            with open(
                file_path,
                "r",
                encoding="utf-8"
            ) as file:

                data = json.load(
                    file
                )


            document_id = data.get(
                "document_id"
            )

            filename = data.get(
                "filename",
                file_path.stem
            )

            text = data.get(
                "text",
                ""
            )


            normalized_text = (
                normalize_for_duplicate(
                    text
                )
            )


            if not normalized_text:

                continue


            documents.append({

                "document_id":
                    document_id,

                "filename":
                    filename,

                "text":
                    normalized_text,

                "pages":
                    len(
                        data.get(
                            "pages",
                            []
                        )
                    ),

                "chunks":
                    len(
                        data.get(
                            "chunks",
                            []
                        )
                    )
            })


        except Exception as error:

            print(
                f"Could not inspect "
                f"{file_path.name}: {error}"
            )


    duplicates = []

    kept_documents = []


    # =====================================================
    # COMPARE DOCUMENTS
    # =====================================================

    for current in documents:

        is_duplicate = False

        for kept in kept_documents:

            # ---------------------------------------------
            # Exact normalized text
            # ---------------------------------------------

            if (
                current["text"]
                == kept["text"]
            ):

                is_duplicate = True

            else:

                # -----------------------------------------
                # Similarity comparison
                # -----------------------------------------

                # Avoid expensive comparison for
                # completely different document sizes.

                current_length = len(
                    current["text"]
                )

                kept_length = len(
                    kept["text"]
                )

                if (
                    current_length > 100
                    and kept_length > 100
                ):

                    size_ratio = (
                        min(
                            current_length,
                            kept_length
                        )
                        /
                        max(
                            current_length,
                            kept_length
                        )
                    )


                    if size_ratio >= 0.90:

                        similarity = (
                            SequenceMatcher(
                                None,
                                current["text"],
                                kept["text"]
                            ).ratio()
                        )

                        if similarity >= 0.95:

                            is_duplicate = True


            if is_duplicate:

                break


        # =================================================
        # STORE RESULT
        # =================================================

        if is_duplicate:

            duplicates.append({

                "document_id":
                    current[
                        "document_id"
                    ],

                "filename":
                    current[
                        "filename"
                    ],

                "duplicate_of":
                    kept[
                        "document_id"
                    ]
            })

        else:

            kept_documents.append(
                current
            )


    return duplicates


# =========================================================
# CLEAN DUPLICATES
# =========================================================

def clean_duplicate_documents() -> list[dict]:

    duplicates = (
        find_duplicate_documents()
    )

    deleted = []


    for duplicate in duplicates:

        document_id = (
            duplicate[
                "document_id"
            ]
        )


        if delete_document(
            document_id
        ):

            deleted.append(
                duplicate
            )


    return deleted

from pathlib import Path
import json
import re
from difflib import SequenceMatcher


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


# =========================================================
# LOAD COMPLETE DOCUMENT
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
# NORMALIZE TEXT FOR DUPLICATE CHECKING
# =========================================================

def normalize_for_duplicate(
    text: str
) -> str:

    if not text:
        return ""

    text = text.lower()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    text = re.sub(
        r"[^a-z0-9 ]",
        "",
        text
    )

    return text.strip()


# =========================================================
# DOCUMENT METADATA
# =========================================================

def read_document_metadata(
    file_path: Path
) -> dict | None:

    try:

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        return {

            "document_id":
                data.get(
                    "document_id"
                ),

            "filename":
                data.get(
                    "filename",
                    file_path.stem
                ),

            "pages":
                len(
                    data.get(
                        "pages",
                        []
                    )
                ),

            "chunks":
                len(
                    data.get(
                        "chunks",
                        []
                    )
                )
        }

    except Exception as error:

        print(
            f"Could not read "
            f"{file_path.name}: {error}"
        )

        return None


# =========================================================
# LIST DOCUMENTS
# =========================================================

def list_documents() -> list[dict]:

    documents = []

    if not STORAGE_DIR.exists():

        return documents

    for file_path in STORAGE_DIR.glob(
        "*.json"
    ):

        metadata = (
            read_document_metadata(
                file_path
            )
        )

        if metadata:

            documents.append(
                metadata
            )

    documents.sort(
        key=lambda document:
        document["filename"].lower()
    )

    return documents


# =========================================================
# DELETE DOCUMENT
# =========================================================

def delete_document(
    document_id: str
) -> bool:

    file_path = (
        STORAGE_DIR
        / f"{document_id}.json"
    )

    if not file_path.exists():

        return False

    file_path.unlink()

    print(
        f"LOCALIS: Deleted document "
        f"{document_id}"
    )

    return True


# =========================================================
# FIND DUPLICATES
# =========================================================

def find_duplicate_documents() -> list[dict]:

    documents = []

    if not STORAGE_DIR.exists():

        return []


    # -----------------------------------------------------
    # Load documents
    # -----------------------------------------------------

    for file_path in STORAGE_DIR.glob(
        "*.json"
    ):

        try:

            with open(
                file_path,
                "r",
                encoding="utf-8"
            ) as file:

                data = json.load(
                    file
                )


            document_id = data.get(
                "document_id"
            )

            filename = data.get(
                "filename",
                file_path.stem
            )

            text = data.get(
                "text",
                ""
            )


            normalized_text = (
                normalize_for_duplicate(
                    text
                )
            )


            if not normalized_text:

                continue


            documents.append({

                "document_id":
                    document_id,

                "filename":
                    filename,

                "text":
                    normalized_text,

                "pages":
                    len(
                        data.get(
                            "pages",
                            []
                        )
                    ),

                "chunks":
                    len(
                        data.get(
                            "chunks",
                            []
                        )
                    )
            })


        except Exception as error:

            print(
                f"Could not inspect "
                f"{file_path.name}: {error}"
            )


    duplicates = []

    kept_documents = []


    # =====================================================
    # COMPARE DOCUMENTS
    # =====================================================

    for current in documents:

        is_duplicate = False

        for kept in kept_documents:

            # ---------------------------------------------
            # Exact normalized text
            # ---------------------------------------------

            if (
                current["text"]
                == kept["text"]
            ):

                is_duplicate = True

            else:

                # -----------------------------------------
                # Similarity comparison
                # -----------------------------------------

                # Avoid expensive comparison for
                # completely different document sizes.

                current_length = len(
                    current["text"]
                )

                kept_length = len(
                    kept["text"]
                )

                if (
                    current_length > 100
                    and kept_length > 100
                ):

                    size_ratio = (
                        min(
                            current_length,
                            kept_length
                        )
                        /
                        max(
                            current_length,
                            kept_length
                        )
                    )


                    if size_ratio >= 0.90:

                        similarity = (
                            SequenceMatcher(
                                None,
                                current["text"],
                                kept["text"]
                            ).ratio()
                        )

                        if similarity >= 0.95:

                            is_duplicate = True


            if is_duplicate:

                break


        # =================================================
        # STORE RESULT
        # =================================================

        if is_duplicate:

            duplicates.append({

                "document_id":
                    current[
                        "document_id"
                    ],

                "filename":
                    current[
                        "filename"
                    ],

                "duplicate_of":
                    kept[
                        "document_id"
                    ]
            })

        else:

            kept_documents.append(
                current
            )


    return duplicates


# =========================================================
# CLEAN DUPLICATES
# =========================================================

def clean_duplicate_documents() -> list[dict]:

    duplicates = (
        find_duplicate_documents()
    )

    deleted = []


    for duplicate in duplicates:

        document_id = (
            duplicate[
                "document_id"
            ]
        )


        if delete_document(
            document_id
        ):

            deleted.append(
                duplicate
            )


    return deleted