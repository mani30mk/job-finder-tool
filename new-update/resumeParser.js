/**
 * resumeParser.js
 * Drop this into your job-finder-tool repo.
 * Parses PDF or plain-text resumes using Gemini API.
 * Returns structured profile used by jobMatcher.js
 */

const GEMINI_KEY_SK = 'oppr_gemini_key';

// ── PDF → base64 ──────────────────────────────────────────────────────────────
export function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result.split(',')[1]);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

// ── PDF → plain text (client-side, no library needed) ────────────────────────
export async function extractTextFromPDF(file) {
  // Use PDF.js if available, else fall back to sending raw PDF to Gemini
  if (window.pdfjsLib) {
    const arrayBuffer = await file.arrayBuffer();
    const pdf = await window.pdfjsLib.getDocument({ data: arrayBuffer }).promise;
    let text = '';
    for (let i = 1; i <= Math.min(pdf.numPages, 5); i++) {
      const page = await pdf.getPage(i);
      const content = await page.getTextContent();
      text += content.items.map(item => item.str).join(' ') + '\n';
    }
    return { type: 'text', content: text.slice(0, 8000) };
  }
  // Fallback: send PDF directly to Gemini as base64
  const b64 = await fileToBase64(file);
  return { type: 'pdf_b64', content: b64, mimeType: file.type };
}

// ── Core parser — calls Gemini ────────────────────────────────────────────────
export async function parseResume(file, apiKey) {
  const key = apiKey || localStorage.getItem(GEMINI_KEY_SK);
  if (!key) throw new Error('No Gemini API key found. Please save your key first.');

  const extracted = await extractTextFromPDF(file);

  // Build Gemini request
  let contentPart;
  if (extracted.type === 'text') {
    contentPart = {
      text: `Parse this resume and return ONLY a JSON object:\n\n${extracted.content}`
    };
  } else {
    // Send raw PDF as inline_data
    contentPart = {
      inline_data: { mime_type: extracted.mimeType, data: extracted.content }
    };
  }

  const prompt = `You are a resume parser. Extract all information from this resume.
Return ONLY a valid JSON object (no markdown, no explanation) with this exact structure:

{
  "name": "Full Name",
  "email": "email@example.com",
  "phone": "+1234567890",
  "location": "City, Country",
  "summary": "2-3 sentence professional summary",
  "experience_years": 2,
  "current_role": "Most recent job title",
  "skills": {
    "languages": ["Python", "JavaScript"],
    "frameworks": ["React", "TensorFlow"],
    "tools": ["Git", "Docker"],
    "domains": ["Machine Learning", "Web Development"]
  },
  "education": [
    {
      "degree": "B.Tech Computer Science",
      "institution": "University Name",
      "year": "2024",
      "gpa": "8.5"
    }
  ],
  "experience": [
    {
      "title": "Job Title",
      "company": "Company Name",
      "duration": "Jun 2023 – Dec 2023",
      "description": "Key responsibilities in 1-2 sentences"
    }
  ],
  "projects": [
    {
      "name": "Project Name",
      "tech": ["Python", "Flask"],
      "description": "What it does in 1 sentence"
    }
  ],
  "certifications": ["AWS Certified", "TensorFlow Developer"],
  "languages_spoken": ["English", "Tamil"],
  "target_roles": ["inferred role 1", "inferred role 2"],
  "search_keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
  "preferred_companies": [],
  "open_to_remote": true,
  "level": "internship|entry|mid|senior"
}

Infer target_roles and search_keywords from the skills and experience. Be specific.`;

  const messages = extracted.type === 'text'
    ? [{ role: 'user', parts: [{ text: prompt + '\n\nRESUME:\n' + extracted.content }] }]
    : [{ role: 'user', parts: [{ text: prompt }, contentPart] }];

  const res = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${key}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contents: messages,
        generationConfig: { temperature: 0.1, maxOutputTokens: 1500 }
      })
    }
  );

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err?.error?.message || `Gemini API error: ${res.status}`);
  }

  const data = await res.json();
  const raw = data?.candidates?.[0]?.content?.parts?.[0]?.text || '';

  // Parse JSON from response
  const jsonMatch = raw.match(/```(?:json)?\s*(\{[\s\S]*?\})\s*```/) || raw.match(/(\{[\s\S]*\})/);
  if (!jsonMatch) throw new Error('Could not extract profile from resume. Try a text-based PDF.');

  const profile = JSON.parse(jsonMatch[1] || jsonMatch[0]);
  profile._parsedAt = new Date().toISOString();
  profile._fileName = file.name;

  return profile;
}

// ── Save / load profile ───────────────────────────────────────────────────────
const PROFILE_SK = 'oppr_resume_profile';

export function saveProfile(profile) {
  localStorage.setItem(PROFILE_SK, JSON.stringify(profile));
}

export function loadProfile() {
  try { return JSON.parse(localStorage.getItem(PROFILE_SK) || 'null'); }
  catch { return null; }
}

export function clearProfile() {
  localStorage.removeItem(PROFILE_SK);
}
