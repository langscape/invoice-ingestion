"use client";
import { useState } from "react";
import { getExtractionPdfUrl } from "@/lib/api";

interface InvoiceViewerProps {
  extractionId: string;
  pageCount: number;
}

export function InvoiceViewer({ extractionId, pageCount }: InvoiceViewerProps) {
  const [zoom, setZoom] = useState(100);
  const pdfUrl = getExtractionPdfUrl(extractionId);

  return (
    <div className="flex flex-col h-full bg-gray-100">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 bg-white border-b text-sm shrink-0">
        <div className="flex items-center gap-2 text-gray-600">
          <span>PDF Viewer</span>
          <span className="text-gray-400">({pageCount} pages)</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setZoom((z) => Math.max(50, z - 25))}
            className="px-3 py-1.5 bg-gray-50 border border-gray-300 rounded hover:bg-gray-100"
          >
            −
          </button>
          <span className="px-2 text-gray-600 min-w-[4rem] text-center">
            {zoom}%
          </span>
          <button
            onClick={() => setZoom((z) => Math.min(200, z + 25))}
            className="px-3 py-1.5 bg-gray-50 border border-gray-300 rounded hover:bg-gray-100"
          >
            +
          </button>
          <button
            onClick={() => setZoom(100)}
            className="px-3 py-1.5 bg-gray-50 border border-gray-300 rounded hover:bg-gray-100 text-xs"
          >
            Reset
          </button>
          <a
            href={pdfUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="px-3 py-1.5 bg-blue-50 border border-blue-300 rounded hover:bg-blue-100 text-blue-700 text-xs ml-2"
          >
            Open PDF
          </a>
        </div>
      </div>

      {/* PDF embed */}
      <div className="flex-1 overflow-auto p-4">
        <div
          className="mx-auto bg-white shadow-lg"
          style={{
            width: `${zoom}%`,
            height: "100%",
            minHeight: "800px"
          }}
        >
          <iframe
            src={pdfUrl}
            className="w-full h-full border-0"
            title="Invoice PDF"
          />
        </div>
      </div>
    </div>
  );
}
