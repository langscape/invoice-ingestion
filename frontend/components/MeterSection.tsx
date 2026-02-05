"use client";
import { ConfidenceBadge } from "./ConfidenceBadge";
import type { Meter, CorrectionInput } from "@/lib/types";

interface MeterSectionProps {
  meter: Meter;
  index: number;
  onCorrection: (correction: CorrectionInput) => void;
}

export function MeterSection({ meter, index, onCorrection }: MeterSectionProps) {
  return (
    <div className="border rounded p-3 mb-3">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="font-medium text-sm">Meter: {meter.meter_number?.value || `#${index + 1}`}</span>
          <ConfidenceBadge confidence={meter.meter_number?.confidence || 0} />
        </div>
        <span className="text-xs px-2 py-0.5 bg-gray-100 rounded">{meter.read_type}</span>
      </div>

      <div className="grid grid-cols-3 gap-3 text-sm">
        <div>
          <p className="text-xs text-gray-500">Consumption</p>
          <p className="font-mono">{meter.consumption?.raw_value} {meter.consumption?.raw_unit}</p>
          {meter.consumption?.normalized_value && (
            <p className="text-xs text-gray-400">= {meter.consumption.normalized_value} {meter.consumption.normalized_unit}</p>
          )}
        </div>

        {meter.demand && (
          <div>
            <p className="text-xs text-gray-500">Demand</p>
            <p className="font-mono">{meter.demand.value} {meter.demand.unit}</p>
            <p className="text-xs text-gray-400">{meter.demand.demand_type}</p>
          </div>
        )}
      </div>

      {meter.tou_breakdown && meter.tou_breakdown.length > 0 && (
        <div className="mt-2">
          <p className="text-xs text-gray-500 mb-1">TOU Breakdown</p>
          <div className="space-y-1">
            {meter.tou_breakdown.map((tou, i) => (
              <div key={i} className="flex justify-between text-xs bg-gray-50 px-2 py-1 rounded">
                <span className="font-medium">{tou.period}</span>
                <span className="font-mono">{tou.consumption.value} {tou.consumption.unit}</span>
                {tou.demand && <span className="font-mono">{tou.demand.value} {tou.demand.unit}</span>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
