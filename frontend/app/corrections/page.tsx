"use client";
import { useQuery } from "@tanstack/react-query";
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

export default function CorrectionsPage() {
  const [showInactive, setShowInactive] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<string>("");

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
          Correction patterns learned from human reviews
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
            <RuleCard key={rule.field_path} rule={rule} categories={categories} />
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

function RuleCard({ rule, categories }: { rule: Rule; categories: Record<string, string> }) {
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

          <button className="text-gray-400 hover:text-gray-600">
            {expanded ? "▲" : "▼"}
          </button>
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
      {expanded && (
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
    </div>
  );
}
