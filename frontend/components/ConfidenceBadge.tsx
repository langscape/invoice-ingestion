interface ConfidenceBadgeProps {
  confidence: number;
  size?: "sm" | "md";
}

export function ConfidenceBadge({ confidence, size = "sm" }: ConfidenceBadgeProps) {
  let color: string;
  if (confidence >= 0.9) {
    color = "bg-green-100 text-green-800 border-green-300";
  } else if (confidence >= 0.7) {
    color = "bg-yellow-100 text-yellow-800 border-yellow-300";
  } else {
    color = "bg-red-100 text-red-800 border-red-300";
  }

  const sizeClasses = size === "sm" ? "text-xs px-1.5 py-0.5" : "text-sm px-2 py-1";

  return (
    <span className={`inline-block rounded border font-mono ${color} ${sizeClasses}`}>
      {(confidence * 100).toFixed(0)}%
    </span>
  );
}
