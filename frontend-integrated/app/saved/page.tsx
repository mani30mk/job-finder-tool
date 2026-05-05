import { Header } from "@/components/Header";
import { Navigation } from "@/components/Navigation";
import { SavedJobsScreen } from "@/components/screens/SavedJobsScreen";

export default function SavedPage() {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Header />
      <main className="flex-1 pb-24 lg:pb-0">
        <div className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 py-4 sm:py-8">
          <SavedJobsScreen />
        </div>
      </main>
      <Navigation />
    </div>
  );
}