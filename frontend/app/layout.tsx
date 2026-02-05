"use client";
import "./globals.css";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient());
  return (
    <html lang="en">
      <body className="bg-gray-50 text-gray-900 min-h-screen">
        <QueryClientProvider client={queryClient}>
          <nav className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
            <h1 className="text-lg font-semibold">Invoice Extraction Review</h1>
            <a href="/queue" className="text-blue-600 hover:text-blue-800 text-sm">Review Queue</a>
          </nav>
          <main>{children}</main>
        </QueryClientProvider>
      </body>
    </html>
  );
}
