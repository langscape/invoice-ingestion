"use client";
import { useParams, useRouter } from "next/navigation";
import { useExtraction } from "@/hooks/useExtraction";
import { InvoiceViewer } from "@/components/InvoiceViewer";
import { ExtractionPanel } from "@/components/ExtractionPanel";
import { useState, useCallback } from "react";
import { submitCorrections, approveExtraction } from "@/lib/api";
import type { CorrectionInput } from "@/lib/types";

export default function ReviewPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const { data: extraction, isLoading, error } = useExtraction(id);
  const [corrections, setCorrections] = useState<CorrectionInput[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleFieldCorrection = useCallback((correction: CorrectionInput) => {
    setCorrections((prev) => {
      const existing = prev.findIndex((c) => c.field_path === correction.field_path);
      if (existing >= 0) {
        const updated = [...prev];
        updated[existing] = correction;
        return updated;
      }
      return [...prev, correction];
    });
  }, []);

  const handleSubmit = async () => {
    if (!corrections.length) return;
    setSubmitting(true);
    try {
      await submitCorrections(id, corrections);
      setSubmitted(true);
    } catch (e) {
      console.error("Failed to submit corrections:", e);
    } finally {
      setSubmitting(false);
    }
  };

  const handleApprove = async () => {
    setSubmitting(true);
    try {
      await approveExtraction(id);
      setSubmitted(true);
    } catch (e) {
      console.error("Failed to approve:", e);
    } finally {
      setSubmitting(false);
    }
  };

  if (isLoading) return <div className="p-6 text-gray-500">Loading extraction...</div>;
  if (error || !extraction) return <div className="p-6 text-red-500">Failed to load extraction</div>;
  if (submitted) return (
    <div className="p-6">
      <div className="bg-green-50 border border-green-200 rounded p-4">
        <p className="text-green-800 font-medium">Review submitted successfully.</p>
        <a href="/queue" className="text-blue-600 hover:underline text-sm mt-2 inline-block">Back to Queue</a>
      </div>
    </div>
  );

  return (
    <div className="flex h-[calc(100vh-53px)]">
      {/* LEFT PANE: PDF Viewer (50%) */}
      <div className="w-1/2 border-r border-gray-200 overflow-hidden">
        <InvoiceViewer
          extractionId={id}
          pageCount={extraction.result?.extraction_metadata?.source_document?.page_count || 1}
        />
      </div>

      {/* RIGHT PANE: Structured Data (50%) */}
      <div className="w-1/2 overflow-y-auto">
        <div className="p-4 border-b border-gray-200 bg-white sticky top-0 z-10 flex items-center justify-between">
          <div>
            <h2 className="font-semibold">Extraction Review</h2>
            <p className="text-sm text-gray-500">
              Confidence: {((extraction.confidence_score || 0) * 100).toFixed(1)}% — {extraction.confidence_tier}
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => router.push(`/llm-calls?extraction_id=${id}`)}
              className="px-4 py-2 bg-gray-100 text-gray-700 rounded text-sm hover:bg-gray-200 border"
            >
              View LLM Calls
            </button>
            <button
              onClick={handleApprove}
              disabled={submitting}
              className="px-4 py-2 bg-green-600 text-white rounded text-sm hover:bg-green-700 disabled:opacity-50"
            >
              Approve All
            </button>
            <button
              onClick={handleSubmit}
              disabled={submitting || !corrections.length}
              className="px-4 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50"
            >
              Submit Corrections ({corrections.length})
            </button>
          </div>
        </div>

        <ExtractionPanel
          extraction={extraction.result}
          onCorrection={handleFieldCorrection}
        />
      </div>
    </div>
  );
}
