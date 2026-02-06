"use client";

import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { LLMCallListItem, LLMCallFull, LLMCallStats } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const STAGE_LABELS: Record<string, string> = {
  pass05_classification: "Classification",
  pass1a_extraction: "Extraction 1A",
  pass1b_extraction: "Extraction 1B",
  pass2_schema_mapping: "Schema Mapping",
  pass4_audit: "Audit",
};

const STAGE_COLORS: Record<string, string> = {
  pass05_classification: "bg-purple-100 text-purple-800",
  pass1a_extraction: "bg-blue-100 text-blue-800",
  pass1b_extraction: "bg-cyan-100 text-cyan-800",
  pass2_schema_mapping: "bg-green-100 text-green-800",
  pass4_audit: "bg-orange-100 text-orange-800",
};

export default function LLMCallsPage() {
  const searchParams = useSearchParams();
  const [calls, setCalls] = useState<LLMCallListItem[]>([]);
  const [stats, setStats] = useState<LLMCallStats | null>(null);
  const [selectedCall, setSelectedCall] = useState<LLMCallFull | null>(null);
  const [loading, setLoading] = useState(true);
  const [stageFilter, setStageFilter] = useState<string>("");
  const [modelFilter, setModelFilter] = useState<string>("");
  const [extractionFilter, setExtractionFilter] = useState<string>("");
  const [initialized, setInitialized] = useState(false);

  // Initialize extraction filter from URL params
  useEffect(() => {
    const extractionId = searchParams.get("extraction_id");
    if (extractionId) {
      setExtractionFilter(extractionId);
    }
    setInitialized(true);
  }, [searchParams]);

  useEffect(() => {
    if (!initialized) return;
    fetchCalls();
    fetchStats();
  }, [stageFilter, modelFilter, extractionFilter, initialized]);

  async function fetchCalls() {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (stageFilter) params.set("stage", stageFilter);
      if (modelFilter) params.set("model", modelFilter);
      if (extractionFilter) params.set("extraction_id", extractionFilter);

      const res = await fetch(`${API_URL}/llm-calls?${params.toString()}`);
      const data = await res.json();
      setCalls(data.items || []);
    } catch (err) {
      console.error("Failed to fetch LLM calls:", err);
    } finally {
      setLoading(false);
    }
  }

  async function fetchStats() {
    try {
      const res = await fetch(`${API_URL}/llm-calls/stats`);
      const data = await res.json();
      setStats(data);
    } catch (err) {
      console.error("Failed to fetch stats:", err);
    }
  }

  async function viewCallDetails(callId: string) {
    try {
      const res = await fetch(`${API_URL}/llm-calls/${callId}`);
      const data = await res.json();
      setSelectedCall(data);
    } catch (err) {
      console.error("Failed to fetch call details:", err);
    }
  }

  function formatDuration(ms: number | null) {
    if (ms === null) return "-";
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  }

  function formatTokens(tokens: number | null) {
    if (tokens === null) return "-";
    if (tokens >= 1000) return `${(tokens / 1000).toFixed(1)}k`;
    return tokens.toString();
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">LLM Calls</h1>
            <p className="text-sm text-gray-500">
              {extractionFilter ? (
                <>
                  Showing calls for extraction{" "}
                  <code className="bg-gray-100 px-1 rounded text-xs">{extractionFilter.slice(0, 8)}...</code>
                  {" · "}
                  <Link href={`/review/${extractionFilter}`} className="text-blue-600 hover:underline">
                    Back to extraction
                  </Link>
                  {" · "}
                  <button
                    onClick={() => setExtractionFilter("")}
                    className="text-blue-600 hover:underline"
                  >
                    Show all
                  </button>
                </>
              ) : (
                "Troubleshoot pipeline LLM interactions"
              )}
            </p>
          </div>
          <nav className="flex gap-4">
            <Link href="/" className="text-gray-600 hover:text-gray-900">Dashboard</Link>
            <Link href="/invoices" className="text-gray-600 hover:text-gray-900">Invoices</Link>
            <Link href="/corrections" className="text-gray-600 hover:text-gray-900">Learning</Link>
          </nav>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-gray-500">Total Calls</div>
              <div className="text-2xl font-bold">{stats.total_calls}</div>
            </div>
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-gray-500">By Stage</div>
              <div className="text-xs mt-2 space-y-1">
                {Object.entries(stats.by_stage).map(([stage, data]) => (
                  <div key={stage} className="flex justify-between">
                    <span className="text-gray-600">{STAGE_LABELS[stage] || stage}</span>
                    <span className="font-medium">{data.count}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-gray-500">By Model</div>
              <div className="text-xs mt-2 space-y-1">
                {Object.entries(stats.by_model).map(([model, data]) => (
                  <div key={model} className="flex justify-between">
                    <span className="text-gray-600 truncate max-w-[120px]" title={model}>{model}</span>
                    <span className="font-medium">{data.count}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-gray-500">Total Tokens</div>
              <div className="text-2xl font-bold">
                {formatTokens(Object.values(stats.by_model).reduce((sum, m) => sum + m.total_tokens, 0))}
              </div>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="bg-white rounded-lg shadow p-4 mb-6">
          <div className="flex flex-wrap gap-4">
            <div>
              <label className="block text-sm text-gray-500 mb-1">Stage</label>
              <select
                value={stageFilter}
                onChange={(e) => setStageFilter(e.target.value)}
                className="border rounded px-3 py-1.5 text-sm"
              >
                <option value="">All Stages</option>
                <option value="pass05_classification">Classification</option>
                <option value="pass1a_extraction">Extraction 1A</option>
                <option value="pass1b_extraction">Extraction 1B</option>
                <option value="pass2_schema_mapping">Schema Mapping</option>
                <option value="pass4_audit">Audit</option>
              </select>
            </div>
            <div>
              <label className="block text-sm text-gray-500 mb-1">Model</label>
              <select
                value={modelFilter}
                onChange={(e) => setModelFilter(e.target.value)}
                className="border rounded px-3 py-1.5 text-sm"
              >
                <option value="">All Models</option>
                <option value="gpt-4o">GPT-4o</option>
                <option value="claude-sonnet-4-5-20250929">Claude Sonnet</option>
                <option value="claude-haiku-4-5-20251001">Claude Haiku</option>
              </select>
            </div>
            <div>
              <label className="block text-sm text-gray-500 mb-1">Extraction ID</label>
              <input
                type="text"
                placeholder="Filter by extraction..."
                value={extractionFilter}
                onChange={(e) => setExtractionFilter(e.target.value)}
                className="border rounded px-3 py-1.5 text-sm w-64"
              />
            </div>
          </div>
        </div>

        {/* Calls Table */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Stage</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Model</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Provider</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Images</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tokens</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Duration</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Time</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {loading ? (
                <tr>
                  <td colSpan={9} className="px-4 py-8 text-center text-gray-500">Loading...</td>
                </tr>
              ) : calls.length === 0 ? (
                <tr>
                  <td colSpan={9} className="px-4 py-8 text-center text-gray-500">No LLM calls found</td>
                </tr>
              ) : (
                calls.map((call) => (
                  <tr key={call.call_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${STAGE_COLORS[call.stage] || "bg-gray-100 text-gray-800"}`}>
                        {STAGE_LABELS[call.stage] || call.stage}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-900 font-mono truncate max-w-[150px]" title={call.model}>
                      {call.model}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">{call.provider}</td>
                    <td className="px-4 py-3 text-sm">
                      {call.has_images ? (
                        <span className="text-blue-600">{call.image_count} img</span>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm font-mono">
                      <span className="text-green-600" title="Input tokens">{formatTokens(call.input_tokens)}</span>
                      <span className="text-gray-400"> / </span>
                      <span className="text-blue-600" title="Output tokens">{formatTokens(call.output_tokens)}</span>
                    </td>
                    <td className="px-4 py-3 text-sm font-mono text-gray-600">
                      {formatDuration(call.duration_ms)}
                    </td>
                    <td className="px-4 py-3">
                      {call.error_message ? (
                        <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">Error</span>
                      ) : (
                        <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">Success</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {call.created_at ? new Date(call.created_at).toLocaleTimeString() : "-"}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => viewCallDetails(call.call_id)}
                        className="text-blue-600 hover:text-blue-800 text-sm"
                      >
                        View
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Call Details Modal */}
        {selectedCall && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
              <div className="px-6 py-4 border-b flex justify-between items-center">
                <div>
                  <h2 className="text-lg font-bold">LLM Call Details</h2>
                  <p className="text-sm text-gray-500">
                    {STAGE_LABELS[selectedCall.stage] || selectedCall.stage} - {selectedCall.model}
                  </p>
                </div>
                <button
                  onClick={() => setSelectedCall(null)}
                  className="text-gray-400 hover:text-gray-600 text-2xl"
                >
                  &times;
                </button>
              </div>

              <div className="overflow-y-auto flex-1 p-6 space-y-6">
                {/* Metadata */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <div className="text-xs text-gray-500 uppercase">Model</div>
                    <div className="font-mono text-sm">{selectedCall.model}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500 uppercase">Provider</div>
                    <div className="text-sm">{selectedCall.provider}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500 uppercase">Duration</div>
                    <div className="text-sm font-mono">{formatDuration(selectedCall.duration_ms)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500 uppercase">Tokens</div>
                    <div className="text-sm font-mono">
                      {formatTokens(selectedCall.input_tokens)} in / {formatTokens(selectedCall.output_tokens)} out
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500 uppercase">Temperature</div>
                    <div className="text-sm font-mono">{selectedCall.temperature ?? "-"}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500 uppercase">Max Tokens</div>
                    <div className="text-sm font-mono">{selectedCall.max_tokens ?? "-"}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500 uppercase">Images</div>
                    <div className="text-sm">{selectedCall.has_images ? `${selectedCall.image_count} images` : "None"}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500 uppercase">Extraction</div>
                    <div className="text-sm font-mono truncate">{selectedCall.extraction_id || "-"}</div>
                  </div>
                </div>

                {/* Error Message */}
                {selectedCall.error_message && (
                  <div className="bg-red-50 border border-red-200 rounded p-4">
                    <div className="text-xs text-red-600 uppercase font-medium mb-1">Error</div>
                    <pre className="text-sm text-red-800 whitespace-pre-wrap">{selectedCall.error_message}</pre>
                  </div>
                )}

                {/* System Prompt */}
                <div>
                  <div className="text-xs text-gray-500 uppercase font-medium mb-2">System Prompt</div>
                  <div className="bg-gray-50 border rounded p-4 max-h-48 overflow-y-auto">
                    <pre className="text-sm whitespace-pre-wrap font-mono">{selectedCall.system_prompt || "(none)"}</pre>
                  </div>
                </div>

                {/* User Prompt */}
                <div>
                  <div className="text-xs text-gray-500 uppercase font-medium mb-2">User Prompt</div>
                  <div className="bg-blue-50 border border-blue-200 rounded p-4 max-h-64 overflow-y-auto">
                    <pre className="text-sm whitespace-pre-wrap font-mono">{selectedCall.user_prompt}</pre>
                  </div>
                </div>

                {/* Response */}
                <div>
                  <div className="text-xs text-gray-500 uppercase font-medium mb-2">Response</div>
                  <div className="bg-green-50 border border-green-200 rounded p-4 max-h-96 overflow-y-auto">
                    <pre className="text-sm whitespace-pre-wrap font-mono">{selectedCall.response_content || "(no response)"}</pre>
                  </div>
                </div>
              </div>

              <div className="px-6 py-4 border-t flex justify-end">
                <button
                  onClick={() => setSelectedCall(null)}
                  className="px-4 py-2 bg-gray-200 text-gray-800 rounded hover:bg-gray-300"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
