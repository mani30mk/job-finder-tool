/**
 * jobMatcher.js
 * Uses parsed resume profile to search for matched jobs via Gemini + Free APIs.
 * Scores each job 0-100 against the profile.
 */

const GEMINI_KEY_SK = 'oppr_gemini_key';

// ── Free API fetchers (same as before, no key needed) ─────────────────────────

async function fetchRemotive(keywords) {
  try {
    const r = await fetch(`https://remotive.com/api/remote-jobs?search=${encodeURIComponent(keywords)}`);
    if (!r.ok) return [];
    const d = await r.json();
    return (d.jobs || []).slice(0, 20).map(j => ({
      _id: 'rem_' + j.id,
      title: j.title,
      company: j.company_name,
      location: j.candidate_required_location || 'Remote',
      type: j.job_type || 'Full-time',
      posted: j.publication_date?.split('T')[0] || '',
      url: j.url,
      tags: j.tags || [],
      description: stripHtml(j.description).slice(0, 500),
      source: 'Remotive',
      _isNew: isNew(j.publication_date)
    }));
  } catch { return []; }
}

async function fetchArbeitnow(keywords) {
  try {
    const r = await fetch(`https://www.arbeitnow.com/api/job-board-api?q=${encodeURIComponent(keywords)}`);
    if (!r.ok) return [];
    const d = await r.json();
    return (d.data || []).slice(0, 20).map(j => ({
      _id: 'arb_' + j.slug,
      title: j.title,
      company: j.company_name,
      location: j.location || (j.remote ? 'Remote' : 'Various'),
      type: j.job_types?.join(', ') || 'Full-time',
      posted: j.created_at ? new Date(j.created_at * 1000).toISOString().split('T')[0] : '',
      url: j.url,
      tags: j.tags || [],
      description: stripHtml(j.description).slice(0, 500),
      source: 'Arbeitnow',
      _isNew: j.created_at ? isNew(new Date(j.created_at * 1000).toISOString()) : false
    }));
  } catch { return []; }
}

async function fetchAdzuna(keywords, location) {
  try {
    const app_id = '5b54b5a1';
    const app_key = '9ff7e43bbcb4c2dad0d22f2a0c4a0c1a';
    const country = guessCountry(location);
    const r = await fetch(
      `https://api.adzuna.com/v1/api/jobs/${country}/search/1?app_id=${app_id}&app_key=${app_key}&results_per_page=15&what=${encodeURIComponent(keywords)}&content-type=application/json`
    );
    if (!r.ok) return [];
    const d = await r.json();
    return (d.results || []).map(j => ({
      _id: 'adz_' + j.id,
      title: j.title,
      company: j.company?.display_name || 'Unknown',
      location: j.location?.display_name || 'Various',
      type: j.contract_time === 'part_time' ? 'Part-time' : 'Full-time',
      posted: j.created?.split('T')[0] || '',
      url: j.redirect_url,
      tags: j.category ? [j.category.label] : [],
      description: (j.description || '').slice(0, 500),
      source: 'Adzuna',
      _isNew: isNew(j.created)
    }));
  } catch { return []; }
}

// ── AI scoring — score each job against profile ───────────────────────────────

export async function scoreJobsWithAI(jobs, profile, apiKey) {
  const key = apiKey || localStorage.getItem(GEMINI_KEY_SK);
  if (!key || !jobs.length) return jobs.map(j => ({ ...j, _score: 50, _reasons: [] }));

  // Score in one batch call to save tokens
  const jobList = jobs.slice(0, 12).map((j, i) => `${i}. ${j.title} at ${j.company} (${j.location}) - Tags: ${j.tags?.join(', ') || 'none'}`).join('\n');

  const prompt = `You are a job matching AI. Score these jobs for this candidate.

CANDIDATE PROFILE:
- Skills: ${[...( profile.skills?.languages||[]), ...(profile.skills?.frameworks||[]), ...(profile.skills?.tools||[])].join(', ')}
- Domain: ${(profile.skills?.domains||[]).join(', ')}
- Level: ${profile.level || 'entry'}
- Experience: ${profile.experience_years || 0} years
- Current role: ${profile.current_role || 'student'}
- Target roles: ${(profile.target_roles||[]).join(', ')}

JOBS TO SCORE:
${jobList}

Return ONLY a JSON array of scores for each job (index matches job number):
[
  { "index": 0, "score": 85, "reasons": ["matches Python skills", "ML domain match"], "missing": ["5 years exp required"] },
  ...
]
Score 0-100. 80+ = excellent match. 60-79 = good. 40-59 = fair. below 40 = poor.`;

  try {
    const res = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${key}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contents: [{ role: 'user', parts: [{ text: prompt }] }],
          generationConfig: { temperature: 0.1, maxOutputTokens: 800 }
        })
      }
    );
    if (!res.ok) return jobs.map(j => ({ ...j, _score: 50, _reasons: [] }));

    const data = await res.json();
    const raw = data?.candidates?.[0]?.content?.parts?.[0]?.text || '[]';
    const match = raw.match(/(\[[\s\S]*\])/);
    if (!match) return jobs.map(j => ({ ...j, _score: 50, _reasons: [] }));

    const scores = JSON.parse(match[1]);
    return jobs.map((j, i) => {
      const s = scores.find(x => x.index === i) || { score: 50, reasons: [], missing: [] };
      return { ...j, _score: s.score, _reasons: s.reasons || [], _missing: s.missing || [] };
    });
  } catch {
    return jobs.map(j => ({ ...j, _score: 50, _reasons: [] }));
  }
}

