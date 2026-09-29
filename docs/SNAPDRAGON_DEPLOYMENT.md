# LOCALIS — Snapdragon Deployment Plan

## 1. Project

LOCALIS is a private, local-first document intelligence platform.

Its purpose is to allow users to upload documents and ask natural-language questions about their content without sending document data to a cloud AI service.

---

## 2. Current Architecture

LOCALIS currently follows this pipeline:

PDF
↓
Document Ingestion
↓
Native PDF Text Extraction / OCR
↓
Text Cleaning
↓
Page-Aware Chunking
↓
Embeddings
↓
Semantic + Keyword Retrieval
↓
Relevant Evidence
↓
Local Language Model
↓
Grounded Answer + Sources

---

## 3. Current AI Stack

### Document Processing

- PyMuPDF
- RapidOCR
- Python

### Embeddings

- Sentence Transformers
- all-MiniLM-L6-v2

### Language Model

- Qwen3-0.6B
- Local inference
- Hugging Face Transformers during development

### Backend

- FastAPI

### Frontend

- React
- Vite

---

## 4. Snapdragon Target

The target deployment platform is a Snapdragon-powered Windows PC, including Snapdragon X-series PCs.

LOCALIS is designed so that the document processing and retrieval pipeline remains application-level while the language-model inference layer can be optimized for Qualcomm hardware.

---

## 5. Qualcomm AI Hub Target

The current language model target is:

Qwen3-0.6B

Qualcomm AI Hub provides a Qwen3-0.6B model variant suitable for Snapdragon platforms.

Target model characteristics:

- Model: Qwen3-0.6B
- Quantization: Q4_0
- Format: GGUF
- Approximate model size: 429 MB
- Input modality: Text
- Output modality: Text

The Snapdragon deployment will use the Qualcomm-supported optimized model/runtime rather than relying on the development laptop's CPU inference path.

---

## 6. Dual Runtime Architecture

LOCALIS will support two inference environments.

### Development Environment

Used on conventional development laptops.

```text
LOCALIS
   ↓
FastAPI
   ↓
Retrieval
   ↓
Qwen3-0.6B
   ↓
CPU / available local compute