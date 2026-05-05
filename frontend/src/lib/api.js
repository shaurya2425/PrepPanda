/**
 * PrepPanda API Client
 * ====================
 * Centralised module for all communication with the FastAPI backend.
 *
 * Usage:
 *   import { api } from '@/lib/api';
 *
 *   const books  = await api.catalog.listBooks();
 *   const answer = await api.srs.ask(chapterId, 'What is mitosis?');
 *   const tree   = await api.mindmap.getTree(chapterId);
 */

// ─────────────────────────────────────────────────────────────────────
// Config
// ─────────────────────────────────────────────────────────────────────

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

// Admin auth is stored in localStorage


// ─────────────────────────────────────────────────────────────────────
// Custom error
// ─────────────────────────────────────────────────────────────────────

export class ApiError extends Error {
  /**
   * @param {number}  status   – HTTP status code
   * @param {string}  message  – Human-readable message
   * @param {object}  [body]   – Raw parsed JSON body from the server
   */
  constructor(status, message, body = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

// ─────────────────────────────────────────────────────────────────────
// Internal helpers
// ─────────────────────────────────────────────────────────────────────

/**
 * Low-level request wrapper.
 *
 * - Automatically prepends BASE_URL.
 * - JSON-encodes body when `json` option is provided.
 * - Throws `ApiError` on non-2xx responses.
 * - Returns parsed JSON (or null for 204 No Content).
 *
 * @param {string}  path      – e.g. "/srs/ask"
 * @param {object}  [opts]
 * @param {'GET'|'POST'|'PUT'|'PATCH'|'DELETE'} [opts.method='GET']
 * @param {object}  [opts.json]       – Object → JSON body
 * @param {FormData} [opts.formData]  – Multipart body (don't set Content-Type manually)
 * @param {object}  [opts.headers]    – Extra headers
 * @param {AbortSignal} [opts.signal] – For request cancellation
 * @returns {Promise<any>}
 */
async function request(path, opts = {}) {
  const {
    method = "GET",
    json,
    formData,
    headers: extraHeaders = {},
    signal,
  } = opts;

  const headers = { ...extraHeaders };

  let body;
  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(json);
  } else if (formData !== undefined) {
    // Let the browser set the multipart boundary automatically
    body = formData;
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body,
    signal,
  });

  // No Content
  if (res.status === 204) return null;

  let data;
  const contentType = res.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    data = await res.json();
  } else {
    data = await res.text();
  }

  if (!res.ok) {
    const message =
      typeof data === "object" && data?.detail
        ? typeof data.detail === "string"
          ? data.detail
          : JSON.stringify(data.detail)
        : `Request failed with status ${res.status}`;
    throw new ApiError(res.status, message, data);
  }

  return data;
}

/**
 * Shorthand for admin-protected requests.
 * Injects the Authorization header automatically.
 */
function adminRequest(path, opts = {}) {
  const auth = localStorage.getItem("adminAuth") || "";
  const headers = {
    ...opts.headers,
    "Authorization": `Basic ${auth}`,
  };
  return request(path, { ...opts, headers });
}

/**
 * Build a query-string from an object, ignoring null/undefined values.
 * @param {Record<string, any>} params
 * @returns {string}  e.g. "?grade=11&subject=biology" or ""
 */
function qs(params) {
  const entries = Object.entries(params).filter(
    ([, v]) => v !== undefined && v !== null
  );
  if (entries.length === 0) return "";
  return "?" + new URLSearchParams(entries).toString();
}

// ─────────────────────────────────────────────────────────────────────
// API — Health
// ─────────────────────────────────────────────────────────────────────

const health = {
  /**
   * Server health check.
   * @returns {Promise<{ status: string, version: string }>}
   */
  check() {
    return request("/health");
  },
};

// ─────────────────────────────────────────────────────────────────────
// API — Catalog  (public, user-facing reads)
// ─────────────────────────────────────────────────────────────────────

