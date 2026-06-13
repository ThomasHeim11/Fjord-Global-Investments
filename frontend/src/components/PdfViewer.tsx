/**
 * Modal that renders a letter PDF in-app via react-pdf and highlights the
 * quoted evidence line, so findings stay traceable without relying on the
 * browser's PDF handling. Imported lazily by FindingCard to keep the heavy
 * PDF.js bundle out of the initial page load.
 */
import { useEffect, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/TextLayer.css";
import "react-pdf/dist/Page/AnnotationLayer.css";

// Bundle the PDF.js worker through Vite so it works offline and in any browser.
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url,
).toString();

/** Escapes regex metacharacters so the highlight term is matched literally. */
function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * Renders the letter PDF in an overlay modal and wraps the highlight term in
 * <mark> within each text run. Closes on Escape, backdrop click, or the close
 * button.
 */
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
