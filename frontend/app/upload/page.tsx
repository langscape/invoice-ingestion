"use client";
import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface JobStatus {
  status: "queued" | "processing" | "completed" | "failed";
  filename: string;
  extraction_id?: string;
  confidence?: number;
  confidence_tier?: string;
  error?: string;
}

export default function UploadPage() {
  const router = useRouter();
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  const uploadFile = async (file: File) => {
    setUploading(true);
    setError(null);
    setJobStatus(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${API_BASE}/upload/`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "Upload failed");
      }

      const data = await response.json();
      setJobId(data.job_id);
      setJobStatus({ status: "queued", filename: file.name });

      // Start polling for status
      pollStatus(data.job_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const pollStatus = async (id: string) => {
    const poll = async () => {
      try {
        const response = await fetch(`${API_BASE}/upload/status/${id}`);
        if (response.ok) {
          const data: JobStatus = await response.json();
          setJobStatus(data);

          if (data.status === "queued" || data.status === "processing") {
            setTimeout(poll, 2000); // Poll every 2 seconds
          }
        }
      } catch (e) {
        console.error("Polling error:", e);
      }
    };
    poll();
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const file = e.dataTransfer.files[0];
    if (file && file.type === "application/pdf") {
      uploadFile(file);
    } else {
      setError("Please drop a PDF file");
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      uploadFile(file);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-bold mb-2">Upload Invoice</h1>
        <p className="text-gray-600 mb-6">Upload a PDF invoice for processing</p>

        {/* Drop Zone */}
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors ${
            isDragging
              ? "border-blue-500 bg-blue-50"
              : "border-gray-300 hover:border-gray-400"
          }`}
        >
          {uploading ? (
            <div className="text-gray-600">
              <div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-4"></div>
              <p>Uploading...</p>
            </div>
          ) : (
            <>
              <div className="text-4xl mb-4">📄</div>
              <p className="text-gray-600 mb-4">
                Drag and drop a PDF here, or click to select
              </p>
              <label className="inline-block px-6 py-2 bg-blue-600 text-white rounded cursor-pointer hover:bg-blue-700">
                Select PDF
                <input
                  type="file"
                  accept=".pdf"
                  onChange={handleFileSelect}
                  className="hidden"
                />
              </label>
            </>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded text-red-700">
            {error}
          </div>
        )}

        {/* Job Status */}
        {jobStatus && (
          <div className="mt-6 p-6 bg-white rounded-lg border shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold">Processing Status</h2>
              <StatusBadge status={jobStatus.status} />
            </div>

            <div className="text-sm text-gray-600 mb-2">
              <span className="font-medium">File:</span> {jobStatus.filename}
            </div>

            {jobStatus.status === "processing" && (
              <div className="flex items-center gap-2 text-blue-600">
                <div className="animate-spin w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full"></div>
                <span>Processing invoice...</span>
              </div>
            )}

            {jobStatus.status === "completed" && jobStatus.extraction_id && (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500">Confidence:</span>{" "}
                    <span className="font-medium">
                      {((jobStatus.confidence || 0) * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500">Tier:</span>{" "}
                    <span className="font-medium">{jobStatus.confidence_tier}</span>
                  </div>
                </div>

                <div className="flex gap-2 pt-2">
                  <button
                    onClick={() => router.push(`/review/${jobStatus.extraction_id}`)}
                    className="flex-1 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                  >
                    Review Extraction
                  </button>
                  <button
                    onClick={() => {
                      setJobId(null);
                      setJobStatus(null);
                    }}
                    className="px-4 py-2 bg-gray-100 rounded hover:bg-gray-200"
                  >
                    Upload Another
                  </button>
                </div>
              </div>
            )}

            {jobStatus.status === "failed" && (
              <div className="text-red-600">
                <span className="font-medium">Error:</span> {jobStatus.error}
              </div>
            )}
          </div>
        )}

        {/* Navigation */}
        <div className="mt-8 flex gap-4">
          <button
            onClick={() => router.push("/queue")}
            className="text-blue-600 hover:text-blue-800"
          >
            &larr; View Queue
          </button>
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    queued: "bg-gray-100 text-gray-700",
    processing: "bg-blue-100 text-blue-700",
    completed: "bg-green-100 text-green-700",
    failed: "bg-red-100 text-red-700",
  };

  return (
    <span className={`px-2 py-1 rounded text-xs font-medium ${colors[status] || colors.queued}`}>
      {status}
    </span>
  );
}
