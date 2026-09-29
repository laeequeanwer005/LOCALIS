from fastapi import (
    FastAPI,
    UploadFile,
    HTTPException,
)

from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import json
import time

from pathlib import Path


# =========================================================
# LOCALIS SERVICES
# =========================================================

from backend.app.services.pdf_service import (
    extract_pdf_text,
)

from backend.app.services.document_service import (
    save_document,
    find_duplicate_document,
)

from backend.app.services.chunk_service import (
    create_chunks,
)

from backend.app.services.embedding_service import (
    create_embeddings,
)

from backend.app.services.search_service import (
    search_document,
)

from backend.app.services.llm_service import (
    generate_answer,
)


# =========================================================
# STORAGE
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

STORAGE_DIR = (
    PROJECT_ROOT
    / "backend"
    / "data"
    / "documents"
)

STORAGE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# =========================================================
# APP
# =========================================================

app = FastAPI(
    title="LOCALIS API",
    description="Private local AI document assistant",
    version="1.0.0",
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# REQUEST MODELS
# =========================================================

class SearchRequest(BaseModel):

    document_id: str

    query: str

    top_k: int = 5


class AskRequest(BaseModel):

    document_id: str

    question: str

    top_k: int = 6


# =========================================================
# ROOT
# =========================================================

@app.get("/")
async def root():

    return {
        "message": "LOCALIS API is running",
        "status": "online",
    }


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
async def health():

    return {
        "status": "healthy",
        "service": "LOCALIS",
    }


# =========================================================
# LIST DOCUMENTS
# =========================================================

@app.get("/documents")
async def list_documents():

    documents = []

    for file_path in STORAGE_DIR.glob("*.json"):

        try:

            with open(
                file_path,
                "r",
                encoding="utf-8",
            ) as file:

                document = json.load(file)

            documents.append(
                {
                    "document_id": document.get(
                        "document_id"
                    ),
                    "filename": document.get(
                        "filename"
                    ),
                    "pages": len(
                        document.get(
                            "pages",
                            [],
                        )
                    ),
                    "chunks": len(
                        document.get(
                            "chunks",
                            [],
                        )
                    ),
                    "document_hash": document.get(
                        "document_hash"
                    ),
                }
            )

        except Exception as error:

            print(
                f"Could not load {file_path.name}: "
                f"{error}"
            )

    documents.sort(
        key=lambda item: item.get(
            "filename",
            "",
        ).lower()
    )

    return {
        "status": "success",
        "documents": documents,
    }


# =========================================================
# DOCUMENT PREVIEW
# =========================================================

@app.get("/documents/{document_id}/preview")
async def preview_document(
    document_id: str,
):

    file_path = (
        STORAGE_DIR
        / f"{document_id}.json"
    )

    if not file_path.exists():

        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    try:

        with open(
            file_path,
            "r",
            encoding="utf-8",
        ) as file:

            document = json.load(file)

        return {
            "status": "success",
            "document": document,
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                "Could not load document preview: "
                f"{error}"
            ),
        )


# =========================================================
# DELETE DOCUMENT
# =========================================================

@app.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
):

    file_path = (
        STORAGE_DIR
        / f"{document_id}.json"
    )

    if not file_path.exists():

        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    try:

        file_path.unlink()

        return {
            "status": "success",
            "document_id": document_id,
            "message": "Document deleted",
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                "Could not delete document: "
                f"{error}"
            ),
        )


# =========================================================
# CLEAN DUPLICATES
# =========================================================

@app.post("/documents/cleanup-duplicates")
async def cleanup_duplicates():

    seen_hashes = {}

    removed_documents = []

    files = list(
        STORAGE_DIR.glob("*.json")
    )

    for file_path in files:

        try:

            with open(
                file_path,
                "r",
                encoding="utf-8",
            ) as file:

                document = json.load(file)

            document_hash = document.get(
                "document_hash"
            )

            if not document_hash:
                continue

            if document_hash not in seen_hashes:

                seen_hashes[
                    document_hash
                ] = file_path

                continue

            original_file = seen_hashes[
                document_hash
            ]

            # Keep the first document.
            file_path.unlink()

            removed_documents.append(
                {
                    "document_id": document.get(
                        "document_id"
                    ),
                    "filename": document.get(
                        "filename"
                    ),
                    "removed_file": file_path.name,
                    "kept_file": original_file.name,
                }
            )

        except Exception as error:

            print(
                f"Could not process duplicate "
                f"{file_path.name}: {error}"
            )

    return {
        "status": "success",
        "removed_count": len(
            removed_documents
        ),
        "removed_documents": removed_documents,
    }