const catalog = {
  /**
   * List all available books.
   *
   * @param {{ grade?: number, subject?: string }} [filters]
   * @returns {Promise<Array<{
   *   book_id: string, title: string, grade: number,
   *   subject: string, chapter_count: number
   * }>>}
   */
  listBooks(filters = {}) {
    return request(`/catalog/books${qs(filters)}`);
  },

  /**
   * Get a single book with its full chapter listing.
   *
   * @param {string} bookId – UUID
   * @returns {Promise<{
   *   book_id: string, title: string, grade: number, subject: string,
   *   chapters: Array<{
   *     chapter_id: string, book_id: string, chapter_number: number,
   *     title: string, pdf_url?: string, chunk_count: number,
   *     image_count: number, pyq_count: number
   *   }>
   * }>}
   */
  getBook(bookId) {
    return request(`/catalog/books/${bookId}`);
  },

  /**
   * List chapters for a book.
   *
   * @param {string} bookId – UUID
   * @returns {Promise<Array<{
   *   chapter_id: string, book_id: string, chapter_number: number,
   *   title: string, pdf_url?: string, chunk_count: number,
   *   image_count: number, pyq_count: number
   * }>>}
   */
  listChapters(bookId) {
    return request(`/catalog/books/${bookId}/chapters`);
  },

  /**
   * Get detail for a single chapter.
   *
   * @param {string} chapterId – UUID
   * @returns {Promise<{
   *   chapter_id: string, book_id: string, chapter_number: number,
   *   title: string, pdf_url?: string, chunk_count: number,
   *   image_count: number, pyq_count: number
   * }>}
   */
  getChapter(chapterId) {
    return request(`/catalog/chapters/${chapterId}`);
  },

  /**
   * List PYQs for an entire book (paginated).
   *
   * @param {string} bookId
   * @param {{ year?: number, exam?: string, limit?: number, offset?: number }} [filters]
   * @returns {Promise<{
   *   total: number, limit: number, offset: number,
   *   items: Array<{
   *     pyq_id: string, book_id: string, chapter_id?: string,
   *     question: string, answer?: string, year?: number,
   *     exam?: string, marks?: number
   *   }>
   * }>}
   */
  listBookPyqs(bookId, filters = {}) {
    return request(`/catalog/books/${bookId}/pyqs${qs(filters)}`);
  },

  /**
   * List PYQs for a specific chapter (paginated).
   *
   * @param {string} chapterId
   * @param {{ year?: number, exam?: string, limit?: number, offset?: number }} [filters]
   * @returns {Promise<{
   *   total: number, limit: number, offset: number,
   *   items: Array<{
   *     pyq_id: string, book_id: string, chapter_id?: string,
   *     question: string, answer?: string, year?: number,
   *     exam?: string, marks?: number
   *   }>
   * }>}
   */
  listChapterPyqs(chapterId, filters = {}) {
    return request(`/catalog/chapters/${chapterId}/pyqs${qs(filters)}`);
  },

  /**
   * Get the full URL to stream the chapter PDF.
   *
   * @param {string} chapterId
   * @returns {string} The full URL string
   */
  getChapterPdfUrl(chapterId) {
    return `${BASE_URL}/catalog/chapters/${chapterId}/pdf`;
  },

  /**
   * Wrap an S3/MinIO URL in the backend proxy to avoid MetadataTooLarge errors.
   */
  getMediaProxyUrl(url) {
    if (!url) return "";
    // Only proxy urls that look like our bucket URLs
    if (url.includes(":9000") || url.includes("uploads/")) {
      return `${BASE_URL}/catalog/media?url=${encodeURIComponent(url)}`;
    }
    return url;
  },
};

// ─────────────────────────────────────────────────────────────────────
// API — Admin — Books  (protected)
// ─────────────────────────────────────────────────────────────────────

const books = {
  /**
   * Create a new book record.
   *
   * @param {{ title: string, grade: number, subject: string }} data
   * @returns {Promise<{ book_id: string, title: string, grade: number, subject: string }>}
   */
  create(data) {
    return adminRequest("/admin/books", {
      method: "POST",
      json: data,
    });
  },

  /**
   * One-shot: create a book and ingest all chapters at once.
   *
   * @param {{ title: string, grade: number, subject: string }} bookMeta
   * @param {Array<{ number: number, title: string }>} chapters  – ordered metadata
   * @param {File[]} pdfFiles  – PDF files **in the same order** as `chapters`
   * @param {{ signal?: AbortSignal }} [opts]
   * @returns {Promise<object>}  IngestBookOut
   */
  ingestBook(bookMeta, chapters, pdfFiles, opts = {}) {
    const fd = new FormData();
    fd.append("title", bookMeta.title);
    fd.append("grade", String(bookMeta.grade));
    fd.append("subject", bookMeta.subject);
    fd.append("chapters", JSON.stringify(chapters));
    pdfFiles.forEach((file) => fd.append("pdfs", file));

    return adminRequest("/admin/ingest-book", {
      method: "POST",
      formData: fd,
      signal: opts.signal,
    });
  },

  /**
   * Delete a book
   * @param {string} bookId
   */
  delete(bookId) {
    return adminRequest(`/admin/books/${bookId}`, {
      method: "DELETE",
    });
  },
};

// ─────────────────────────────────────────────────────────────────────
// API — Admin — Chapters  (protected)
// ─────────────────────────────────────────────────────────────────────

