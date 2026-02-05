"use client";
import type { ExtractionResult, CorrectionInput } from "@/lib/types";
import { FieldEditor } from "./FieldEditor";
import { ChargeLineEditor } from "./ChargeLineEditor";
import { MeterSection } from "./MeterSection";
import { TotalsSection } from "./TotalsSection";

interface ExtractionPanelProps {
  extraction: ExtractionResult | null | undefined;
  onCorrection: (correction: CorrectionInput) => void;
}

export function ExtractionPanel({ extraction, onCorrection }: ExtractionPanelProps) {
  if (!extraction) return <div className="p-4 text-gray-500">No extraction data</div>;

  return (
    <div className="p-4 space-y-6">
      {/* Invoice Details */}
      <section>
        <h3 className="font-semibold text-lg mb-3 border-b pb-1">Invoice Details</h3>
        <div className="grid grid-cols-2 gap-3">
          <FieldEditor label="Invoice Number" fieldPath="invoice.invoice_number" field={extraction.invoice?.invoice_number} onCorrection={onCorrection} />
          <FieldEditor label="Invoice Date" fieldPath="invoice.invoice_date" field={extraction.invoice?.invoice_date} onCorrection={onCorrection} />
          <FieldEditor label="Due Date" fieldPath="invoice.due_date" field={extraction.invoice?.due_date} onCorrection={onCorrection} />
          <FieldEditor label="Statement Type" fieldPath="invoice.statement_type" field={{ value: extraction.invoice?.statement_type || "", confidence: 1.0 }} onCorrection={onCorrection} />
          {extraction.invoice?.billing_period && (
            <>
              <FieldEditor label="Billing Start" fieldPath="invoice.billing_period.start" field={extraction.invoice.billing_period.start} onCorrection={onCorrection} />
              <FieldEditor label="Billing End" fieldPath="invoice.billing_period.end" field={extraction.invoice.billing_period.end} onCorrection={onCorrection} />
            </>
          )}
          <FieldEditor label="Rate Schedule" fieldPath="invoice.rate_schedule" field={extraction.invoice?.rate_schedule} onCorrection={onCorrection} />
        </div>
      </section>

      {/* Account Information */}
      <section>
        <h3 className="font-semibold text-lg mb-3 border-b pb-1">Account</h3>
        <div className="grid grid-cols-2 gap-3">
          <FieldEditor label="Account Number" fieldPath="account.account_number" field={extraction.account?.account_number} onCorrection={onCorrection} />
          <FieldEditor label="Customer Name" fieldPath="account.customer_name" field={extraction.account?.customer_name} onCorrection={onCorrection} />
          <FieldEditor label="Service Address" fieldPath="account.service_address" field={extraction.account?.service_address} onCorrection={onCorrection} />
          <FieldEditor label="Utility Provider" fieldPath="account.utility_provider" field={extraction.account?.utility_provider} onCorrection={onCorrection} />
          {extraction.account?.supplier && (
            <FieldEditor label="Supplier" fieldPath="account.supplier" field={extraction.account.supplier} onCorrection={onCorrection} />
          )}
        </div>
      </section>

      {/* Meters */}
      {extraction.meters?.length > 0 && (
        <section>
          <h3 className="font-semibold text-lg mb-3 border-b pb-1">Meters ({extraction.meters.length})</h3>
          {extraction.meters.map((meter, i) => (
            <MeterSection key={i} meter={meter} index={i} onCorrection={onCorrection} />
          ))}
        </section>
      )}

      {/* Charges */}
      <section>
        <h3 className="font-semibold text-lg mb-3 border-b pb-1">Charges ({extraction.charges?.length || 0})</h3>
        <div className="space-y-2">
          {extraction.charges?.map((charge, i) => (
            <ChargeLineEditor key={charge.line_id || i} charge={charge} index={i} onCorrection={onCorrection} />
          ))}
        </div>
      </section>

      {/* Totals */}
      <section>
        <h3 className="font-semibold text-lg mb-3 border-b pb-1">Totals</h3>
        <TotalsSection totals={extraction.totals} onCorrection={onCorrection} />
      </section>

      {/* Validation Summary */}
      {extraction.validation && (
        <section>
          <h3 className="font-semibold text-lg mb-3 border-b pb-1">Validation</h3>
          <div className="text-sm space-y-1">
            <p>Math disposition: <span className="font-mono">{extraction.validation.overall_math_disposition}</span></p>
            {extraction.validation.math_results?.notes?.map((note, i) => (
              <p key={i} className="text-yellow-700">{note}</p>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
