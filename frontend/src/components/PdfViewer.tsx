import { useEffect, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/TextLayer.css";
import "react-pdf/dist/Page/AnnotationLayer.css";

// Bundle the PDF.js worker through Vite so it works offline and in any browser.
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url,
).toString();

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

// Renders the real letter inside the app and highlights the exact quoted line,
// so evidence is traceable without depending on the browser's PDF handling.
export function PdfViewer({
  url,
  filename,
  highlight,
  onClose,
}: {
  url: string;
  filename: string;
  highlight: string;
  onClose: () => void;
}) {
  const [numPages, setNumPages] = useState(0);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const term = highlight.trim();
  const re = term ? new RegExp(`(${escapeRegExp(term)})`, "gi") : null;
  // react-pdf hands each text run to this; return HTML, so we can wrap matches.
  const textRenderer = (item: { str: string }) =>
    re ? item.str.replace(re, "<mark>$1</mark>") : item.str;

  return (
    <div className="pdf-overlay" onClick={onClose}>
      <div className="pdf-modal" onClick={(e) => e.stopPropagation()}>
        <div className="pdf-modal-head">
          <span className="pdf-modal-title">{filename}</span>
          {term && <span className="pdf-modal-hint">highlighting “{term}”</span>}
          <button className="pdf-modal-close" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <div className="pdf-modal-body">
          <Document
            file={url}
            onLoadSuccess={(doc) => setNumPages(doc.numPages)}
            loading={<div className="pdf-status">Loading letter…</div>}
            error={<div className="pdf-status">Could not load the letter.</div>}
          >
            {Array.from({ length: numPages }, (_, i) => (
              <Page
                key={i}
                pageNumber={i + 1}
                width={720}
                customTextRenderer={textRenderer}
                renderAnnotationLayer={false}
              />
            ))}
          </Document>
        </div>
      </div>
    </div>
  );
}