// ── Main: find jobs from profile ──────────────────────────────────────────────

export async function findJobsFromProfile(profile, options = {}) {
  const {
    useRemotive = true,
    useArbeitnow = true,
    useAdzuna = true,
    scoreWithAI = true,
    apiKey = null
  } = options;

  const keywords = (profile.search_keywords || []).slice(0, 4).join(' ')
    || (profile.target_roles || []).slice(0, 2).join(' ')
    || profile.current_role
    || 'software engineer';

  const location = profile.location || '';

  const fetches = [];
  if (useRemotive) fetches.push(fetchRemotive(keywords));
  if (useArbeitnow) fetches.push(fetchArbeitnow(keywords));
  if (useAdzuna) fetches.push(fetchAdzuna(keywords, location));

  const results = await Promise.allSettled(fetches);
  let jobs = results.flatMap(r => r.status === 'fulfilled' ? r.value : []);

  // Deduplicate
  const seen = new Set();
  jobs = jobs.filter(j => {
    const key = (j.title + j.company).toLowerCase().replace(/\s/g, '');
    if (seen.has(key)) return false;
    seen.add(key); return true;
  });

  // Filter by level
  if (profile.level === 'internship') {
    const intern = jobs.filter(j =>
      j.title.toLowerCase().includes('intern') ||
      j.tags.some(t => t.toLowerCase().includes('intern'))
    );
    if (intern.length >= 3) jobs = intern;
  }

  // Score with AI
  if (scoreWithAI && jobs.length > 0) {
    jobs = await scoreJobsWithAI(jobs, profile, apiKey);
  } else {
    jobs = jobs.map(j => ({ ...j, _score: 50, _reasons: [] }));
  }

  // Sort by score desc, then by new
  jobs.sort((a, b) => {
    if (b._score !== a._score) return b._score - a._score;
    if (b._isNew !== a._isNew) return b._isNew ? 1 : -1;
    return 0;
  });

  return jobs;
}

// ── Daily updates ─────────────────────────────────────────────────────────────

const DAILY_SK = 'oppr_daily_';

export function getLastFetchDate() {
  return localStorage.getItem(DAILY_SK + 'date') || null;
}

export function setLastFetchDate() {
  localStorage.setItem(DAILY_SK + 'date', new Date().toDateString());
}

export function shouldRefreshToday() {
  return getLastFetchDate() !== new Date().toDateString();
}

export function saveDailyJobs(jobs) {
  localStorage.setItem(DAILY_SK + 'jobs', JSON.stringify(jobs));
  setLastFetchDate();
}

export function loadDailyJobs() {
  try { return JSON.parse(localStorage.getItem(DAILY_SK + 'jobs') || 'null'); }
  catch { return null; }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function stripHtml(h) {
  const d = document.createElement('div');
  d.innerHTML = h || '';
  return d.textContent || '';
}

function guessCountry(loc) {
  if (!loc) return 'us';
  const l = loc.toLowerCase();
  if (l.includes('india')) return 'in';
  if (l.includes('uk') || l.includes('london')) return 'gb';
  if (l.includes('australia')) return 'au';
  if (l.includes('canada')) return 'ca';
  if (l.includes('germany')) return 'de';
  return 'us';
}

function isNew(dateStr) {
  if (!dateStr) return false;
  const d = new Date(dateStr);
  const now = new Date();
  return (now - d) < 48 * 60 * 60 * 1000; // within 48 hours
}
