"use client";

import { useState, useEffect } from "react";
import { User, Settings, Bell, Link as LinkIcon, Wifi, WifiOff, Loader2 } from "lucide-react";
import { api } from "@/lib/api";

const DEFAULT_PROFILE = {
  name: "Manikandan S",
  title: "CS Engineer & ML Researcher",
  skills: [
    "Python", "PyTorch", "TensorFlow", "Scikit-learn", "FastAPI",
    "SQLite", "C++", "Machine Learning", "Deep Learning", "Knowledge Distillation",
    "Computer Vision", "NLP",
  ],
  experience: "Fresher (Research)",
  location: "Salem, Tamil Nadu, India",
  email: "",
  apiUrl: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  notificationsEnabled: true,
};

type ConnectionStatus = "idle" | "testing" | "ok" | "fail";

export function ProfileScreen() {
  const [profile, setProfile] = useState(DEFAULT_PROFILE);
  const [formData, setFormData] = useState(DEFAULT_PROFILE);
  const [isEditing, setIsEditing] = useState(false);
  const [connStatus, setConnStatus] = useState<ConnectionStatus>("idle");
  const [connLatency, setConnLatency] = useState<number | null>(null);

  // Load overrides from localStorage (only overrides, not the whole profile)
  useEffect(() => {
    try {
      const stored = localStorage.getItem("userProfile");
      if (stored) {
        const data = JSON.parse(stored);
        const merged = { ...DEFAULT_PROFILE, ...data };
        setProfile(merged);
        setFormData(merged);
      }
    } catch {}
  }, []);

  const handleSave = () => {
    setProfile(formData);
    localStorage.setItem("userProfile", JSON.stringify(formData));
    // Persist API URL override for api.ts to pick up
    if (formData.apiUrl) localStorage.setItem("apiUrl", formData.apiUrl);
    setIsEditing(false);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const testConnection = async () => {
    setConnStatus("testing");
    setConnLatency(null);
    // Temporarily override baseUrl for the test
    localStorage.setItem("apiUrl", formData.apiUrl);
    const ms = await api.testConnection();
    if (ms !== null) {
      setConnStatus("ok");
      setConnLatency(ms);
    } else {
      setConnStatus("fail");
    }
  };

  return (
    <div className="space-y-8 max-w-2xl">

      {/* Profile Header */}
      <div className="bg-white rounded-lg border border-gray-200 p-8">
        <div className="flex items-start justify-between mb-6">
          <div className="flex items-center space-x-4">
            <div className="w-16 h-16 rounded-full bg-gradient-to-br from-blue-400 to-blue-600 flex items-center justify-center">
              <User className="w-8 h-8 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{profile.name}</h1>
              <p className="text-gray-600">{profile.title}</p>
              <p className="text-sm text-gray-500 mt-1">{profile.location}</p>
            </div>
          </div>
          <button
            onClick={() => { setIsEditing(!isEditing); setFormData(profile); }}
            className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-900 font-semibold rounded-lg transition"
          >
            {isEditing ? "Cancel" : "Edit"}
          </button>
        </div>

        {isEditing ? (
          <div className="space-y-4">
            {[
              { label: "Full Name", name: "name", type: "text" },
              { label: "Job Title", name: "title", type: "text" },
              { label: "Location", name: "location", type: "text" },
              { label: "Experience", name: "experience", type: "text" },
            ].map(({ label, name, type }) => (
              <div key={name}>
                <label className="block text-sm font-semibold text-gray-700 mb-2">{label}</label>
                <input
                  type={type} name={name}
                  value={formData[name as keyof typeof formData] as string}
                  onChange={handleChange}
                  className="w-full px-4 py-2 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 outline-none transition"
                />
              </div>
            ))}
            <button
              onClick={handleSave}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 rounded-lg transition"
            >
              Save Profile
            </button>
          </div>
        ) : (
          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Experience:</span>
              <span className="font-semibold text-gray-900">{profile.experience}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">University:</span>
              <span className="font-semibold text-gray-900">SASTRA University, CSE</span>
            </div>
          </div>
        )}
      </div>

      {/* Skills */}
      <div className="bg-white rounded-lg border border-gray-200 p-8">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Skills ({profile.skills.length})</h2>
        <div className="flex flex-wrap gap-2">
          {profile.skills.map(skill => (
            <span
              key={skill}
              className="px-3 py-1.5 bg-blue-50 text-blue-700 rounded-full font-semibold text-sm border border-blue-200"
            >
              {skill}
            </span>
          ))}
        </div>
      </div>

      {/* Settings */}
      <div className="bg-white rounded-lg border border-gray-200 p-8">
        <h2 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-2">
          <Settings className="w-5 h-5" />
          Settings
        </h2>

        <div className="space-y-6">
          {/* Notifications toggle */}
          <div className="flex items-center justify-between pb-6 border-b border-gray-200">
            <div className="flex items-center gap-3">
              <Bell className="w-5 h-5 text-gray-600" />
              <div>
                <p className="font-semibold text-gray-900">Daily Digest</p>
                <p className="text-sm text-gray-500">New match notifications</p>
              </div>
            </div>
            <button
              onClick={() => setFormData(prev => ({ ...prev, notificationsEnabled: !prev.notificationsEnabled }))}
              className={`relative inline-flex h-8 w-14 items-center rounded-full transition-colors ${
                formData.notificationsEnabled ? "bg-blue-600" : "bg-gray-300"
              }`}
            >
              <span className={`inline-block h-6 w-6 transform rounded-full bg-white shadow transition-transform ${
                formData.notificationsEnabled ? "translate-x-7" : "translate-x-1"
              }`} />
            </button>
          </div>

          {/* API URL */}
          <div>
            <label className="flex items-center gap-2 mb-3">
              <LinkIcon className="w-5 h-5 text-gray-600" />
              <span className="font-semibold text-gray-900">Backend API URL</span>
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                name="apiUrl"
                value={formData.apiUrl}
                placeholder="http://localhost:8000"
                onChange={handleChange}
                className="flex-1 px-4 py-2 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 outline-none transition text-sm font-mono"
              />
              <button
                onClick={testConnection}
                disabled={connStatus === "testing"}
                className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-900 text-sm font-semibold rounded-lg transition flex items-center gap-2 disabled:opacity-60"
              >
                {connStatus === "testing" ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : connStatus === "ok" ? (
                  <Wifi className="w-4 h-4 text-green-600" />
                ) : connStatus === "fail" ? (
                  <WifiOff className="w-4 h-4 text-red-500" />
                ) : (
                  <Wifi className="w-4 h-4" />
                )}
                Test
              </button>
            </div>
            {/* Connection status line */}
            {connStatus === "ok" && (
              <p className="text-xs text-green-600 mt-2">✅ Connected — {connLatency}ms</p>
            )}
            {connStatus === "fail" && (
              <p className="text-xs text-red-500 mt-2">
                ❌ Cannot reach server. Check that FastAPI is running and the URL is correct.
              </p>
            )}
            <p className="text-xs text-gray-500 mt-2">
              Set <code className="bg-gray-100 px-1 rounded">NEXT_PUBLIC_API_URL</code> in{" "}
              <code className="bg-gray-100 px-1 rounded">.env.local</code> to avoid re-entering this.
            </p>
          </div>
        </div>

        <button
          onClick={handleSave}
          className="mt-6 w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2.5 rounded-lg transition"
        >
          Save Settings
        </button>
      </div>
    </div>
  );
}
