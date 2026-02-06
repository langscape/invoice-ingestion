"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Pattern {
  extracted: string;
  corrected: string;
  count: number;
}

interface Rule {
  field_path: string;
  total_corrections: number;
  is_active: boolean;
  category: string;
  category_description: string;
  patterns: Pattern[];
  last_correction: string | null;
}

interface Correction {
  correction_id: string;
  extraction_id: string;
  field_path: string;
  extracted_value: string | null;
  corrected_value: string;
  correction_type: string;
  correction_category: string;
  correction_reason: string | null;
  created_at: string | null;
  context: Record<string, unknown> | null;
}

interface RulesResponse {
  summary: {
    total_corrections: number;
    active_rules: number;
    pending_rules: number;
  };
  rules: Rule[];
  categories: Record<string, string>;
}

async function fetchRules(): Promise<RulesResponse> {
  const res = await fetch(`${API_BASE}/corrections/rules`);
  if (!res.ok) throw new Error("Failed to fetch rules");
  return res.json();
}

async function fetchCorrections(fieldPath?: string): Promise<{ items: Correction[] }> {
  const query = fieldPath ? `?field_path=${encodeURIComponent(fieldPath)}` : "";
  const res = await fetch(`${API_BASE}/corrections${query}`);
  if (!res.ok) throw new Error("Failed to fetch corrections");
  return res.json();
}

