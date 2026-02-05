"use client";
import { useState, useRef } from "react";
import { getExtractionImageUrl } from "@/lib/api";

interface InvoiceViewerProps {
  extractionId: string;
  pageCount: number;
}

export function InvoiceViewer({ extractionId, pageCount }: InvoiceViewerProps) {
  const [currentPage, setCurrentPage] = useState(1);
  const [zoom, setZoom] = useState(1.0);
  const containerRef = useRef<HTMLDivElement>(null);

  const imageUrl = getExtractionImageUrl(extractionId, currentPage);

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-100 border-b text-sm">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={currentPage <= 1}
            className="px-2 py-1 bg-white border rounded disabled:opacity-40"
          >
            Prev
          </button>
          <span>
            Page {currentPage} of {pageCount}
          </span>
          <button
            onClick={() => setCurrentPage((p) => Math.min(pageCount, p + 1))}
            disabled={currentPage >= pageCount}
            className="px-2 py-1 bg-white border rounded disabled:opacity-40"
          >
            Next
          </button>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setZoom((z) => Math.max(0.25, z - 0.25))} className="px-2 py-1 bg-white border rounded">
            -
          </button>
          <span>{Math.round(zoom * 100)}%</span>
          <button onClick={() => setZoom((z) => Math.min(3, z + 0.25))} className="px-2 py-1 bg-white border rounded">
            +
          </button>
          <button onClick={() => setZoom(1.0)} className="px-2 py-1 bg-white border rounded text-xs">
            Reset
          </button>
        </div>
      </div>

      {/* Image viewer */}
      <div ref={containerRef} className="flex-1 overflow-auto bg-gray-200 p-4">
        <div style={{ transform: `scale(${zoom})`, transformOrigin: "top left" }}>
          <img
            src={imageUrl}
            alt={`Invoice page ${currentPage}`}
            className="bg-white shadow-lg max-w-none"
            style={{ width: "100%" }}
          />
        </div>
      </div>
    </div>
  );
}