# =========================================================
# DOCUMENT EXTRACTION
# =========================================================

@app.post("/documents/extract")
async def extract_document(
    file: UploadFile,
):

    total_start = time.perf_counter()

    print()
    print("=" * 70)
    print("LOCALIS DOCUMENT PROCESSING")
    print("=" * 70)

    # =====================================================
    # VALIDATE FILE
    # =====================================================

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail="No file provided",
        )

    if not file.filename.lower().endswith(
        ".pdf"
    ):

        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported",
        )

    try:

        # =================================================
        # STEP 1 — READ PDF
        # =================================================

        print(
            "\n[1/5] Reading uploaded PDF..."
        )

        step_start = time.perf_counter()

        pdf_bytes = await file.read()

        read_time = (
            time.perf_counter()
            - step_start
        )

        print(
            f"[1/5] PDF loaded: "
            f"{len(pdf_bytes) / 1024:.2f} KB"
        )

        print(
            f"[1/5] Time: "
            f"{read_time:.3f}s"
        )

        if not pdf_bytes:

            raise ValueError(
                "The uploaded PDF is empty."
            )

        # =================================================
        # DUPLICATE CHECK
        # =================================================

        print(
            "\nChecking for an existing document..."
        )

        duplicate = find_duplicate_document(
            pdf_bytes
        )

        if duplicate:

            duplicate_time = (
                time.perf_counter()
                - total_start
            )

            print(
                "Duplicate document found."
            )

            print(
                f"Total time: "
                f"{duplicate_time:.3f}s"
            )

            return {
                "filename": duplicate.get(
                    "filename",
                    file.filename,
                ),
                "status": "success",
                "document_id": duplicate.get(
                    "document_id"
                ),
                "page_count": len(
                    duplicate.get(
                        "pages",
                        [],
                    )
                ),
                "chunk_count": len(
                    duplicate.get(
                        "chunks",
                        [],
                    )
                ),
                "chunks": duplicate.get(
                    "chunks",
                    [],
                ),
                "pages": duplicate.get(
                    "pages",
                    [],
                ),
                "duplicate": True,
                "processing_time_seconds": round(
                    duplicate_time,
                    3,
                ),
                "processing_steps": {
                    "pdf_read": round(
                        read_time,
                        3,
                    ),
                    "text_extraction": 0.0,
                    "chunking": 0.0,
                    "embeddings": 0.0,
                    "storage": 0.0,
                },
            }

        # =================================================
        # STEP 2 — EXTRACT TEXT
        # =================================================

        print(
            "\n[2/5] Extracting text from PDF..."
        )

        step_start = time.perf_counter()

        result = extract_pdf_text(
            pdf_bytes
        )

        extraction_time = (
            time.perf_counter()
            - step_start
        )

        print(
            f"[2/5] Extraction completed in "
            f"{extraction_time:.3f}s"
        )

        print(
            f"[2/5] Pages: "
            f"{result['page_count']}"
        )

        print(
            f"[2/5] Extracted characters: "
            f"{len(result['text'])}"
        )

        if not result["text"].strip():

            raise ValueError(
                "No text could be extracted "
                "from this PDF."
            )

        # =================================================
        # STEP 3 — CREATE CHUNKS
        # =================================================

        print(
            "\n[3/5] Creating document chunks..."
        )

        step_start = time.perf_counter()

        chunks = create_chunks(
            result["pages"]
        )

        chunk_time = (
            time.perf_counter()
            - step_start
        )

        print(
            f"[3/5] Chunking completed in "
            f"{chunk_time:.3f}s"
        )

        print(
            f"[3/5] Created chunks: "
            f"{len(chunks)}"
        )

        if not chunks:

            raise ValueError(
                "Document text was extracted, "
                "but no chunks could be created."
            )

        # =================================================
        # STEP 4 — CREATE EMBEDDINGS
        # =================================================

        print(
            "\n[4/5] Creating embeddings..."
        )

        step_start = time.perf_counter()

        embeddings = create_embeddings(
            [
                chunk["text"]
                for chunk in chunks
            ]
        )

        embedding_time = (
            time.perf_counter()
            - step_start
        )

        print(
            f"[4/5] Embeddings completed in "
            f"{embedding_time:.3f}s"
        )

        print(
            f"[4/5] Embeddings created: "
            f"{len(embeddings)}"
        )

        for chunk, embedding in zip(
            chunks,
            embeddings,
        ):

            chunk["embedding"] = embedding

        # =================================================
        # STEP 5 — SAVE DOCUMENT
        # =================================================

        print(
            "\n[5/5] Saving document..."
        )

        step_start = time.perf_counter()

        saved_document = save_document(
            filename=file.filename,
            extracted_text=result["text"],
            pages=result["pages"],
            chunks=chunks,
            pdf_bytes=pdf_bytes,
        )

        save_time = (
            time.perf_counter()
            - step_start
        )

        print(
            f"[5/5] Document saved in "
            f"{save_time:.3f}s"
        )

        # =================================================
        # TOTAL
        # =================================================

        total_time = (
            time.perf_counter()
            - total_start
        )

        print()
        print("=" * 70)
        print("DOCUMENT PROCESSING COMPLETE")
        print("=" * 70)

        print(
            f"File: {file.filename}"
        )

        print(
            f"Pages: {result['page_count']}"
        )

        print(
            f"Chunks: {len(chunks)}"
        )

        print(
            f"Extraction: "
            f"{extraction_time:.3f}s"
        )

        print(
            f"Chunking: "
            f"{chunk_time:.3f}s"
        )

        print(
            f"Embeddings: "
            f"{embedding_time:.3f}s"
        )

        print(
            f"Storage: "
            f"{save_time:.3f}s"
        )

        print(
            f"TOTAL: "
            f"{total_time:.3f}s"
        )

        print(
            f"Document ID: "
            f"{saved_document['document_id']}"
        )

        print("=" * 70)
        print()

        # =================================================
        # RESPONSE
        # =================================================

        return {

            "filename":
                file.filename,

            "status":
                "success",

            "document_id":
                saved_document[
                    "document_id"
                ],

            "page_count":
                result[
                    "page_count"
                ],

            "chunk_count":
                len(chunks),

            "chunks":
                chunks,

            "pages":
                result[
                    "pages"
                ],

            "duplicate":
                False,

            "processing_time_seconds":
                round(
                    total_time,
                    3,
                ),

            "processing_steps": {

                "pdf_read":
                    round(
                        read_time,
                        3,
                    ),

                "text_extraction":
                    round(
                        extraction_time,
                        3,
                    ),

                "chunking":
                    round(
                        chunk_time,
                        3,
                    ),

                "embeddings":
                    round(
                        embedding_time,
                        3,
                    ),

                "storage":
                    round(
                        save_time,
                        3,
                    ),
            },
        }

    except Exception as error:

        print()
        print("=" * 70)
        print("DOCUMENT PROCESSING ERROR")
        print("=" * 70)

        print(
            str(error)
        )

        print("=" * 70)
        print()

        raise HTTPException(
            status_code=400,
            detail=(
                "Could not process PDF: "
                f"{str(error)}"
            ),
        )


