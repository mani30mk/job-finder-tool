"use client";

import { useState, useEffect, useRef } from "react";
import {
  User, Settings, Bell, Link as LinkIcon,
  Wifi, WifiOff, Loader2, FileText, Upload, CheckCircle, XCircle,
} from "lucide-react";
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
type ResumeStatus = "idle" | "uploading" | "success" | "error";

export function ProfileScreen() {
  const [profile, setProfile] = useState(DEFAULT_PROFILE);
  const [formData, setFormData] = useState(DEFAULT_PROFILE);
  const [isEditing, setIsEditing] = useState(false);
  const [connStatus, setConnStatus] = useState<ConnectionStatus>("idle");
  const [connLatency, setConnLatency] = useState<number | null>(null);

  // Resume upload state
  const [resumeStatus, setResumeStatus] = useState<ResumeStatus>("idle");
  const [resumeFileName, setResumeFileName] = useState<string | null>(null);
  const [resumeError, setResumeError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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
      const savedResume = localStorage.getItem("resumeFileName");
      if (savedResume) setResumeFileName(savedResume);
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

  // ── Resume upload handler ──
  const handleResumeUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    const allowed = [".pdf", ".docx", ".txt", ".md"];
    const ext = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();
    if (!allowed.includes(ext)) {
      setResumeStatus("error");
      setResumeError(`Invalid file type. Allowed: ${allowed.join(", ")}`);
      return;
    }

    // Validate file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
      setResumeStatus("error");
      setResumeError("File too large. Maximum size: 10MB");
      return;
    }

    setResumeStatus("uploading");
    setResumeError(null);

    try {
      const baseUrl = formData.apiUrl || api.baseUrl;
      const form = new FormData();
      form.append("file", file);

      const res = await fetch(`${baseUrl}/api/v1/profile/upload`, {
        method: "POST",
        body: form,
        signal: AbortSignal.timeout(30000),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }

      const data = await res.json();
      const parsed = data.profile;

      // Update profile with parsed resume data
      const updatedProfile = {
        ...formData,
        name: parsed.name || formData.name,
        skills: parsed.skills?.length > 0
          ? [...new Set([...parsed.skills.map((s: string) => s.charAt(0).toUpperCase() + s.slice(1))])]
          : formData.skills,
        title: parsed.job_titles?.[0]
          ? parsed.job_titles.map((t: string) => t.charAt(0).toUpperCase() + t.slice(1)).join(" / ")
          : formData.title,
        experience: parsed.experience_years > 0
          ? `${parsed.experience_years} years`
          : formData.experience,
        location: parsed.locations_preferred?.[0]
          ? parsed.locations_preferred.map((l: string) => l.charAt(0).toUpperCase() + l.slice(1)).join(", ")
          : formData.location,
        email: parsed.email || formData.email,
      };

      setFormData(updatedProfile);
      setProfile(updatedProfile);
      localStorage.setItem("userProfile", JSON.stringify(updatedProfile));
      setResumeFileName(file.name);
      localStorage.setItem("resumeFileName", file.name);
      setResumeStatus("success");

    } catch (err: unknown) {
      setResumeStatus("error");
      setResumeError(err instanceof Error ? err.message : "Upload failed");
    }

    // Reset file input so same file can be re-uploaded
    if (fileInputRef.current) fileInputRef.current.value = "";
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

      {/* ── Resume Upload ── */}
      <div className="bg-white rounded-lg border border-gray-200 p-8">
        <h2 className="text-xl font-bold text-gray-900 mb-2 flex items-center gap-2">
          <FileText className="w-5 h-5 text-blue-600" />
          Resume
        </h2>
        <p className="text-sm text-gray-500 mb-5">
          Upload your resume to auto-fill your profile. Updating it will re-parse and refresh your skills &amp; details.
        </p>

        {/* Current resume display */}
        {resumeFileName && resumeStatus !== "uploading" && (
          <div className="flex items-center gap-3 mb-4 px-4 py-3 bg-blue-50 border border-blue-200 rounded-lg">
            <FileText className="w-5 h-5 text-blue-600 shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-blue-900 truncate">{resumeFileName}</p>
              <p className="text-xs text-blue-600">Currently loaded</p>
            </div>
            <CheckCircle className="w-5 h-5 text-green-500 shrink-0" />
          </div>
        )}

        {/* Upload area */}
        <div
          onClick={() => fileInputRef.current?.click()}
          className={`relative border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
            resumeStatus === "uploading"
              ? "border-blue-400 bg-blue-50"
              : resumeStatus === "error"
              ? "border-red-300 bg-red-50 hover:border-red-400"
              : "border-gray-300 bg-gray-50 hover:border-blue-400 hover:bg-blue-50"
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.txt,.md"
            onChange={handleResumeUpload}
            className="hidden"
            id="resume-upload"
          />

          {resumeStatus === "uploading" ? (
            <div className="flex flex-col items-center gap-3">
              <Loader2 className="w-10 h-10 text-blue-500 animate-spin" />
              <p className="text-sm font-semibold text-blue-700">Parsing resume...</p>
              <p className="text-xs text-blue-500">Extracting skills, experience &amp; details</p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-3">
              <div className="w-14 h-14 rounded-full bg-blue-100 flex items-center justify-center">
                <Upload className="w-7 h-7 text-blue-600" />
              </div>
              <div>
                <p className="text-sm font-semibold text-gray-900">
                  {resumeFileName ? "Upload New Resume" : "Upload Resume"}
                </p>
                <p className="text-xs text-gray-500 mt-1">PDF, DOCX, or TXT — max 10MB</p>
              </div>
            </div>
          )}
        </div>

        {/* Status messages */}
        {resumeStatus === "success" && (
          <div className="flex items-center gap-2 mt-3 px-3 py-2 bg-green-50 border border-green-200 rounded-lg">
            <CheckCircle className="w-4 h-4 text-green-600 shrink-0" />
            <p className="text-sm text-green-700 font-medium">
              Resume parsed! Profile updated with extracted skills &amp; details.
            </p>
          </div>
        )}
        {resumeStatus === "error" && (
          <div className="flex items-center gap-2 mt-3 px-3 py-2 bg-red-50 border border-red-200 rounded-lg">
            <XCircle className="w-4 h-4 text-red-500 shrink-0" />
            <p className="text-sm text-red-700">{resumeError || "Upload failed. Check your backend connection."}</p>
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