const chapters = {
  /**
   * Upload & ingest a single chapter PDF for an existing book.
   *
   * @param {string} bookId
   * @param {{ chapterNumber: number, chapterTitle: string }} meta
   * @param {File}   pdfFile
   * @param {{ signal?: AbortSignal }} [opts]
   * @returns {Promise<object>}  ChapterOut
   */
  ingest(bookId, meta, pdfFile, opts = {}) {
    const fd = new FormData();
    fd.append("chapter_number", String(meta.chapterNumber));
    fd.append("chapter_title", meta.chapterTitle);
    fd.append("pdf", pdfFile);

    return adminRequest(`/admin/books/${bookId}/chapters`, {
      method: "POST",
      formData: fd,
      signal: opts.signal,
    });
  },
};

// ─────────────────────────────────────────────────────────────────────
// API — Admin — PYQs  (protected)
// ─────────────────────────────────────────────────────────────────────

const pyqs = {
  /**
   * Ingest PYQ blocks as raw text for a book.
   * Each question is auto-mapped to the best chapter by semantic similarity.
   *
   * @param {string} bookId
   * @param {string} rawText  – PYQ block-formatted text
   * @returns {Promise<{ inserted: number, skipped: number, pyq_ids: string[] }>}
   */
  ingestText(bookId, rawText) {
    const fd = new FormData();
    fd.append("body", rawText);

    return adminRequest(`/admin/books/${bookId}/pyqs`, {
      method: "POST",
      formData: fd,
    });
  },

  /**
   * Ingest PYQ blocks from a plain-text file upload.
   *
   * @param {string} bookId
   * @param {File}   file  – .txt file with PYQ blocks
   * @returns {Promise<{ inserted: number, skipped: number, pyq_ids: string[] }>}
   */
  ingestFile(bookId, file) {
    const fd = new FormData();
    fd.append("file", file);

    return adminRequest(`/admin/books/${bookId}/pyqs/file`, {
      method: "POST",
      formData: fd,
    });
  },

  /**
   * Delete a PYQ
   * @param {string} pyqId
   */
  delete(pyqId) {
    return adminRequest(`/admin/pyqs/${pyqId}`, {
      method: "DELETE",
    });
  },
};

// ─────────────────────────────────────────────────────────────────────
// API — SRS  (Smart Retrieval System)
// ─────────────────────────────────────────────────────────────────────

const srs = {
  /**
   * Ask a question and receive a Markdown answer from the SRS pipeline.
   *
   * @param {string} chapterId  – UUID of the chapter to search
   * @param {string} question   – Student's question
   * @param {{ signal?: AbortSignal }} [opts]
   * @returns {Promise<{
   *   question: string,
   *   question_normalised: string,
   *   markdown: string,
   *   chunks_used: number,
   *   images_used: number,
   *   images_replaced: number,
   *   images: Array<{ image_id: string, image_path: string, caption?: string, position_index: number }>
   * }>}
   */
  ask(chapterId, question, opts = {}) {
    return request("/srs/ask", {
      method: "POST",
      json: { question, chapter_id: chapterId },
      signal: opts.signal,
    });
  },
};

// ─────────────────────────────────────────────────────────────────────
// API — Mind Map
// ─────────────────────────────────────────────────────────────────────

const mindmap = {
  /**
   * Get a nested mind-map tree for a chapter.
   *
   * @param {string} chapterId  – UUID
   * @returns {Promise<{
   *   chapter_id: string,
   *   chapter_title: string,
   *   node_count: number,
   *   leaf_count: number,
   *   tree: object
   * }>}
   */
  getTree(chapterId) {
    return request(`/mindmap/${chapterId}`);
  },

  /**
   * Get a flat node list (with parent_id) for a chapter.
   * Useful for React-Flow / graph layouts.
   *
   * @param {string} chapterId  – UUID
   * @returns {Promise<{
   *   chapter_id: string,
   *   chapter_title: string,
   *   nodes: Array<{
   *     id: string,
   *     parent_id: string|null,
   *     label: string,
   *     tag: string,
   *     depth: number,
   *     detail?: string,
   *     figure_ids: string[]
   *   }>
   * }>}
   */
  getFlat(chapterId) {
    return request(`/mindmap/${chapterId}/flat`);
  },

  /**
   * Get chunk position bounds for a chapter.
   * Use this to know valid start/end ranges before calling `getRange()`.
   *
   * @param {string} chapterId  – UUID
   * @returns {Promise<{ chapter_id: string, min_pos: number, max_pos: number, total: number }>}
   */
  getBounds(chapterId) {
    return request(`/mindmap/${chapterId}/bounds`);
  },

  /**
   * Build a nested mind-map from a subset of chunks (by position_index range).
   *
   * @param {string} chapterId  – UUID
   * @param {number} start      – Start position_index (inclusive)
   * @param {number} end        – End position_index (inclusive)
   * @returns {Promise<{
   *   chapter_id: string, chapter_title: string,
   *   node_count: number, leaf_count: number, tree: object
   * }>}
   */
  getRange(chapterId, start, end) {
    return request(`/mindmap/${chapterId}/range`, {
      method: "POST",
      json: { start, end },
    });
  },

  /**
   * Flat node list from a chunk range.
   *
   * @param {string} chapterId  – UUID
   * @param {number} start      – Start position_index (inclusive)
   * @param {number} end        – End position_index (inclusive)
   * @returns {Promise<{
   *   chapter_id: string, chapter_title: string,
   *   nodes: Array<{ id: string, parent_id: string|null, label: string, tag: string, depth: number, detail?: string, figure_ids: string[] }>
   * }>}
   */
  getRangeFlat(chapterId, start, end) {
    return request(`/mindmap/${chapterId}/range/flat`, {
      method: "POST",
      json: { start, end },
    });
  },
};

