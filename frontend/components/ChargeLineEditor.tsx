"use client";
import { ConfidenceBadge } from "./ConfidenceBadge";
import type { Charge, CorrectionInput } from "@/lib/types";

interface ChargeLineEditorProps {
  charge: Charge;
  index: number;
  onCorrection: (correction: CorrectionInput) => void;
}

export function ChargeLineEditor({ charge, index, onCorrection }: ChargeLineEditorProps) {
  const mathFailed = charge.math_check && !charge.math_check.matches_stated;
  const borderClass = mathFailed ? "border-red-300 bg-red-50" : "border-gray-200";

  return (
    <div className={`border rounded p-3 text-sm ${borderClass}`}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-medium truncate">{charge.description?.value || "\u2014"}</span>
            <ConfidenceBadge confidence={charge.description?.confidence || 0} />
          </div>
          <div className="flex gap-4 text-xs text-gray-500">
            <span>{charge.category}</span>
            <span>{charge.charge_section}</span>
            <span>{charge.charge_owner}</span>
          </div>
        </div>

        <div className="text-right shrink-0">
          {charge.quantity && charge.rate && (
            <p className="text-xs text-gray-500">
              {charge.quantity.value} {charge.quantity.unit} x {charge.rate.value} {charge.rate.unit}
            </p>
          )}
          <p className="font-mono font-medium">
            {charge.amount?.currency === "EUR" ? "\u20AC" : "$"}
            {charge.amount?.value?.toFixed(2) || "0.00"}
          </p>
          <ConfidenceBadge confidence={charge.amount?.confidence || 0} />
        </div>
      </div>

      {mathFailed && charge.math_check && (
        <div className="mt-2 text-xs text-red-700 bg-red-100 p-2 rounded">
          Math check failed: expected {charge.math_check.expected_amount.toFixed(2)},
          variance {charge.math_check.variance.toFixed(2)}
        </div>
      )}

      {charge.vat_rate != null && (
        <div className="mt-1 text-xs text-gray-500">
          VAT: {(charge.vat_rate * 100).toFixed(0)}%
          {charge.vat_amount && ` (${charge.vat_amount.currency} ${charge.vat_amount.value.toFixed(2)})`}
        </div>
      )}
    </div>
  );
}
