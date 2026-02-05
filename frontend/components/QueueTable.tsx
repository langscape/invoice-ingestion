"use client";
import { useRouter } from "next/navigation";
import { ConfidenceBadge } from "./ConfidenceBadge";
import type { ExtractionListItem } from "@/lib/types";

interface QueueTableProps {
  items: ExtractionListItem[];
}

export function QueueTable({ items }: QueueTableProps) {
  const router = useRouter();

  if (!items.length) {
    return <p className="text-gray-500 text-sm">No invoices pending review.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left text-gray-500">
            <th className="py-2 px-3 font-medium">Invoice</th>
            <th className="py-2 px-3 font-medium">Utility</th>
            <th className="py-2 px-3 font-medium">Commodity</th>
            <th className="py-2 px-3 font-medium">Confidence</th>
            <th className="py-2 px-3 font-medium">Tier</th>
            <th className="py-2 px-3 font-medium">Status</th>
            <th className="py-2 px-3 font-medium">Date</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr
              key={item.extraction_id}
              onClick={() => router.push(`/review/${item.extraction_id}`)}
              className="border-b hover:bg-blue-50 cursor-pointer"
            >
              <td className="py-2 px-3 font-mono text-xs">{item.blob_name || item.extraction_id.slice(0, 8)}</td>
              <td className="py-2 px-3">{item.utility_provider || "\u2014"}</td>
              <td className="py-2 px-3 capitalize">{item.commodity_type?.replace("_", " ") || "\u2014"}</td>
              <td className="py-2 px-3">
                {item.confidence_score != null ? (
                  <ConfidenceBadge confidence={item.confidence_score} />
                ) : "\u2014"}
              </td>
              <td className="py-2 px-3">
                <span className={`text-xs px-2 py-0.5 rounded ${
                  item.confidence_tier === "full_review" ? "bg-red-100 text-red-700" :
                  item.confidence_tier === "targeted_review" ? "bg-yellow-100 text-yellow-700" :
                  "bg-green-100 text-green-700"
                }`}>
                  {item.confidence_tier || "\u2014"}
                </span>
              </td>
              <td className="py-2 px-3">
                <span className={`text-xs px-2 py-0.5 rounded ${
                  item.status === "pending_review" ? "bg-orange-100 text-orange-700" :
                  item.status === "accepted" ? "bg-green-100 text-green-700" :
                  "bg-gray-100 text-gray-700"
                }`}>
                  {item.status}
                </span>
              </td>
              <td className="py-2 px-3 text-xs text-gray-500">
                {item.created_at ? new Date(item.created_at).toLocaleDateString() : "\u2014"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