// ─────────────────────────────────────────────────────────────────────
// API — Analysis
// ─────────────────────────────────────────────────────────────────────

const analysis = {
  /**
   * Get full PYQ analysis for a book (zones, trends, predictions).
   *
   * @param {string} bookId - UUID
   * @param {{ zone_radius?: number, top_k?: number }} [params]
   * @returns {Promise<any>}
   */
  getBookAnalysis(bookId, params = {}) {
    return request(`/analysis/books/${bookId}${qs(params)}`);
  },

  /**
   * Get full PYQ analysis scoped to a single chapter.
   *
   * @param {string} chapterId - UUID
   * @param {{ zone_radius?: number, top_k?: number }} [params]
   * @returns {Promise<any>}
   */
  getChapterAnalysis(chapterId, params = {}) {
    return request(`/analysis/chapters/${chapterId}${qs(params)}`);
  },

  /**
   * Get chart-ready PYQ pattern data for a book.
   * @param {string} bookId - UUID
   * @returns {Promise<any>}
   */
  getBookPatterns(bookId) {
    return request(`/analysis/books/${bookId}/patterns`);
  },

  /**
   * Get chart-ready PYQ pattern data for a chapter.
   * @param {string} chapterId - UUID
   * @returns {Promise<any>}
   */
  getChapterPatterns(chapterId) {
    return request(`/analysis/chapters/${chapterId}/patterns`);
  },
};

// ─────────────────────────────────────────────────────────────────────
// API — Quiz
// ─────────────────────────────────────────────────────────────────────

const quiz = {
  /**
   * Generate an MCQ quiz for a chapter.
   *
   * @param {string} chapterId - UUID
   * @param {{ forceNew?: boolean }} [opts]
   * @returns {Promise<Array<{
   *   id: number,
   *   question: string,
   *   options: string[],
   *   correct: number,
   *   explanation: string,
   *   topic: string
   * }>>}
   */
  generate(chapterId, opts = {}) {
    const query = opts.forceNew ? "?force_new=true" : "";
    return request(`/quiz/generate${query}`, {
      method: "POST",
      json: { chapter_id: chapterId },
    });
  },

  /**
   * Submit quiz answers and receive performance analytics.
   *
   * @param {string} chapterId - UUID
   * @param {Array<{ question_id: number, selected: number }>} answers
   * @returns {Promise<{
   *   score: number, total: number, accuracy: number,
   *   strengths: string[], weak_topics: Record<string, number>,
   *   insights: string[], attempt_number: number,
   *   per_question: Array<{
   *     question_id: number, question: string, selected: number,
   *     correct: number, is_correct: boolean, topic: string,
   *     explanation: string, options: string[]
   *   }>
   * }>}
   */
  submit(chapterId, answers) {
    return request("/quiz/submit", {
      method: "POST",
      json: { chapter_id: chapterId, answers },
    });
  },

  /**
   * Generate an adaptive quiz focused on weak areas (~70% weak, ~30% other).
   *
   * @param {string} chapterId - UUID
   * @returns {Promise<Array<{
   *   id: number, question: string, options: string[],
   *   correct: number, explanation: string, topic: string
   * }>>}
   */
  generateAdaptive(chapterId) {
    return request("/quiz/generate-adaptive", {
      method: "POST",
      json: { chapter_id: chapterId },
    });
  },
};

// ─────────────────────────────────────────────────────────────────────
// Public surface
// ─────────────────────────────────────────────────────────────────────

const admin = {
  /**
   * Verify basic auth credentials.
   */
  verify() {
    return adminRequest("/admin/verify");
  }
};

export const api = {
  health,
  admin,
  catalog,
  books,
  chapters,
  pyqs,
  srs,
  mindmap,
  analysis,
  quiz,
};

export default api;