# =========================================================
# SEARCH
# =========================================================

@app.post("/documents/search")
async def search_documents(
    request: SearchRequest,
):

    try:

        print()
        print("=" * 60)
        print("LOCALIS SEARCH")
        print("=" * 60)

        print(
            "Document ID:",
            request.document_id,
        )

        print(
            "Query:",
            request.query,
        )

        results = search_document(
            document_id=request.document_id,
            query=request.query,
            top_k=request.top_k,
        )

        print(
            "Results:",
            len(results),
        )

        return {
            "status": "success",
            "query": request.query,
            "results": results,
        }

    except FileNotFoundError:

        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    except Exception as error:

        print(
            "SEARCH ERROR:",
            error,
        )

        raise HTTPException(
            status_code=400,
            detail=(
                "Search failed: "
                f"{str(error)}"
            ),
        )


# =========================================================
# ASK DOCUMENT
# =========================================================

@app.post("/documents/ask")
async def ask_document(
    request: AskRequest,
):

    total_start = time.perf_counter()

    try:

        print()
        print("=" * 70)
        print("LOCALIS QUESTION")
        print("=" * 70)

        print(
            "Document ID:",
            request.document_id,
        )

        print(
            "Question:",
            request.question,
        )

        print(
            "Top K:",
            request.top_k,
        )

        # =================================================
        # STEP 1 — SEARCH
        # =================================================

        print(
            "\n[1/3] Searching document..."
        )

        search_start = time.perf_counter()

        search_results = search_document(
            document_id=request.document_id,
            query=request.question,
            top_k=request.top_k,
        )

        search_time = (
            time.perf_counter()
            - search_start
        )

        print(
            f"[1/3] Found "
            f"{len(search_results)} "
            f"relevant chunks"
        )

        print(
            f"[1/3] Search time: "
            f"{search_time:.3f}s"
        )

        # =================================================
        # NO RESULTS
        # =================================================

        if not search_results:

            total_time = (
                time.perf_counter()
                - total_start
            )

            return {
                "status": "success",
                "question": request.question,
                "answer": (
                    "I could not find that "
                    "information in the document."
                ),
                "sources": [],
                "performance": {
                    "search_time_seconds":
                        round(
                            search_time,
                            3,
                        ),
                    "llm_time_seconds":
                        0.0,
                    "total_time_seconds":
                        round(
                            total_time,
                            3,
                        ),
                },
            }

        # =================================================
        # STEP 2 — BUILD EVIDENCE
        # =================================================

        print(
            "\n[2/3] Building evidence context..."
        )

        context_parts = []

        for result in search_results:

            text = (
                result.get(
                    "text",
                    "",
                ).strip()
            )

            if not text:
                continue

            page = result.get(
                "page"
            )

            chunk_id = result.get(
                "chunk_id"
            )

            source_header = (
                f"[PAGE {page} · "
                f"CHUNK {chunk_id}]"
            )

            context_parts.append(
                source_header
                + "\n"
                + text
            )

        context = (
            "\n\n".join(
                context_parts
            )
        )

        print(
            f"[2/3] Context characters: "
            f"{len(context)}"
        )

        # =================================================
        # STEP 3 — LOCAL AI
        # =================================================

        print(
            "\n[3/3] Generating local AI answer..."
        )

        llm_start = time.perf_counter()

        answer = generate_answer(
            question=request.question,
            context=context,
        )

        llm_time = (
            time.perf_counter()
            - llm_start
        )

        # =================================================
        # TOTAL
        # =================================================

        total_time = (
            time.perf_counter()
            - total_start
        )

        print()
        print("LOCALIS ANSWER:")
        print(answer)

        print(
            f"\nSearch time: "
            f"{search_time:.3f}s"
        )

        print(
            f"LLM time: "
            f"{llm_time:.3f}s"
        )

        print(
            f"Total time: "
            f"{total_time:.3f}s"
        )

        print()
        print("=" * 70)
        print("QUESTION COMPLETE")
        print("=" * 70)
        print()

        return {
            "status": "success",

            "question":
                request.question,

            "answer":
                answer,

            "sources":
                search_results,

            "performance": {

                "search_time_seconds":
                    round(
                        search_time,
                        3,
                    ),

                "llm_time_seconds":
                    round(
                        llm_time,
                        3,
                    ),

                "total_time_seconds":
                    round(
                        total_time,
                        3,
                    ),
            },
        }

    except FileNotFoundError:

        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    except Exception as error:

        print(
            "ASK ERROR:",
            error,
        )

        raise HTTPException(
            status_code=400,
            detail=(
                "Question answering failed: "
                f"{str(error)}"
            ),
        )