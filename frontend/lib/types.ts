export interface ExtractionListItem {
  extraction_id: string;
  blob_name: string;
  confidence_score: number | null;
  confidence_tier: string | null;
  commodity_type: string | null;
  utility_provider: string | null;
  created_at: string | null;
  status: string;
  result?: ExtractionResult | null;
}

export interface ExtractionResult {
  extraction_metadata: ExtractionMetadata;
  classification: Classification;
  invoice: Invoice;
  account: Account;
  meters: Meter[];
  charges: Charge[];
  totals: Totals;
  validation?: Validation | null;
  traceability: TraceabilityEntry[];
}

export interface ExtractionMetadata {
  extraction_id: string;
  extraction_timestamp: string;
  pipeline_version: string;
  overall_confidence: number;
  confidence_tier: string;
  flags: string[];
  processing_time_ms: number;
  source_document: SourceDocument;
  locale_context?: LocaleContext | null;
}

export interface SourceDocument {
  file_hash: string;
  file_type: string;
  page_count: number;
  ocr_applied: boolean;
  image_quality_score: number;
  language_detected: string;
}

export interface LocaleContext {
  country_code: string | null;
  language: string;
  currency: CurrencyInfo;
}

export interface CurrencyInfo {
  code: string;
  symbol: string;
}

export interface Classification {
  commodity_type: string;
  commodity_confidence: number;
  complexity_tier: string;
  complexity_signals: string[];
  market_type: string;
  has_supplier_split: boolean;
  has_demand_charges: boolean;
  has_tou: boolean;
  has_net_metering: boolean;
  estimated_line_item_count: number;
  format_fingerprint: string;
}

export interface ConfidentValue<T = string> {
  value: T;
  confidence: number;
  source_location?: string | null;
}

export interface MonetaryAmount {
  value: number;
  currency: string;
  original_string?: string | null;
  confidence: number;
}

export interface Invoice {
  invoice_number: ConfidentValue<string>;
  invoice_date: ConfidentValue<string>;
  due_date: ConfidentValue<string>;
  billing_period?: {
    start: ConfidentValue<string>;
    end: ConfidentValue<string>;
    days: number;
  };
  rate_schedule?: ConfidentValue<string> | null;
  statement_type: string;
}

export interface Account {
  account_number: ConfidentValue<string>;
  customer_name: ConfidentValue<string>;
  service_address: ConfidentValue<string>;
  billing_address?: ConfidentValue<string> | null;
  utility_provider: ConfidentValue<string>;
  supplier?: ConfidentValue<string> | null;
}

export interface Meter {
  meter_number: ConfidentValue<string>;
  read_type: string;
  consumption: {
    raw_value: number;
    raw_unit: string;
    normalized_value?: number | null;
    normalized_unit?: string | null;
  };
  demand?: {
    value: number;
    unit: string;
    demand_type: string;
  } | null;
  tou_breakdown?: TOUPeriod[] | null;
}

export interface TOUPeriod {
  period: string;
  consumption: { value: number; unit: string };
  demand?: { value: number; unit: string } | null;
}

export interface Charge {
  line_id: string;
  description: ConfidentValue<string>;
  category: string;
  charge_owner: string;
  charge_section: string;
  quantity?: { value: number; unit: string } | null;
  rate?: { value: number; unit: string } | null;
  amount: MonetaryAmount;
  math_check?: {
    expected_amount: number;
    matches_stated: boolean;
    variance: number;
  } | null;
  vat_rate?: number | null;
  vat_amount?: MonetaryAmount | null;
}

export interface Totals {
  supply_subtotal?: MonetaryAmount | null;
  distribution_subtotal?: MonetaryAmount | null;
  taxes_subtotal?: MonetaryAmount | null;
  current_charges?: MonetaryAmount | null;
  total_amount_due?: MonetaryAmount | null;
  previous_balance?: MonetaryAmount | null;
  payments_received?: MonetaryAmount | null;
  minimum_bill_applied: boolean;
  vat_summary?: VATSummaryEntry[] | null;
  total_net?: MonetaryAmount | null;
  total_vat?: MonetaryAmount | null;
  total_gross?: MonetaryAmount | null;
}

export interface VATSummaryEntry {
  vat_rate: number;
  vat_category: string;
  taxable_base: MonetaryAmount;
  vat_amount: MonetaryAmount;
}

export interface Validation {
  math_results: {
    line_items_sum_valid: boolean;
    section_subtotals_valid: boolean;
    notes: string[];
  };
  logic_checks: {
    commodity_unit_consistency: boolean;
    billing_period_reasonable: boolean;
    notes: string[];
  };
  overall_math_disposition: string;
}

export interface TraceabilityEntry {
  field: string;
  value: unknown;
  reasoning: string;
  source_pages: number[];
  extraction_pass: string;
}

export type CorrectionCategory =
  | "ocr_error"
  | "format_normalize"
  | "wrong_on_document"
  | "missing_context"
  | "calculation_error"
  | "other";

export const CORRECTION_CATEGORY_LABELS: Record<CorrectionCategory, string> = {
  ocr_error: "OCR Error",
  format_normalize: "Format Issue",
  wrong_on_document: "Wrong on Document",
  missing_context: "Missing Context",
  calculation_error: "Calculation Error",
  other: "Other",
};

export const CORRECTION_CATEGORY_DESCRIPTIONS: Record<CorrectionCategory, string> = {
  ocr_error: "OCR misread characters (0/O, 1/l confusion)",
  format_normalize: "Format standardization (trailing chars, spacing)",
  wrong_on_document: "The document itself has an error",
  missing_context: "LLM missed context that changes interpretation",
  calculation_error: "Mathematical or calculation error",
  other: "Other reason",
};

export interface CorrectionInput {
  field_path: string;
  extracted_value?: string | null;
  corrected_value: string;
  correction_type?: string;
  correction_category?: CorrectionCategory | null;
  correction_reason?: string | null;
}

export interface QueueFilters {
  commodityType?: string;
  confidenceTier?: string;
}
