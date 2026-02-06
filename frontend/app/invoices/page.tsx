"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function reprocessInvoice(extractionId: string): Promise<{ job_id: string }> {
  const res = await fetch(`${API_BASE}/upload/reprocess/${extractionId}`, {
    method: "POST",
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Failed to reprocess");
  }
  return res.json();
}

interface Extraction {
  extraction_id: string;
  blob_name: string;
  confidence_score: number | null;
  confidence_tier: string | null;
  commodity_type: string | null;
  utility_provider: string | null;
  created_at: string | null;
  status: string;
}

async function fetchAllExtractions(params?: Record<string, string>) {
  const query = params ? "?" + new URLSearchParams(params).toString() : "";
  const res = await fetch(`${API_BASE}/extractions${query}`);
  if (!res.ok) throw new Error("Failed to fetch extractions");
  return res.json();
}

export default function InvoicesPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [reprocessingId, setReprocessingId] = useState<string | null>(null);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["extractions", statusFilter],
    queryFn: () => fetchAllExtractions(statusFilter ? { status: statusFilter } : undefined),
    refetchInterval: 5000, // Auto-refresh every 5 seconds
  });

  const reprocessMutation = useMutation({
    mutationFn: reprocessInvoice,
    onSuccess: (data) => {
      alert(`Reprocessing started! Job ID: ${data.job_id}\n\nThe page will refresh automatically when complete.`);
      setReprocessingId(null);
      // Invalidate to trigger refresh
      queryClient.invalidateQueries({ queryKey: ["extractions"] });
    },
    onError: (error: Error) => {
      alert(`Reprocess failed: ${error.message}`);
      setReprocessingId(null);
    },
  });

  const handleReprocess = (extractionId: string) => {
    if (confirm("Reprocess this invoice? This will run the extraction pipeline again with current learning rules.")) {
      setReprocessingId(extractionId);
      reprocessMutation.mutate(extractionId);
    }
  };

  const extractions: Extraction[] = data?.items || [];

  const statusCounts = extractions.reduce((acc, e) => {
    acc[e.status] = (acc[e.status] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">All Invoices</h1>
          <p className="text-gray-600 text-sm mt-1">
            {extractions.length} invoice{extractions.length !== 1 ? "s" : ""} total
          </p>
        </div>
        <button
          onClick={() => router.push("/upload")}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Upload New
        </button>
      </div>

      {/* Status Summary */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
        <StatusCard
          label="All"
          count={extractions.length}
          active={statusFilter === ""}
          onClick={() => setStatusFilter("")}
          color="gray"
        />
        <StatusCard
          label="Processing"
          count={statusCounts["processing"] || 0}
          active={statusFilter === "processing"}
          onClick={() => setStatusFilter("processing")}
          color="blue"
        />
        <StatusCard
          label="Pending Review"
          count={statusCounts["pending_review"] || 0}
          active={statusFilter === "pending_review"}
          onClick={() => setStatusFilter("pending_review")}
          color="yellow"
        />
        <StatusCard
          label="Reviewed"
          count={statusCounts["reviewed"] || 0}
          active={statusFilter === "reviewed"}
          onClick={() => setStatusFilter("reviewed")}
          color="purple"
        />
        <StatusCard
          label="Accepted"
          count={statusCounts["accepted"] || 0}
          active={statusFilter === "accepted"}
          onClick={() => setStatusFilter("accepted")}
          color="green"
        />
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="text-center py-12 text-gray-500">Loading...</div>
      ) : error ? (
        <div className="text-center py-12 text-red-500">Failed to load invoices</div>
      ) : extractions.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg border">
          <div className="text-4xl mb-4">📄</div>
          <p className="text-gray-600 mb-4">No invoices yet</p>
          <button
            onClick={() => router.push("/upload")}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Upload Your First Invoice
          </button>
        </div>
      ) : (
        <div className="bg-white rounded-lg border overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">File</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Utility</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Commodity</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Confidence</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Created</th>
                <th className="text-right px-4 py-3 text-xs font-medium text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {extractions.map((extraction) => (
                <tr key={extraction.extraction_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <span className="font-mono text-sm truncate block max-w-[200px]" title={extraction.blob_name}>
                      {extraction.blob_name}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {extraction.utility_provider || "—"}
                  </td>
                  <td className="px-4 py-3">
                    <CommodityBadge type={extraction.commodity_type} />
                  </td>
                  <td className="px-4 py-3">
                    <ConfidenceBar score={extraction.confidence_score} tier={extraction.confidence_tier} />
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={extraction.status} />
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {extraction.created_at
                      ? new Date(extraction.created_at).toLocaleString()
                      : "—"}
                  </td>
                  <td className="px-4 py-3 text-right space-x-3">
                    <button
                      onClick={() => router.push(`/review/${extraction.extraction_id}`)}
                      className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                    >
                      View
                    </button>
                    <button
                      onClick={() => router.push(`/llm-calls?extraction_id=${extraction.extraction_id}`)}
                      className="text-gray-500 hover:text-gray-700 text-sm"
                      title="View LLM calls"
                    >
                      LLM
                    </button>
                    <button
                      onClick={() => handleReprocess(extraction.extraction_id)}
                      disabled={reprocessingId === extraction.extraction_id}
                      className="text-orange-600 hover:text-orange-800 text-sm disabled:opacity-50"
                      title="Reprocess with current learning rules"
                    >
                      {reprocessingId === extraction.extraction_id ? "..." : "Reprocess"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function StatusCard({
  label,
  count,
  active,
  onClick,
  color,
}: {
  label: string;
  count: number;
  active: boolean;
  onClick: () => void;
  color: "gray" | "blue" | "yellow" | "purple" | "green";
}) {
  const colors = {
    gray: "border-gray-300 bg-gray-50",
    blue: "border-blue-300 bg-blue-50",
    yellow: "border-yellow-300 bg-yellow-50",
    purple: "border-purple-300 bg-purple-50",
    green: "border-green-300 bg-green-50",
  };

  return (
    <button
      onClick={onClick}
      className={`p-3 rounded-lg border-2 text-left transition-all ${
        active ? `${colors[color]} ring-2 ring-offset-1 ring-blue-500` : "border-gray-200 bg-white hover:border-gray-300"
      }`}
    >
      <div className="text-2xl font-bold">{count}</div>
      <div className="text-xs text-gray-600">{label}</div>
    </button>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    processing: "bg-blue-100 text-blue-700",
    pending_review: "bg-yellow-100 text-yellow-700",
    reviewed: "bg-purple-100 text-purple-700",
    accepted: "bg-green-100 text-green-700",
    rejected: "bg-red-100 text-red-700",
  };

  const labels: Record<string, string> = {
    processing: "Processing",
    pending_review: "Pending Review",
    reviewed: "Reviewed",
    accepted: "Accepted",
    rejected: "Rejected",
  };

  return (
    <span className={`px-2 py-1 rounded text-xs font-medium ${styles[status] || "bg-gray-100 text-gray-700"}`}>
      {labels[status] || status}
    </span>
  );
}

function CommodityBadge({ type }: { type: string | null }) {
  if (!type) return <span className="text-gray-400">—</span>;

  const icons: Record<string, string> = {
    electricity: "⚡",
    natural_gas: "🔥",
    water: "💧",
  };

  return (
    <span className="text-sm">
      {icons[type] || ""} {type.replace("_", " ")}
    </span>
  );
}

function ConfidenceBar({ score, tier }: { score: number | null; tier: string | null }) {
  if (score === null) return <span className="text-gray-400">—</span>;

  const percent = Math.round(score * 100);
  const color =
    percent >= 90 ? "bg-green-500" : percent >= 70 ? "bg-yellow-500" : "bg-red-500";

  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-2 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-full ${color}`} style={{ width: `${percent}%` }} />
      </div>
      <span className="text-xs text-gray-600">{percent}%</span>
    </div>
  );
}
