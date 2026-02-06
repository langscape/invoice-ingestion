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
            <a href="/" className="text-lg font-semibold hover:text-gray-700">Invoice Extraction</a>
            <div className="flex items-center gap-6">
              <a href="/upload" className="text-blue-600 hover:text-blue-800 text-sm font-medium">Upload</a>
              <a href="/invoices" className="text-blue-600 hover:text-blue-800 text-sm">All Invoices</a>
              <a href="/queue" className="text-blue-600 hover:text-blue-800 text-sm">Review Queue</a>
              <a href="/corrections" className="text-blue-600 hover:text-blue-800 text-sm">Learning Rules</a>
            </div>
          </nav>
          <main>{children}</main>
        </QueryClientProvider>
      </body>
    </html>
  );
}
