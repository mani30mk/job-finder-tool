# Resume Feature — Integration Guide

## Files to add to your repo

```
job-finder-tool/
├── resume.html          ← main resume feature page  (NEW)
├── resumeParser.js      ← resume parsing module     (NEW, optional import)
├── jobMatcher.js        ← job matching + scoring    (NEW, optional import)
├── job-finder-gemini.html   ← your existing job finder
└── ...
```

## Quick Start

1. Copy `resume.html`, `resumeParser.js`, `jobMatcher.js` into your repo root.
2. Open `resume.html` in any browser.
3. Paste your free Gemini API key (from https://aistudio.google.com/app/apikey).
4. Upload your PDF resume → AI parses it → finds matched jobs automatically.

---

## How It Works

### Step 1 — Upload Resume
- Drag & drop a **PDF or .txt** resume
- PDF.js extracts text client-side (no upload to any server)

### Step 2 — AI Parses
- Gemini 1.5 Flash extracts: name, skills, experience, education, projects, target roles
- Builds **search_keywords** automatically from your profile
- Everything stored in `localStorage` — persists across sessions

### Step 3 — Match Jobs
Fetches from **3 free APIs** simultaneously:
| API | Coverage | Key needed? |
|-----|----------|------------|
| Remotive | Remote tech jobs | ❌ No |
| Arbeitnow | Global + visa-friendly | ❌ No |
| Adzuna | Worldwide (IN, US, UK, AU…) | ❌ No |

Then uses **Gemini AI** to score each job 0–100 based on your profile:
- ✅ Match reasons shown (e.g. "Python skill match")
- ✗ Missing requirements shown (e.g. "requires 5yr exp")
- Sorted by best match first

### Step 4 — Daily Updates
- A banner appears showing when jobs were last refreshed
- Click **"Refresh Now"** to fetch today's new listings
- 🆕 badge marks jobs posted within 48 hours
- All results auto-saved — close & reopen, everything is there

---

## Token Usage (Free Tier Friendly)

Each full search uses **2 Gemini API calls**:
1. Resume parse: ~800 tokens
2. Job scoring (up to 12 jobs): ~500 tokens

Free limit: **1,500 calls/day** → plenty for daily use.

---

## Link from your existing job-finder page

Add this button to `job-finder-gemini.html`:

```html
<a href="resume.html" class="nav-btn">📄 Resume Match</a>
```

---

## Customization

### Add more job APIs
In `resume.html`, find `fetchRemotive`, `fetchArbeitnow`, `fetchAdzuna` and add:

```js
async function fetchMyNewAPI(q) {
  const r = await fetch(`https://api.example.com/jobs?q=${encodeURIComponent(q)}`);
  const d = await r.json();
  return d.jobs.map(j => ({
    _id: 'myapi_' + j.id,
    title: j.title,
    company: j.company,
    location: j.location,
    type: 'Full-time',
    posted: j.date,
    url: j.apply_url,
    tags: j.skills || [],
    description: j.summary,
    source: 'MyAPI',
    _isNew: false,
    _score: 50, _reasons: [], _missing: []
  }));
}
```

Then add it to `findMatchedJobs()`:
```js
const [rem, arb, adz, mine] = await Promise.allSettled([
  fetchRemotive(keywords),
  fetchArbeitnow(keywords),
  fetchAdzuna(keywords, location),
  fetchMyNewAPI(keywords)   // ← add here
]);
```

### Change Gemini model
Find `gemini-1.5-flash` and replace with `gemini-1.5-pro` for better accuracy (uses more tokens).

---

## Privacy
- Resume text is sent **only to Google's Gemini API** using your own key
- No data is stored on any server
- Everything lives in your browser's `localStorage`
