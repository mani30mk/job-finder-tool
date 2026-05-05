"use client";

import { Header } from "@/components/Header";
import { Navigation } from "@/components/Navigation";
import { ProfileScreen } from "@/components/screens/ProfileScreen";

export default function ProfilePage() {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Header />
      <main className="flex-1 pb-24 lg:pb-0 safe-area-inset-bottom">
        <div className="max-w-4xl mx-auto px-3 sm:px-6 lg:px-8 py-4 sm:py-8">
          <ProfileScreen />
        </div>
      </main>
      <Navigation />
    </div>
  );
}
