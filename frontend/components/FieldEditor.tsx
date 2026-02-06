"use client";
import { useState } from "react";
import { ConfidenceBadge } from "./ConfidenceBadge";
import type { ConfidentValue, CorrectionInput, CorrectionCategory } from "@/lib/types";
import { CORRECTION_CATEGORY_LABELS, CORRECTION_CATEGORY_DESCRIPTIONS } from "@/lib/types";

interface FieldEditorProps {
  label: string;
  fieldPath: string;
  field: ConfidentValue | null | undefined;
  onCorrection: (correction: CorrectionInput) => void;
}

// Auto-suggest category based on field and change pattern
function suggestCategory(fieldPath: string, extracted: string, corrected: string): CorrectionCategory {
  // Year change pattern in date fields
  if (fieldPath.includes("date") || fieldPath.includes("period")) {
    const extMatch = extracted.match(/(\d{4})/);
    const corMatch = corrected.match(/(\d{4})/);
    if (extMatch && corMatch && extMatch[1] !== corMatch[1]) {
      return "wrong_on_document";
    }
  }

  // Trailing character removal
  if (extracted.startsWith(corrected) || corrected.length < extracted.length) {
    return "format_normalize";
  }

  // Character confusion (similar length, few differences)
  if (Math.abs(extracted.length - corrected.length) <= 1) {
    return "ocr_error";
  }

  return "other";
}

export function FieldEditor({ label, fieldPath, field, onCorrection }: FieldEditorProps) {
  const [editing, setEditing] = useState(false);
  const [editValue, setEditValue] = useState("");
  const [correctedValue, setCorrectedValue] = useState<string | null>(null);
  const [showCategoryPicker, setShowCategoryPicker] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<CorrectionCategory | null>(null);

  if (!field) return null;

  const displayValue = correctedValue ?? String(field.value);
  const wasCorrected = correctedValue !== null;

  const borderColor = wasCorrected
    ? "border-blue-300 bg-blue-50"
    : field.confidence >= 0.9 ? "border-green-200"
    : field.confidence >= 0.7 ? "border-yellow-200"
    : "border-red-300";

  const handleSave = () => {
    if (editValue && editValue !== String(field.value)) {
      // Show category picker before finalizing
      const suggested = suggestCategory(fieldPath, String(field.value), editValue);
      setSelectedCategory(suggested);
      setShowCategoryPicker(true);
    } else {
      setEditing(false);
    }
  };

  const handleConfirmWithCategory = () => {
    onCorrection({
      field_path: fieldPath,
      extracted_value: String(field.value),
      corrected_value: editValue,
      correction_type: "value_change",
      correction_category: selectedCategory,
    });
    setCorrectedValue(editValue);
    setEditing(false);
    setShowCategoryPicker(false);
  };

  const handleCancelCategory = () => {
    setShowCategoryPicker(false);
    setEditing(false);
  };

  return (
    <div className={`border rounded p-2 ${borderColor}`}>
      <div className="flex items-center justify-between mb-1">
        <label className="text-xs font-medium text-gray-500">
          {label}
          {wasCorrected && <span className="ml-1 text-blue-600">(edited)</span>}
        </label>
        <ConfidenceBadge confidence={field.confidence} />
      </div>

      {showCategoryPicker ? (
        <div className="space-y-2">
          <div className="text-xs text-gray-600 mb-1">
            <span className="font-mono bg-gray-100 px-1">{String(field.value)}</span>
            <span className="mx-1">→</span>
            <span className="font-mono bg-blue-100 px-1">{editValue}</span>
          </div>
          <div className="text-xs font-medium text-gray-700 mb-1">Why this correction?</div>
          <div className="grid grid-cols-2 gap-1">
            {(Object.keys(CORRECTION_CATEGORY_LABELS) as CorrectionCategory[]).map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`text-left px-2 py-1.5 text-xs rounded border ${
                  selectedCategory === cat
                    ? "border-blue-500 bg-blue-50 text-blue-700"
                    : "border-gray-200 hover:border-gray-300"
                }`}
                title={CORRECTION_CATEGORY_DESCRIPTIONS[cat]}
              >
                {CORRECTION_CATEGORY_LABELS[cat]}
              </button>
            ))}
          </div>
          <div className="flex gap-1 mt-2">
            <button
              onClick={handleConfirmWithCategory}
              className="flex-1 px-2 py-1 bg-blue-600 text-white rounded text-xs"
            >
              Confirm
            </button>
            <button
              onClick={handleCancelCategory}
              className="px-2 py-1 bg-gray-200 rounded text-xs"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : editing ? (
        <div className="flex gap-1">
          <input
            type="text"
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            className="flex-1 border rounded px-2 py-1 text-sm"
            autoFocus
          />
          <button onClick={handleSave} className="px-2 py-1 bg-blue-600 text-white rounded text-xs">Save</button>
          <button onClick={() => setEditing(false)} className="px-2 py-1 bg-gray-200 rounded text-xs">Cancel</button>
        </div>
      ) : (
        <div className="flex items-center justify-between">
          <span className="text-sm font-mono">{displayValue || "\u2014"}</span>
          <button
            onClick={() => { setEditValue(displayValue); setEditing(true); }}
            className="text-xs text-blue-600 hover:text-blue-800"
          >
            Edit
          </button>
        </div>
      )}

      {field.source_location && (
        <p className="text-xs text-gray-400 mt-1">{field.source_location}</p>
      )}
    </div>
  );
}
