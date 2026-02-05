"use client";
import type { Totals, CorrectionInput } from "@/lib/types";

interface TotalsSectionProps {
  totals: Totals | null | undefined;
  onCorrection: (correction: CorrectionInput) => void;
}

function AmountRow({ label, amount }: { label: string; amount: { value: number; currency: string } | null | undefined }) {
  if (!amount) return null;
  const symbol = amount.currency === "EUR" ? "\u20AC" : amount.currency === "GBP" ? "\u00A3" : "$";
  return (
    <div className="flex justify-between py-1">
      <span className="text-sm text-gray-600">{label}</span>
      <span className="font-mono text-sm">{symbol}{amount.value.toFixed(2)}</span>
    </div>
  );
}

export function TotalsSection({ totals, onCorrection }: TotalsSectionProps) {
  if (!totals) return <p className="text-sm text-gray-500">No totals data</p>;

  return (
    <div className="space-y-1">
      <AmountRow label="Supply Subtotal" amount={totals.supply_subtotal} />
      <AmountRow label="Distribution Subtotal" amount={totals.distribution_subtotal} />
      <AmountRow label="Taxes Subtotal" amount={totals.taxes_subtotal} />
      <div className="border-t my-2" />
      <AmountRow label="Current Charges" amount={totals.current_charges} />
      <AmountRow label="Previous Balance" amount={totals.previous_balance} />
      <AmountRow label="Payments Received" amount={totals.payments_received} />
      <div className="border-t my-2" />

      {totals.total_net && <AmountRow label="Total Net" amount={totals.total_net} />}
      {totals.total_vat && <AmountRow label="Total VAT" amount={totals.total_vat} />}
      {totals.total_gross && <AmountRow label="Total Gross" amount={totals.total_gross} />}

      <div className="flex justify-between py-2 font-bold border-t-2">
        <span>Total Amount Due</span>
        <span className="font-mono">
          {totals.total_amount_due
            ? `${totals.total_amount_due.currency === "EUR" ? "\u20AC" : "$"}${totals.total_amount_due.value.toFixed(2)}`
            : "\u2014"}
        </span>
      </div>

      {totals.minimum_bill_applied && (
        <p className="text-xs text-yellow-700 bg-yellow-50 p-2 rounded">Minimum bill applied</p>
      )}

      {totals.vat_summary && totals.vat_summary.length > 0 && (
        <div className="mt-3">
          <p className="text-xs font-medium text-gray-500 mb-1">VAT Summary</p>
          {totals.vat_summary.map((entry, i) => (
            <div key={i} className="flex justify-between text-xs bg-gray-50 px-2 py-1 rounded mb-1">
              <span>VAT {(entry.vat_rate * 100).toFixed(0)}% ({entry.vat_category})</span>
              <span>Base: {entry.taxable_base.value.toFixed(2)} → VAT: {entry.vat_amount.value.toFixed(2)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
