"use client";
import { useState } from "react";
import { ConfidenceBadge } from "./ConfidenceBadge";
import type { ConfidentValue, CorrectionInput } from "@/lib/types";

interface FieldEditorProps {
  label: string;
  fieldPath: string;
  field: ConfidentValue | null | undefined;
  onCorrection: (correction: CorrectionInput) => void;
}

export function FieldEditor({ label, fieldPath, field, onCorrection }: FieldEditorProps) {
  const [editing, setEditing] = useState(false);
  const [editValue, setEditValue] = useState("");

  if (!field) return null;

  const borderColor =
    field.confidence >= 0.9 ? "border-green-200" :
    field.confidence >= 0.7 ? "border-yellow-200" :
    "border-red-300";

  const handleSave = () => {
    if (editValue && editValue !== String(field.value)) {
      onCorrection({
        field_path: fieldPath,
        extracted_value: String(field.value),
        corrected_value: editValue,
        correction_type: "value_change",
      });
    }
    setEditing(false);
  };

  return (
    <div className={`border rounded p-2 ${borderColor}`}>
      <div className="flex items-center justify-between mb-1">
        <label className="text-xs font-medium text-gray-500">{label}</label>
        <ConfidenceBadge confidence={field.confidence} />
      </div>

      {editing ? (
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
          <span className="text-sm font-mono">{String(field.value) || "\u2014"}</span>
          <button
            onClick={() => { setEditValue(String(field.value)); setEditing(true); }}
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
