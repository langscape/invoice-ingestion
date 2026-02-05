import type { CorrectionInput, ExtractionListItem } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchJSON<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export async function fetchExtractions(params?: Record<string, string>) {
  const query = params ? "?" + new URLSearchParams(params).toString() : "";
  return fetchJSON<{ items: ExtractionListItem[]; offset: number; limit: number }>(`/extractions${query}`);
}

export async function fetchExtraction(id: string) {
  return fetchJSON<ExtractionListItem>(`/extractions/${id}`);
}

export async function fetchReviewQueue(params?: Record<string, string>) {
  const query = params ? "?" + new URLSearchParams(params).toString() : "";
  return fetchJSON<{ items: ExtractionListItem[]; offset: number; limit: number }>(`/review/queue${query}`);
}

export async function fetchQueueStats() {
  return fetchJSON<{ counts_by_tier: Record<string, number> }>("/review/queue/stats");
}

export async function submitCorrections(extractionId: string, corrections: CorrectionInput[]) {
  return fetchJSON<{ correction_ids: string[]; count: number }>(`/review/${extractionId}/corrections`, {
    method: "POST",
    body: JSON.stringify({ corrections }),
  });
}

export async function approveExtraction(extractionId: string) {
  return fetchJSON<{ status: string }>(`/review/${extractionId}/approve`, { method: "POST" });
}

export async function approveAllGreen(extractionId: string) {
  return fetchJSON<{ status: string }>(`/review/${extractionId}/approve-all-green`, { method: "POST" });
}

export function getExtractionPdfUrl(extractionId: string): string {
  return `${API_BASE}/extractions/${extractionId}/pdf`;
}

export function getExtractionImageUrl(extractionId: string, page: number): string {
  return `${API_BASE}/extractions/${extractionId}/images/${page}`;
}
