import { useEffect, useRef, useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

type Source = {
  chunk_id: number;
  page?: number;
  text: string;
  score?: number;
  semantic_score?: number;
  keyword_score?: number;
  phrase_score?: number;
};

type Document = {
  document_id: string;
  filename: string;
  pages: number;
  chunks: number;
};

type PreviewPage = {
  page: number;
  text: string;
};

function AIThinking({ text }: { text: string }) {
  return (
    <div className="ai-thinking">
      <div className="ai-thinking-logo">
        <div className="ai-logo-core">
          <span>✦</span>
        </div>

        <div className="ai-orbit orbit-1" />
        <div className="ai-orbit orbit-2" />
      </div>

      <div className="ai-thinking-content">
        <div className="ai-thinking-title">
          <span>LOCALIS</span>
          <span className="thinking-label">LOCAL AI</span>
        </div>

        <div className="ai-thinking-text">
          {text}
          <span className="thinking-dots">
            <span>.</span>
            <span>.</span>
            <span>.</span>
          </span>
        </div>
      </div>
    </div>
  );
}

function App() {
  const [file, setFile] = useState<File | null>(null);

  const [documentId, setDocumentId] = useState("");

  const [question, setQuestion] = useState("");

  const [answer, setAnswer] = useState("");

  const [sources, setSources] = useState<Source[]>([]);

  const [documents, setDocuments] = useState<Document[]>([]);

  const [previewDocument, setPreviewDocument] =
    useState<Document | null>(null);

  const [previewPages, setPreviewPages] =
    useState<PreviewPage[]>([]);

  const [loadingPreview, setLoadingPreview] =
    useState(false);

  const [activeDocumentId, setActiveDocumentId] =
    useState<string | null>(null);

  const [loadingDocuments, setLoadingDocuments] =
    useState(false);

  const [cleaningDuplicates, setCleaningDuplicates] =
    useState(false);

  const [loadingUpload, setLoadingUpload] =
    useState(false);

  const [uploadStage, setUploadStage] =
    useState("");

  const [loadingAsk, setLoadingAsk] =
    useState(false);

  const [isThinking, setIsThinking] =
    useState(false);

  const [thinkingText, setThinkingText] =
    useState("Thinking");

  const [message, setMessage] =
    useState("");

  const thinkingIntervalRef =
    useRef<number | null>(null);

  /*
   * =========================================================
   * LOAD DOCUMENT LIBRARY
   * =========================================================
   */

  const loadDocuments = async () => {
    try {
      setLoadingDocuments(true);

      console.log(
        "LOCALIS: Loading document library..."
      );

      const response = await fetch(
        `${API_URL}/documents`
      );

      if (!response.ok) {
        throw new Error(
          `Failed to load documents: ${response.status}`
        );
      }

      const data = await response.json();

      const loadedDocuments: Document[] =
        data.documents || [];

      console.log(
        "LOCALIS DOCUMENTS:",
        loadedDocuments
      );

      setDocuments(loadedDocuments);

      setActiveDocumentId((currentId) => {
        if (currentId) {
          return currentId;
        }

        return loadedDocuments.length > 0
          ? loadedDocuments[0].document_id
          : null;
      });

      setDocumentId((currentId) => {
        if (currentId) {
          return currentId;
        }

        return loadedDocuments.length > 0
          ? loadedDocuments[0].document_id
          : "";
      });
    } catch (error) {
      console.error(
        "DOCUMENT LIBRARY ERROR:",
        error
      );
    } finally {
      setLoadingDocuments(false);
    }
  };

  /*
   * =========================================================
   * LOAD DOCUMENTS WHEN APP STARTS
   * =========================================================
   */

  useEffect(() => {
    loadDocuments();
  }, []);

  /*
   * =========================================================
   * CLEAN THINKING ANIMATION
   * =========================================================
   */

  useEffect(() => {
    return () => {
      if (
        thinkingIntervalRef.current !== null
      ) {
        window.clearInterval(
          thinkingIntervalRef.current
        );
      }
    };
  }, []);

  /*
   * =========================================================
   * SELECT DOCUMENT
   * =========================================================
   */

  const handleSelectDocument = (
    selectedDocument: Document
  ) => {
    setActiveDocumentId(
      selectedDocument.document_id
    );

    setDocumentId(
      selectedDocument.document_id
    );

    setFile(null);

    setQuestion("");

    setAnswer("");

    setSources([]);

    setMessage(
      `Selected ${selectedDocument.filename}`
    );

    console.log(
      "LOCALIS ACTIVE DOCUMENT:",
      selectedDocument
    );
  };

  /*
   * =========================================================
   * DELETE DOCUMENT
   * =========================================================
   */

  const handleDeleteDocument = async (
    event: React.MouseEvent,
    selectedDocument: Document
  ) => {
    event.stopPropagation();

    const confirmed = window.confirm(
      `Delete "${selectedDocument.filename}" from LOCALIS?`
    );

    if (!confirmed) {
      return;
    }

    try {
      setMessage(
        `Deleting ${selectedDocument.filename}...`
      );

      const response = await fetch(
        `${API_URL}/documents/${selectedDocument.document_id}`,
        {
          method: "DELETE",
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "Could not delete document."
        );
      }

      setDocuments((currentDocuments) =>
        currentDocuments.filter(
          (document) =>
            document.document_id !==
            selectedDocument.document_id
        )
      );

      if (
        activeDocumentId ===
        selectedDocument.document_id
      ) {
        setActiveDocumentId(null);
        setDocumentId("");
        setQuestion("");
        setAnswer("");
        setSources([]);
      }

      setMessage(
        `"${selectedDocument.filename}" deleted successfully.`
      );
    } catch (error) {
      console.error(
        "LOCALIS DELETE ERROR:",
        error
      );

      setMessage(
        error instanceof Error
          ? error.message
          : "Could not delete the document."
      );
    }
  };

  /*
   * =========================================================
   * LOAD DOCUMENT PREVIEW
   * =========================================================
   */

  const handlePreviewDocument = async (
    selectedDocument: Document
  ) => {
    try {
      setLoadingPreview(true);

      setPreviewDocument(
        selectedDocument
      );

      setPreviewPages([]);

      console.log(
        "LOCALIS: Loading preview...",
        selectedDocument.document_id
      );

      const response = await fetch(
        `${API_URL}/documents/${selectedDocument.document_id}/preview`
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "Could not load document preview."
        );
      }

      setPreviewPages(
        data.pages || []
      );

      console.log(
        "LOCALIS PREVIEW:",
        data
      );
    } catch (error) {
      console.error(
        "LOCALIS PREVIEW ERROR:",
        error
      );

      setMessage(
        error instanceof Error
          ? error.message
          : "Could not load document preview."
      );
    } finally {
      setLoadingPreview(false);
    }
  };

  /*
   * =========================================================
   * CLEAN DUPLICATE DOCUMENTS
   * =========================================================
   */

  const handleCleanDuplicates = async () => {
    const confirmed = window.confirm(
      "LOCALIS will find exact duplicate documents and keep the first copy. Continue?"
    );

    if (!confirmed) {
      return;
    }

    try {
      setCleaningDuplicates(true);

      setMessage(
        "Checking for duplicate documents..."
      );

      console.log(
        "LOCALIS: Cleaning duplicate documents..."
      );

      const response = await fetch(
        `${API_URL}/documents/cleanup-duplicates`,
        {
          method: "POST",
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "Could not clean duplicate documents."
        );
      }

      const deletedCount =
        data.deleted_count || 0;

      console.log(
        "LOCALIS DUPLICATE CLEANUP:",
        data
      );

      const deletedIds =
        new Set<string>(
          (data.deleted_documents || []).map(
            (document: {
              document_id: string;
            }) => document.document_id
          )
        );

      if (
        activeDocumentId &&
        deletedIds.has(activeDocumentId)
      ) {
        setActiveDocumentId(null);
        setDocumentId("");
        setQuestion("");
        setAnswer("");
        setSources([]);
      }

      await loadDocuments();

      if (deletedCount === 0) {
        setMessage(
          "No duplicate documents were found."
        );
      } else {
        setMessage(
          `${deletedCount} duplicate document${
            deletedCount !== 1
              ? "s"
              : ""
          } cleaned successfully.`
        );
      }
    } catch (error) {
      console.error(
        "LOCALIS DUPLICATE CLEANUP ERROR:",
        error
      );

      setMessage(
        error instanceof Error
          ? error.message
          : "Could not clean duplicate documents."
      );
    } finally {
      setCleaningDuplicates(false);
    }
  };

  /*
   * =========================================================
   * FILE SELECTION
   * =========================================================
   */

  const handleFileChange = (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const selectedFile =
      event.target.files?.[0] || null;

    setFile(selectedFile);

    setMessage("");

    setAnswer("");

    setSources([]);

    setDocumentId("");

    setUploadStage("");
  };

  /*
   * =========================================================
   * UPLOAD / PROCESS DOCUMENT
   * =========================================================
   */

  const handleUpload = async () => {
    if (!file) {
      setMessage(
        "Please select a PDF first."
      );
      return;
    }

    setLoadingUpload(true);

    setUploadStage(
      "Uploading PDF..."
    );

    setMessage(
      "Connecting to LOCALIS..."
    );

    setAnswer("");

    setSources([]);

    setDocumentId("");

    const formData = new FormData();

    formData.append(
      "file",
      file
    );

    const controller =
      new AbortController();

    const timeoutId =
      window.setTimeout(() => {
        controller.abort();
      }, 120000);

    try {
      console.log(
        "================================="
      );

      console.log(
        "LOCALIS UPLOAD START"
      );

      console.log(
        "API:",
        `${API_URL}/documents/extract`
      );

      console.log(
        "File:",
        file.name
      );

      console.log(
        "Size:",
        file.size
      );

      console.log(
        "================================="
      );

      setUploadStage(
        "Sending document to LOCALIS..."
      );

      setMessage(
        "Processing document locally..."
      );

      const response =
        await fetch(
          `${API_URL}/documents/extract`,
          {
            method: "POST",
            body: formData,
            signal: controller.signal,
          }
        );

      console.log(
        "LOCALIS response status:",
        response.status
      );

      const responseText =
        await response.text();

      console.log(
        "LOCALIS raw response:",
        responseText
      );

      let data: any = {};

      try {
        data = JSON.parse(
          responseText
        );
      } catch {
        throw new Error(
          "LOCALIS returned an invalid response."
        );
      }

      if (!response.ok) {
        throw new Error(
          data.detail ||
            `Upload failed with HTTP ${response.status}`
        );
      }

      if (!data.document_id) {
        throw new Error(
          "Document was processed, but LOCALIS did not return a document ID."
        );
      }

      setUploadStage(
        "Document processed successfully."
      );

      setDocumentId(
        data.document_id
      );

      setActiveDocumentId(
        data.document_id
      );

      setMessage(
        `Document processed successfully · ${data.page_count} page${
          data.page_count !== 1
            ? "s"
            : ""
        } · ${data.chunk_count} chunk${
          data.chunk_count !== 1
            ? "s"
            : ""
        }`
      );

      console.log(
        "LOCALIS DOCUMENT READY:",
        data.document_id
      );

      await loadDocuments();

      setDocumentId(
        data.document_id
      );

      setActiveDocumentId(
        data.document_id
      );
    } catch (error) {
      console.error(
        "LOCALIS UPLOAD ERROR:",
        error
      );

      if (
        error instanceof DOMException &&
        error.name === "AbortError"
      ) {
        setUploadStage(
          "Processing timed out."
        );

        setMessage(
          "LOCALIS took more than 2 minutes to process this document. Check the backend terminal."
        );
      } else if (
        error instanceof Error
      ) {
        setUploadStage(
          "Processing failed."
        );

        setMessage(
          error.message
        );
      } else {
        setUploadStage(
          "Processing failed."
        );

        setMessage(
          "Something went wrong while processing the document."
        );
      }
    } finally {
      window.clearTimeout(
        timeoutId
      );

      setLoadingUpload(false);
    }
  };

  /*
   * =========================================================
   * ASK DOCUMENT
   * =========================================================
   */

  const handleAsk = async () => {
    if (
      !question.trim() ||
      !documentId
    ) {
      return;
    }

    setAnswer("");

    setSources([]);

    setMessage("");

    setLoadingAsk(true);

    setIsThinking(true);

    setThinkingText(
      "Reading your document"
    );

    const thinkingMessages = [
      "Reading your document",
      "Finding relevant information",
      "Understanding the context",
      "Connecting relevant sections",
      "Preparing your answer",
    ];

    let messageIndex = 0;

    thinkingIntervalRef.current =
      window.setInterval(() => {
        messageIndex =
          (messageIndex + 1) %
          thinkingMessages.length;

        setThinkingText(
          thinkingMessages[
            messageIndex
          ]
        );
      }, 1200);

    const controller =
      new AbortController();

    const timeoutId =
      window.setTimeout(() => {
        controller.abort();
      }, 180000);

    try {
      const response =
        await fetch(
          `${API_URL}/documents/ask`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify({
              document_id:
                documentId,

              question:
                question.trim(),

              top_k: 6,
            }),

            signal: controller.signal,
          }
        );

      window.clearTimeout(
        timeoutId
      );

      const responseText =
        await response.text();

      console.log(
        "LOCALIS ASK RESPONSE:",
        responseText
      );

      let data: any = {};

      try {
        data = JSON.parse(
          responseText
        );
      } catch {
        throw new Error(
          "LOCALIS returned an invalid answer response."
        );
      }

      if (!response.ok) {
        throw new Error(
          data.detail ||
            `Question failed with HTTP ${response.status}`
        );
      }

      if (
        thinkingIntervalRef.current !==
        null
      ) {
        window.clearInterval(
          thinkingIntervalRef.current
        );

        thinkingIntervalRef.current =
          null;
      }

      setThinkingText(
        "Answer ready"
      );

      await new Promise(
        (resolve) =>
          setTimeout(
            resolve,
            500
          )
      );

      setIsThinking(false);

      setLoadingAsk(false);

      const finalAnswer =
        data.answer ||
        "No answer was returned.";

      setSources(
        data.sources || []
      );

      /*
       * =====================================================
       * TYPEWRITER EFFECT
       * =====================================================
       */

      setAnswer("");

      for (
        let index = 0;
        index <= finalAnswer.length;
        index++
      ) {
        setAnswer(
          finalAnswer.slice(
            0,
            index
          )
        );

        await new Promise(
          (resolve) =>
            setTimeout(
              resolve,
              finalAnswer.length >
              500
                ? 5
                : 12
            )
        );
      }
    } catch (error) {
      window.clearTimeout(
        timeoutId
      );

      if (
        thinkingIntervalRef.current !==
        null
      ) {
        window.clearInterval(
          thinkingIntervalRef.current
        );

        thinkingIntervalRef.current =
          null;
      }

      setIsThinking(false);

      setLoadingAsk(false);

      if (
        error instanceof DOMException &&
        error.name === "AbortError"
      ) {
        setMessage(
          "LOCALIS took too long to generate the answer. Check the backend terminal."
        );
      } else if (
        error instanceof Error
      ) {
        setMessage(
          error.message
        );
      } else {
        setMessage(
          "Something went wrong while asking LOCALIS."
        );
      }
    }
  };

  /*
   * =========================================================
   * ACTIVE DOCUMENT
   * =========================================================
   */

  const activeDocument =
    documents.find(
      (document) =>
        document.document_id ===
        activeDocumentId
    );

  /*
   * =========================================================
   * UI
   * =========================================================
   */

  return (
    <div className="app-shell">

      {/* =====================================================
          NAVBAR
          ===================================================== */}

      <header className="navbar">

        <div className="brand">

          <div className="brand-mark">
            L
          </div>

          <div>
            <div className="brand-name">
              LOCALIS
            </div>

            <div className="brand-subtitle">
              PRIVATE AI
            </div>
          </div>

        </div>

        <div className="nav-status">
          <span className="status-dot" />
          Running locally
        </div>

      </header>


      {/* =====================================================
          MAIN
          ===================================================== */}

      <main className="main-container">

        {/* ===================================================
            HERO
            =================================================== */}

        <section className="hero">

          <div className="hero-badge">
            <span>●</span>
            LOCAL-FIRST AI
          </div>

          <div className="document-library-header">

            <div>
              <h2>
                Your documents
              </h2>

              <p>
                Select a previously processed
                document or upload a new PDF.
              </p>
            </div>

            <button
              type="button"
              className="cleanup-duplicates-button"
              onClick={
                handleCleanDuplicates
              }
              disabled={
                cleaningDuplicates ||
                documents.length < 2
              }
            >
              {cleaningDuplicates
                ? "Cleaning..."
                : "Clean duplicates"}
            </button>

          </div>

          <div className="feature-row">

            <div className="feature-pill">
              🔒 Private
            </div>

            <div className="feature-pill">
              ⚡ Local processing
            </div>

            <div className="feature-pill">
              ◈ Source grounded
            </div>

          </div>

        </section>


        {/* ===================================================
            DOCUMENT LIBRARY
            =================================================== */}

        <section className="workspace">

          <div className="section-label">
            01 · DOCUMENT LIBRARY
          </div>

          <div className="upload-card">

            <div className="upload-content">

              <h2>
                Your documents
              </h2>

              <p>
                Select a previously processed
                document or upload a new PDF.
              </p>

              {loadingDocuments ? (

                <div className="message-card">
                  Loading document library...
                </div>

              ) : documents.length === 0 ? (

                <div className="message-card">
                  No documents stored yet.
                  Upload your first PDF below.
                </div>

              ) : (

                <div className="document-library-grid">

                  {documents.map(
                    (document) => (

                      <div
                        key={
                          document.document_id
                        }
                        className={`document-library-button ${
                          document.document_id ===
                          activeDocumentId
                            ? "active"
                            : ""
                        }`}
                        onClick={() => {
                          handleSelectDocument(
                            document
                          );

                          handlePreviewDocument(
                            document
                          );
                        }}
                        role="button"
                        tabIndex={0}
                        onKeyDown={(event) => {
                          if (
                            event.key ===
                              "Enter" ||
                            event.key ===
                              " "
                          ) {
                            handleSelectDocument(
                              document
                            );

                            handlePreviewDocument(
                              document
                            );
                          }
                        }}
                      >

                        <span className="document-library-icon">
                          PDF
                        </span>

                        <span className="document-library-content">

                          <span className="document-library-name">
                            {document.filename}
                          </span>

                          <span className="document-library-meta">
                            {document.pages} page
                            {document.pages !==
                            1
                              ? "s"
                              : ""}
                            {" · "}
                            {document.chunks} chunk
                            {document.chunks !==
                            1
                              ? "s"
                              : ""}
                          </span>

                        </span>

                        <div className="document-library-actions">

                          <span className="document-library-arrow">
                            →
                          </span>

                          <button
                            type="button"
                            className="document-delete-button"
                            onClick={(event) =>
                              handleDeleteDocument(
                                event,
                                document
                              )
                            }
                            title="Delete document"
                          >
                            ×
                          </button>

                        </div>

                      </div>

                    )
                  )}

                </div>

              )}

            </div>

          </div>

        </section>


        {/* ===================================================
            DOCUMENT UPLOAD
            =================================================== */}

        <section className="workspace">

          <div className="section-label">
            02 · UPLOAD
          </div>

          <div className="upload-card">

            <div className="upload-icon">
              ↑
            </div>

            <div className="upload-content">

              <h2>
                Upload your document
              </h2>

              <p>
                PDF files are processed locally
                by LOCALIS.
              </p>

              <label className="file-picker">

                <input
                  type="file"
                  accept=".pdf,application/pdf"
                  onChange={
                    handleFileChange
                  }
                />

                <span>
                  Choose PDF
                </span>

              </label>

              {file && (

                <div className="selected-file">

                  <div className="file-symbol">
                    PDF
                  </div>

                  <div className="file-info">

                    <strong>
                      {file.name}
                    </strong>

                    <span>
                      {(
                        file.size /
                        1024 /
                        1024
                      ).toFixed(2)}{" "}
                      MB
                    </span>

                  </div>

                  <span className="check">
                    ✓
                  </span>

                </div>

              )}

            </div>

            <button
              className="primary-button"
              onClick={
                handleUpload
              }
              disabled={
                !file ||
                loadingUpload
              }
            >

              {loadingUpload
                ? "Processing..."
                : "Process document"}

              {!loadingUpload && (
                <span>
                  →
                </span>
              )}

            </button>

          </div>


          {/* =================================================
              PROCESSING STATUS
              ================================================= */}

          {loadingUpload && (

            <div className="processing-status">

              <div className="processing-spinner">
                <span />
              </div>

              <div className="processing-content">

                <div className="processing-title">
                  LOCALIS is processing
                  your document
                </div>

                <div className="processing-stage">
                  {uploadStage ||
                    "Preparing document..."}
                </div>

                <div className="processing-note">
                  Your PDF is being processed
                  locally. Nothing is being
                  uploaded to a cloud AI service.
                </div>

              </div>

            </div>

          )}


          {documentId && (

            <div className="success-card">

              <div className="success-icon">
                ✓
              </div>

              <div>

                <strong>
                  Document ready
                </strong>

                <p>
                  {activeDocument
                    ? activeDocument.filename
                    : message}
                </p>

              </div>

            </div>

          )}


          {!documentId &&
            message && (
              <div className="message-card">
                {message}
              </div>
            )}

        </section>


        {/* ===================================================
            ACTIVE DOCUMENT
            =================================================== */}

        {activeDocument && (

          <section className="workspace">

            <div className="section-label">
              ACTIVE DOCUMENT
            </div>

            <div className="success-card">

              <div className="success-icon">
                ✓
              </div>

              <div>

                <strong>
                  {activeDocument.filename}
                </strong>

                <p>
                  {activeDocument.pages} page
                  {activeDocument.pages !==
                  1
                    ? "s"
                    : ""}
                  {" · "}
                  {activeDocument.chunks} chunk
                  {activeDocument.chunks !==
                  1
                    ? "s"
                    : ""}
                  {" · "}
                  Ready for questions
                </p>

              </div>

            </div>

          </section>

        )}


        {/* ===================================================
            DOCUMENT PREVIEW
            =================================================== */}

        {previewDocument && (

          <section className="workspace">

            <div className="section-label">
              DOCUMENT PREVIEW
            </div>

            <div className="document-preview-card">

              <div className="document-preview-header">

                <div>

                  <div className="document-preview-title">
                    {previewDocument.filename}
                  </div>

                  <div className="document-preview-meta">
                    {previewDocument.pages} page
                    {previewDocument.pages !==
                    1
                      ? "s"
                      : ""}
                    {" · "}
                    {previewDocument.chunks} chunk
                    {previewDocument.chunks !==
                    1
                      ? "s"
                      : ""}
                  </div>

                </div>

                <button
                  type="button"
                  className="document-preview-close"
                  onClick={() => {
                    setPreviewDocument(
                      null
                    );

                    setPreviewPages([]);
                  }}
                >
                  ×
                </button>

              </div>


              {loadingPreview ? (

                <div className="document-preview-loading">
                  Loading document...
                </div>

              ) : previewPages.length ===
                0 ? (

                <div className="document-preview-empty">
                  No extracted page content
                  is available.
                </div>

              ) : (

                <div className="document-preview-pages">

                  {previewPages.map(
                    (page) => (

                      <div
                        key={page.page}
                        className="document-preview-page"
                      >

                        <div className="document-preview-page-number">
                          PAGE {page.page}
                        </div>

                        <div className="document-preview-text">
                          {page.text ||
                            "No text extracted from this page."}
                        </div>

                      </div>

                    )
                  )}

                </div>

              )}

            </div>

          </section>

        )}


        {/* ===================================================
            ASK
            =================================================== */}

        <section className="workspace">

          <div className="section-label">
            03 · ASK
          </div>

          <div className="ask-card">

            <div className="ask-heading">

              <div>

                <h2>
                  Ask your document
                </h2>

                <p>
                  Ask questions in natural
                  language and get answers
                  grounded in your uploaded
                  content.
                </p>

              </div>

              <div className="ai-badge">
                LOCAL AI
              </div>

            </div>


            <div className="question-box">

              <textarea
                value={question}
                onChange={(event) =>
                  setQuestion(
                    event.target.value
                  )
                }
                placeholder={
                  documentId
                    ? "What would you like to know?"
                    : "Process a document first, then ask anything..."
                }
                rows={3}
              />

              <button
                className="ask-button"
                onClick={
                  handleAsk
                }
                disabled={
                  !documentId ||
                  !question.trim() ||
                  loadingAsk
                }
              >

                {loadingAsk
                  ? "Thinking..."
                  : "Ask"}

                {!loadingAsk && (
                  <span>
                    ↗
                  </span>
                )}

              </button>

            </div>


            {!documentId && (

              <div className="locked-message">
                Your question is ready —
                process a document above
                to let LOCALIS answer it.
              </div>

            )}

          </div>

        </section>


        {/* ===================================================
            AI RESPONSE
            =================================================== */}

        {(isThinking || answer) && (

          <section className="results-section">

            <div className="section-label">
              04 · ANSWER
            </div>


            {/* THINKING */}

            {isThinking && (

              <AIThinking
                text={
                  thinkingText
                }
              />

            )}


            {/* ANSWER */}

            {answer &&
              !isThinking && (

                <div className="answer-card">

                  <div className="answer-header">

                    <div className="answer-icon">
                      ✦
                    </div>

                    <div>

                      <span>
                        LOCAL AI ANSWER
                      </span>

                      <h2>
                        Your answer
                      </h2>

                    </div>

                  </div>

                  <p className="answer-text">
                    {answer}
                    <span className="typing-cursor" />
                  </p>

                </div>

              )}


            {/* SOURCES */}

            {answer &&
              !isThinking &&
              sources.length > 0 && (

                <div className="sources">

                  <div className="sources-title">

                    <span>
                      Sources
                    </span>

                    <small>
                      {sources.length}{" "}
                      relevant chunk(s)
                    </small>

                  </div>


                  <div className="source-grid">

                    {sources.map(
                      (
                        source,
                        index
                      ) => (

                        <div
                          className="source-card"
                          key={
                            `${source.chunk_id}-${index}`
                          }
                        >

                          <div className="source-top">

                            <div className="source-meta">

                              <span className="source-location">
                                PAGE{" "}
                                {source.page ??
                                  "?"}
                                {" · "}
                                CHUNK{" "}
                                {
                                  source.chunk_id
                                }
                              </span>

                              {source.score !==
                                undefined && (
                                <span className="source-score">
                                  {(
                                    source.score *
                                    100
                                  ).toFixed(
                                    1
                                  )}
                                  %
                                </span>
                              )}

                            </div>

                          </div>

                          <p>
                            {source.text}
                          </p>

                        </div>

                      )
                    )}

                  </div>

                </div>

              )}

          </section>

        )}


        {/* ===================================================
            ERROR / MESSAGE
            =================================================== */}

        {message &&
          !documentId &&
          !answer && (

            <div className="bottom-message">
              {message}
            </div>

          )}

      </main>


      {/* =====================================================
          FOOTER
          ===================================================== */}

      <footer className="footer">

        <span>
          LOCALIS
        </span>

        <span>
          Private AI · Local-first architecture
        </span>

        <span>
          v0.1.0
        </span>

      </footer>

    </div>
  );
}

export default App;