async function updateCorrection(
  correctionId: string,
  updates: Partial<Correction>
): Promise<Correction> {
  const res = await fetch(`${API_BASE}/corrections/${correctionId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error("Failed to update correction");
  return res.json();
}

async function deleteCorrection(correctionId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/corrections/${correctionId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete correction");
}

const CATEGORY_OPTIONS = [
  { value: "ocr_error", label: "OCR Error" },
  { value: "format_normalize", label: "Format Issue" },
  { value: "wrong_on_document", label: "Wrong on Document" },
  { value: "missing_context", label: "Missing Context" },
  { value: "calculation_error", label: "Calculation Error" },
  { value: "other", label: "Other" },
];

export default function CorrectionsPage() {
  const queryClient = useQueryClient();
  const [showInactive, setShowInactive] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<string>("");
  const [editingRule, setEditingRule] = useState<string | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ["correction-rules"],
    queryFn: fetchRules,
  });

  const rules = data?.rules || [];
  const summary = data?.summary;
  const categories = data?.categories || {};

  const filteredRules = rules.filter((rule) => {
    if (!showInactive && !rule.is_active) return false;
    if (selectedCategory && rule.category !== selectedCategory) return false;
    return true;
  });

  const uniqueCategories = [...new Set(rules.map((r) => r.category))];

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Learning Rules</h1>
        <p className="text-gray-600 text-sm mt-1">
          Correction patterns learned from human reviews. Click a rule to edit or delete corrections.
        </p>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-white rounded-lg border p-4">
            <div className="text-3xl font-bold text-gray-900">{summary.total_corrections}</div>
            <div className="text-sm text-gray-500">Total Corrections</div>
          </div>
          <div className="bg-white rounded-lg border p-4">
            <div className="text-3xl font-bold text-green-600">{summary.active_rules}</div>
            <div className="text-sm text-gray-500">Active Rules (2+ occurrences)</div>
          </div>
          <div className="bg-white rounded-lg border p-4">
            <div className="text-3xl font-bold text-yellow-600">{summary.pending_rules}</div>
            <div className="text-sm text-gray-500">Pending Rules (1 occurrence)</div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-4 mb-6">
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={showInactive}
            onChange={(e) => setShowInactive(e.target.checked)}
            className="rounded"
          />
          Show pending rules
        </label>

        <select
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
          className="border rounded px-3 py-1.5 text-sm"
        >
          <option value="">All Categories</option>
          {uniqueCategories.map((cat) => (
            <option key={cat} value={cat}>
              {categories[cat] || cat}
            </option>
          ))}
        </select>
      </div>

      {/* Rules List */}
      {isLoading ? (
        <div className="text-center py-12 text-gray-500">Loading...</div>
      ) : error ? (
        <div className="text-center py-12 text-red-500">Failed to load rules</div>
      ) : filteredRules.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg border">
          <div className="text-4xl mb-4">📚</div>
          <p className="text-gray-600">No correction rules yet</p>
          <p className="text-sm text-gray-500 mt-2">
            Rules are learned from human corrections during invoice review
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredRules.map((rule) => (
            <RuleCard
              key={rule.field_path}
              rule={rule}
              categories={categories}
              isEditing={editingRule === rule.field_path}
              onEdit={() => setEditingRule(editingRule === rule.field_path ? null : rule.field_path)}
              onRefresh={() => queryClient.invalidateQueries({ queryKey: ["correction-rules"] })}
            />
          ))}
        </div>
      )}

      {/* Legend */}
      <div className="mt-8 p-4 bg-gray-50 rounded-lg">
        <h3 className="font-medium mb-3">How Learning Works</h3>
        <div className="text-sm text-gray-600 space-y-2">
          <p>
            <span className="inline-block w-3 h-3 rounded-full bg-green-500 mr-2"></span>
            <strong>Active rules</strong> (2+ corrections) are injected into LLM prompts to prevent repeated mistakes.
          </p>
          <p>
            <span className="inline-block w-3 h-3 rounded-full bg-yellow-500 mr-2"></span>
            <strong>Pending rules</strong> (1 correction) need one more occurrence to become active.
          </p>
        </div>
      </div>
    </div>
  );
}

function RuleCard({
  rule,
  categories,
  isEditing,
  onEdit,
  onRefresh,
}: {
  rule: Rule;
  categories: Record<string, string>;
  isEditing: boolean;
  onEdit: () => void;
  onRefresh: () => void;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className={`bg-white rounded-lg border overflow-hidden ${
        rule.is_active ? "border-green-200" : "border-yellow-200"
      }`}
    >
      <div
        className="p-4 cursor-pointer hover:bg-gray-50"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span
                className={`w-2 h-2 rounded-full ${
                  rule.is_active ? "bg-green-500" : "bg-yellow-500"
                }`}
              />
              <code className="text-sm font-mono bg-gray-100 px-2 py-0.5 rounded">
                {rule.field_path}
              </code>
              <span
                className={`px-2 py-0.5 rounded text-xs ${
                  rule.is_active
                    ? "bg-green-100 text-green-700"
                    : "bg-yellow-100 text-yellow-700"
                }`}
              >
                {rule.is_active ? "Active" : "Pending"}
              </span>
            </div>

            <div className="flex items-center gap-4 mt-2 text-sm text-gray-600">
              <span>{rule.total_corrections} correction{rule.total_corrections !== 1 ? "s" : ""}</span>
              <span>•</span>
              <span className="capitalize">{categories[rule.category] || rule.category}</span>
              {rule.last_correction && (
                <>
                  <span>•</span>
                  <span>Last: {new Date(rule.last_correction).toLocaleDateString()}</span>
                </>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onEdit();
              }}
              className="px-3 py-1 text-sm text-blue-600 hover:bg-blue-50 rounded"
            >
              Edit
            </button>
            <button className="text-gray-400 hover:text-gray-600">
              {expanded ? "▲" : "▼"}
            </button>
          </div>
        </div>

        {/* Quick preview of top pattern */}
        {rule.patterns.length > 0 && !expanded && (
          <div className="mt-3 text-sm">
            <span className="text-gray-500">Top pattern: </span>
            <code className="bg-red-50 text-red-700 px-1.5 py-0.5 rounded">
              {rule.patterns[0].extracted || "(empty)"}
            </code>
            <span className="mx-2">→</span>
            <code className="bg-green-50 text-green-700 px-1.5 py-0.5 rounded">
              {rule.patterns[0].corrected}
            </code>
            {rule.patterns.length > 1 && (
              <span className="text-gray-400 ml-2">+{rule.patterns.length - 1} more</span>
            )}
          </div>
        )}
      </div>

      {/* Expanded details */}
      {expanded && !isEditing && (
        <div className="border-t bg-gray-50 p-4">
          <h4 className="text-sm font-medium mb-3">Correction Patterns</h4>
          <div className="space-y-2">
            {rule.patterns.map((pattern, i) => (
              <div key={i} className="flex items-center gap-3 text-sm">
                <code className="bg-red-50 text-red-700 px-2 py-1 rounded font-mono">
                  {pattern.extracted || "(empty)"}
                </code>
                <span className="text-gray-400">→</span>
                <code className="bg-green-50 text-green-700 px-2 py-1 rounded font-mono">
                  {pattern.corrected}
                </code>
                <span className="text-gray-500 text-xs">
                  ({pattern.count}x)
                </span>
              </div>
            ))}
          </div>

          {rule.category_description && (
            <div className="mt-4 p-3 bg-blue-50 rounded text-sm text-blue-800">
              <strong>Why:</strong> {rule.category_description}
            </div>
          )}
        </div>
      )}

      {/* Edit mode */}
      {isEditing && (
        <CorrectionEditor
          fieldPath={rule.field_path}
          onClose={onEdit}
          onRefresh={onRefresh}
        />
      )}
    </div>
  );
}

function CorrectionEditor({
  fieldPath,
  onClose,
  onRefresh,
}: {
  fieldPath: string;
  onClose: () => void;
  onRefresh: () => void;
}) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<Partial<Correction>>({});

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["corrections", fieldPath],
    queryFn: () => fetchCorrections(fieldPath),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, updates }: { id: string; updates: Partial<Correction> }) =>
      updateCorrection(id, updates),
    onSuccess: () => {
      refetch();
      onRefresh();
      setEditingId(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteCorrection,
    onSuccess: () => {
      refetch();
      onRefresh();
    },
  });

  const corrections = data?.items || [];

  const startEdit = (c: Correction) => {
    setEditingId(c.correction_id);
    setEditForm({
      extracted_value: c.extracted_value || "",
      corrected_value: c.corrected_value,
      correction_category: c.correction_category,
      correction_reason: c.correction_reason || "",
    });
  };

  const saveEdit = () => {
    if (!editingId) return;
    updateMutation.mutate({ id: editingId, updates: editForm });
  };

  const handleDelete = (correctionId: string) => {
    if (confirm("Delete this correction? This cannot be undone.")) {
      deleteMutation.mutate(correctionId);
    }
  };

  return (
    <div className="border-t bg-white p-4">
      <div className="flex items-center justify-between mb-4">
        <h4 className="font-medium">Edit Corrections for {fieldPath}</h4>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">
          ×
        </button>
      </div>

      {isLoading ? (
        <div className="text-center py-4 text-gray-500">Loading...</div>
      ) : corrections.length === 0 ? (
        <div className="text-center py-4 text-gray-500">No corrections found</div>
      ) : (
        <div className="space-y-3">
          {corrections.map((c) => (
            <div
              key={c.correction_id}
              className="border rounded-lg p-3 bg-gray-50"
            >
              {editingId === c.correction_id ? (
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">Extracted Value</label>
                      <input
                        type="text"
                        value={editForm.extracted_value || ""}
                        onChange={(e) => setEditForm({ ...editForm, extracted_value: e.target.value })}
                        className="w-full border rounded px-2 py-1 text-sm"
                        placeholder="(empty)"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">Corrected Value</label>
                      <input
                        type="text"
                        value={editForm.corrected_value || ""}
                        onChange={(e) => setEditForm({ ...editForm, corrected_value: e.target.value })}
                        className="w-full border rounded px-2 py-1 text-sm"
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">Category</label>
                      <select
                        value={editForm.correction_category || ""}
                        onChange={(e) => setEditForm({ ...editForm, correction_category: e.target.value })}
                        className="w-full border rounded px-2 py-1 text-sm"
                      >
                        {CATEGORY_OPTIONS.map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">Reason</label>
                      <input
                        type="text"
                        value={editForm.correction_reason || ""}
                        onChange={(e) => setEditForm({ ...editForm, correction_reason: e.target.value })}
                        className="w-full border rounded px-2 py-1 text-sm"
                        placeholder="Optional reason..."
                      />
                    </div>
                  </div>
                  <div className="flex justify-end gap-2">
                    <button
                      onClick={() => setEditingId(null)}
                      className="px-3 py-1 text-sm text-gray-600 hover:bg-gray-200 rounded"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={saveEdit}
                      disabled={updateMutation.isPending}
                      className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                    >
                      {updateMutation.isPending ? "Saving..." : "Save"}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 text-sm">
                      <code className="bg-red-50 text-red-700 px-1.5 py-0.5 rounded">
                        {c.extracted_value || "(empty)"}
                      </code>
                      <span className="text-gray-400">→</span>
                      <code className="bg-green-50 text-green-700 px-1.5 py-0.5 rounded">
                        {c.corrected_value}
                      </code>
                    </div>
                    <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
                      <span className="capitalize">{c.correction_category.replace("_", " ")}</span>
                      {c.correction_reason && (
                        <>
                          <span>•</span>
                          <span>{c.correction_reason}</span>
                        </>
                      )}
                      {c.created_at && (
                        <>
                          <span>•</span>
                          <span>{new Date(c.created_at).toLocaleDateString()}</span>
                        </>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => startEdit(c)}
                      className="p-1 text-blue-600 hover:bg-blue-50 rounded"
                      title="Edit"
                    >
                      ✏️
                    </button>
                    <button
                      onClick={() => handleDelete(c.correction_id)}
                      disabled={deleteMutation.isPending}
                      className="p-1 text-red-600 hover:bg-red-50 rounded disabled:opacity-50"
                      title="Delete"
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
