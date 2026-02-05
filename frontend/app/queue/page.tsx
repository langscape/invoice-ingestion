"use client";
import { useReviewQueue } from "@/hooks/useReviewQueue";
import { QueueTable } from "@/components/QueueTable";
import { useState } from "react";

export default function QueuePage() {
  const [filters, setFilters] = useState<{
    commodityType?: string;
    confidenceTier?: string;
  }>({});

  const { data, isLoading, error } = useReviewQueue(filters);

  return (
    <div className="p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold mb-4">Review Queue</h2>
        <div className="flex gap-4 mb-4">
          <select
            className="border rounded px-3 py-2 text-sm"
            value={filters.commodityType || ""}
            onChange={(e) => setFilters({ ...filters, commodityType: e.target.value || undefined })}
          >
            <option value="">All Commodities</option>
            <option value="electricity">Electricity</option>
            <option value="natural_gas">Natural Gas</option>
            <option value="water">Water</option>
          </select>
          <select
            className="border rounded px-3 py-2 text-sm"
            value={filters.confidenceTier || ""}
            onChange={(e) => setFilters({ ...filters, confidenceTier: e.target.value || undefined })}
          >
            <option value="">All Tiers</option>
            <option value="full_review">Full Review</option>
            <option value="targeted_review">Targeted Review</option>
            <option value="auto_accept">Auto Accept</option>
          </select>
        </div>
      </div>

      {isLoading && <p className="text-gray-500">Loading...</p>}
      {error && <p className="text-red-500">Error loading queue</p>}
      {data && <QueueTable items={data.items} />}
    </div>
  );
}
