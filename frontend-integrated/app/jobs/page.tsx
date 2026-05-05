"use client";

import { Suspense } from "react";
import { Header } from "@/components/Header";
import { Navigation } from "@/components/Navigation";
import { JobsFeedScreen } from "@/components/screens/JobsFeedScreen";
import { useSearchParams } from "next/navigation";

function JobsContent() {
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get("q") || "";

  return <JobsFeedScreen initialSearchQuery={initialQuery} />;
}

export default function JobsPage() {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Header />
      <main className="flex-1 pb-24 lg:pb-0">
        <div className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 py-4 sm:py-8">
          <Suspense fallback={<div className="animate-pulse h-96 bg-gray-100 rounded-lg" />}>
            <JobsContent />
          </Suspense>
        </div>
      </main>
      <Navigation />
    </div>
  );
}
