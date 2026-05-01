// ── Resume Module — profile, parsing, scoring, daily tracking ─────────────────
const PROFILE_SK = 'huntr_profile';
const RESUME_TEXT_SK = 'huntr_resume_text';
const RESUME_META_SK = 'huntr_resume_meta';
const DAILY_SK = 'huntr_daily';

let profile = null;
let selectedFile = null;
const LOCAL_KEY_SK = 'huntr_gemini_key'; // fallback for local dev

// ── Gemini API helper (server proxy with local fallback) ──────────────────────
function saveGeminiKey(){
  const k = document.getElementById('gemini-key-input')?.value?.trim();
  if(!k){ alert('Paste your Gemini API key first.'); return; }
  localStorage.setItem(LOCAL_KEY_SK, k);
  setResumeStatus('✓ API key saved!', 'ok');
}

async function callGemini(body){
  // Try server proxy first (works on Vercel)
  try{
    const res = await fetch('/api/gemini', {
      method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body)
    });
    if(res.ok) return await res.json();
  } catch(e){}
  // Fallback: direct API call with localStorage key
  const key = localStorage.getItem(LOCAL_KEY_SK) || document.getElementById('gemini-key-input')?.value?.trim();
  if(!key) throw new Error('Gemini API key required. Paste your key above and click Save Key.');
  if(!localStorage.getItem(LOCAL_KEY_SK)) localStorage.setItem(LOCAL_KEY_SK, key);

  // Model pipeline — tries each model in order until one works
  const MODELS = [
    'gemini-2.5-flash',
    'gemini-2.0-flash',
    'gemini-2.0-flash-lite',
    'gemini-1.5-flash',
    'gemini-1.5-pro',
  ];

  let lastError = '';
  for(const model of MODELS){
    try{
      const res = await fetch(
        'https://generativelanguage.googleapis.com/v1beta/models/'+model+':generateContent?key='+key,
        { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) }
      );
      if(res.ok){
        console.log('[HUNTR] Using model:', model);
        return await res.json();
      }
      const err = await res.json().catch(()=>({}));
      lastError = err?.error?.message || 'HTTP '+res.status;
      // If invalid key, stop trying
      if(res.status===400 || res.status===403){
        localStorage.removeItem(LOCAL_KEY_SK);
        throw new Error('Invalid API key: '+lastError);
      }
      // If quota exceeded or model not found, try next model
      if(res.status===429 || res.status===404){
        console.warn('[HUNTR] Model '+model+' unavailable ('+res.status+'), trying next...');
        continue;
      }
      // Other error — try next
      console.warn('[HUNTR] Model '+model+' error: '+lastError);
      continue;
    } catch(e){
      if(e.message.startsWith('Invalid API key')) throw e;
      lastError = e.message;
      console.warn('[HUNTR] Model '+model+' fetch failed:', e.message);
      continue;
    }
  }
  throw new Error('All models exhausted. Last error: '+lastError+'. Wait 30s and retry, or check your API key quota at ai.dev/rate-limit');
}

function persistProfile(p){ try{ localStorage.setItem(PROFILE_SK, JSON.stringify(p)); }catch(e){} }
function loadProfileData(){ try{ return JSON.parse(localStorage.getItem(PROFILE_SK)||'null'); }catch{return null;} }

// ── File handling ─────────────────────────────────────────────────────────────
function onFileSelect(e){ handleFile(e.target.files[0]); }

function handleFile(file){
  if(!file) return;
  selectedFile = file;
  document.getElementById('file-name').textContent = '📎 ' + file.name;
  document.getElementById('file-name').style.display = 'block';
  document.getElementById('btn-parse').disabled = false;
  setResumeStatus('File ready: ' + file.name + ' (' + (file.size/1024).toFixed(0) + ' KB)', 'ok');
}

async function extractText(file){
  if(file.type === 'text/plain') return await file.text();
  if(window.pdfjsLib){
    const buf = await file.arrayBuffer();
    const pdf = await pdfjsLib.getDocument({data:buf}).promise;
    let txt = '';
    for(let i=1; i<=Math.min(pdf.numPages, 6); i++){
      const page = await pdf.getPage(i);
      const content = await page.getTextContent();
      txt += content.items.map(x=>x.str).join(' ') + '\n';
    }
    return txt.slice(0, 9000);
  }
  throw new Error('PDF.js failed to load. Try a .txt resume.');
}

// ── Parse resume via server proxy ─────────────────────────────────────────────
async function startParse(){
  if(!selectedFile){ setResumeStatus('Upload a file first.', 'warn'); return; }
  const btn = document.getElementById('btn-parse');
  btn.disabled = true; btn.textContent = '⏳ Parsing…';
  document.getElementById('resume-progress').style.display = 'block';
  setResumeProg(10, 'Extracting text from PDF…');

  try{
    const text = await extractText(selectedFile);
    setResumeProg(30, 'Saving resume text…');
    try{ localStorage.setItem(RESUME_TEXT_SK, text); }catch(e){}
    try{ localStorage.setItem(RESUME_META_SK, JSON.stringify({name:selectedFile.name, savedAt:new Date().toISOString()})); }catch(e){}

    setResumeProg(50, 'AI is analyzing your resume…');
    const parsed = await parseResumeWithGemini(text);
    setResumeProg(90, 'Building profile…');

    profile = { ...parsed, _parsedAt: new Date().toISOString(), _file: selectedFile.name };
    persistProfile(profile);

    setResumeProg(100, 'Done!');
    setTimeout(()=>{ document.getElementById('resume-progress').style.display='none'; }, 600);

    showProfileBanner(profile);
    autoFillFromProfile(profile);
    document.getElementById('resume-upload-section').style.display = 'none';
    setResumeStatus('Resume parsed! Searching jobs now…', 'ok');

    setTimeout(()=> huntFromProfile(), 500);
  } catch(e){
    setResumeStatus('Error: ' + e.message, 'err');
    document.getElementById('resume-progress').style.display = 'none';
  }
  btn.disabled = false; btn.textContent = '⚡ Parse Resume with AI';
}

async function parseResumeWithGemini(resumeText){
  const prompt = 'You are a resume parser. Extract ALL information from this resume.\nReturn ONLY a valid JSON object (no markdown fences, no explanation, just raw JSON).\n\n{\n  "name": "Full Name",\n  "email": "email",\n  "phone": "phone",\n  "location": "City, Country",\n  "summary": "2-3 sentence professional summary",\n  "experience_years": 0,\n  "current_role": "Most recent job title or Student",\n  "skills": {\n    "languages": ["Python","Java"],\n    "frameworks": ["React","TensorFlow"],\n    "tools": ["Git","Docker"],\n    "domains": ["Machine Learning","Web Dev"]\n  },\n  "education": [{"degree":"","institution":"","year":"","gpa":""}],\n  "experience": [{"title":"","company":"","duration":"","description":""}],\n  "projects": [{"name":"","tech":[],"description":""}],\n  "certifications": [],\n  "target_roles": ["role1","role2","role3"],\n  "search_keywords": ["kw1","kw2","kw3","kw4","kw5","kw6"],\n  "level": "internship",\n  "open_to_remote": true\n}\n\nlevel must be one of: internship, entry, mid, senior.\nInfer target_roles and search_keywords from skills and experience.\n\nRESUME:\n' + resumeText;

  const body = {
    contents: [{role:'user', parts:[{text: prompt}]}],
    generationConfig: { temperature: 0.1, maxOutputTokens: 4096 }
  };
  const d = await callGemini(body);
  const raw = d?.candidates?.[0]?.content?.parts?.[0]?.text || '';
  console.log('[HUNTR] Raw Gemini response:', raw.slice(0, 500));

  // Try multiple extraction strategies
  let jsonStr = null;

  // Strategy 1: markdown code fence ```json ... ```
  let m = raw.match(/```(?:json)?\s*\n?([\s\S]*?)\n?\s*```/);
  if(m) jsonStr = m[1].trim();

  // Strategy 2: bare JSON object { ... }
  if(!jsonStr){
    m = raw.match(/(\{[\s\S]*\})/);
    if(m) jsonStr = m[1].trim();
  }

  if(!jsonStr){
    console.error('[HUNTR] Could not find JSON in response:', raw);
    throw new Error('Could not parse profile. Raw response logged to console (F12). Try again or use a .txt resume.');
  }

  try{
    return JSON.parse(jsonStr);
  } catch(e){
    console.error('[HUNTR] JSON parse failed:', e.message, '\nExtracted string:', jsonStr.slice(0, 300));
    throw new Error('JSON parse error: ' + e.message + '. Check console (F12) for details.');
  }
}

// ── Profile UI ────────────────────────────────────────────────────────────────
function showProfileBanner(p){
  document.getElementById('profile-banner').style.display = 'block';
  const initials = (p.name||'U').split(' ').map(x=>x[0]).join('').slice(0,2).toUpperCase();
  document.getElementById('profile-avatar').textContent = initials;
  document.getElementById('profile-name').textContent = p.name || 'Unknown';
  document.getElementById('profile-role').textContent = p.current_role || 'Professional';
  document.getElementById('profile-parsed-date').textContent =
    p._parsedAt ? 'Parsed ' + new Date(p._parsedAt).toLocaleDateString() : '';

  const sk = p.skills || {};
  let chips = '';
  if(sk.languages?.length) chips += sk.languages.map(s=>'<span class="chip chip-lang">'+h(s)+'</span>').join('');
  if(sk.frameworks?.length) chips += sk.frameworks.map(s=>'<span class="chip chip-fw">'+h(s)+'</span>').join('');
  if(sk.tools?.length) chips += sk.tools.map(s=>'<span class="chip chip-tool">'+h(s)+'</span>').join('');
  if(sk.domains?.length) chips += sk.domains.map(s=>'<span class="chip chip-dom">'+h(s)+'</span>').join('');
  document.getElementById('profile-skills').innerHTML = chips;

  document.getElementById('profile-keywords').innerHTML =
    (p.search_keywords||[]).map(k=>'<span class="keyword-chip">'+h(k)+'</span>').join('');

  let meta = [];
  if(p.location) meta.push('📍 '+p.location);
  if(p.experience_years !== undefined) meta.push('💼 '+p.experience_years+'yr exp');
  if(p.level) meta.push('🎯 '+p.level);
  if(p.open_to_remote) meta.push('🌐 Remote OK');
  if(p.target_roles?.length) meta.push('→ '+p.target_roles.join(', '));
  document.getElementById('profile-meta-info').innerHTML = meta.map(m=>'<span>'+m+'</span>').join('');
}

function autoFillFromProfile(p){
  if(!p) return;
  document.getElementById('q').value = (p.search_keywords || p.target_roles || []).slice(0,4).join(', ');
  if(p.level) document.getElementById('level').value = p.level;
  if(p.location) document.getElementById('loc').value = p.location;
  const allSkills = [...(p.skills?.languages||[]),...(p.skills?.frameworks||[]),...(p.skills?.tools||[])];
  document.getElementById('skills').value = allSkills.slice(0,8).join(', ');
  if(p.location){
    const loc = p.location.toLowerCase();
    if(loc.includes('india')) document.getElementById('country').value = 'in';
    else if(loc.includes('us')||loc.includes('america')) document.getElementById('country').value = 'us';
    else if(loc.includes('uk')||loc.includes('london')) document.getElementById('country').value = 'gb';
    else if(loc.includes('australia')) document.getElementById('country').value = 'au';
    else if(loc.includes('canada')) document.getElementById('country').value = 'ca';
  }
  if(p.level === 'internship') document.getElementById('jtype').value = 'intern';
}

function huntFromProfile(){
  if(!profile){ setStatus('Upload your resume first.','warn'); return; }
  autoFillFromProfile(profile);
  doSearch(true);
}

function resetProfile(){
  if(!confirm('Clear your profile? You will need to upload your resume again.')) return;
  profile = null;
  localStorage.removeItem(PROFILE_SK);
  localStorage.removeItem(RESUME_TEXT_SK);
  localStorage.removeItem(RESUME_META_SK);
  localStorage.removeItem(DAILY_SK);
  document.getElementById('profile-banner').style.display = 'none';
  document.getElementById('daily-banner').style.display = 'none';
  document.getElementById('resume-upload-section').style.display = 'block';
  document.getElementById('file-name').style.display = 'none';
  document.getElementById('btn-parse').disabled = true;
  selectedFile = null;
  // Clear form
  document.getElementById('q').value = '';
  document.getElementById('loc').value = '';
  document.getElementById('skills').value = '';
}

// ── AI Job Scoring ────────────────────────────────────────────────────────────
async function scoreJobsWithProfile(jobList, p){
  if(!jobList.length || !p) return jobList;
  const BATCH = 12;
  const results = jobList.map(j => ({...j, _score:50, _reasons:[], _missing:[]}));
  const toScore = results.slice(0, BATCH);

  const jobSummary = toScore.map((j,i) =>
    i+'. "'+j.title+'" at '+j.company+' ['+j._src+'] tags:'+(j.skills||[]).slice(0,4).join(',')
  ).join('\n');

  const allSkills = [...(p.skills?.languages||[]),...(p.skills?.frameworks||[]),...(p.skills?.tools||[]),...(p.skills?.domains||[])].join(', ');

  const prompt = 'Score these jobs for this candidate. Return ONLY JSON array.\n\nCANDIDATE: '+(p.current_role||'student')+', '+(p.experience_years||0)+'yr exp, level:'+p.level+'\nSKILLS: '+allSkills+'\nTARGET: '+(p.target_roles||[]).join(', ')+'\n\nJOBS:\n'+jobSummary+'\n\nReturn JSON array (one per job, index 0 to '+(toScore.length-1)+'):\n[{"index":0,"score":85,"reasons":["skill match"],"missing":["requires 3yr exp"]}]\nScore 0-100. Only JSON, nothing else.';

  try{
    const body = {
      contents: [{role:'user', parts:[{text: prompt}]}],
      generationConfig: { temperature: 0.15, maxOutputTokens: 700 }
    };
    const d = await callGemini(body);
    const raw = d?.candidates?.[0]?.content?.parts?.[0]?.text || '';
    const m = raw.match(/(\[[\s\S]*\])/);
    if(!m) return results;
    const scores = JSON.parse(m[1]);
    scores.forEach(s => {
      if(results[s.index]){
        results[s.index]._score = s.score || 50;
        results[s.index]._reasons = s.reasons || [];
        results[s.index]._missing = s.missing || [];
      }
    });
  } catch(e){ /* keep default scores */ }
  return results;
}

// ── Daily tracking ────────────────────────────────────────────────────────────
function saveDailyDate(){ localStorage.setItem(DAILY_SK, new Date().toDateString()); }

function checkDailyUpdate(){
  const last = localStorage.getItem(DAILY_SK);
  const today = new Date().toDateString();
  const banner = document.getElementById('daily-banner');
  const msg = document.getElementById('daily-message');
  const sub = document.getElementById('daily-sub');
  if(!last){
    banner.style.display = 'block';
    msg.textContent = 'No jobs searched yet — click Hunt to start!';
    sub.textContent = '';
    return;
  }
  banner.style.display = 'block';
  if(last !== today){
    msg.textContent = 'New day! Fresh jobs may be available';
    sub.textContent = 'Last searched: ' + last + ' · Click Refresh Now for today\'s listings';
  } else {
    msg.textContent = 'Jobs are up to date ✓';
    sub.textContent = 'Last searched: today · Results saved in browser';
  }
}

function isNewJob(dateStr){
  if(!dateStr) return false;
  return (Date.now() - new Date(dateStr).getTime()) < 48*60*60*1000;
}

// ── Resume UI helpers ─────────────────────────────────────────────────────────
function setResumeStatus(msg, type){
  const el = document.getElementById('resume-status');
  el.style.display = 'block'; el.textContent = msg; el.className = 'status-bar ' + type;
}

function setResumeProg(pct, label){
  document.getElementById('resume-prog-fill').style.width = pct + '%';
  document.getElementById('resume-prog-label').textContent = label;
}

// ── Init resume on page load ──────────────────────────────────────────────────
function initResume(){
  // Setup PDF.js
  if(window.pdfjsLib){
    pdfjsLib.GlobalWorkerOptions.workerSrc =
      'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
  }
  // Drag & drop
  const zone = document.getElementById('upload-zone');
  if(zone){
    zone.addEventListener('dragover', e=>{ e.preventDefault(); zone.classList.add('dragover'); });
    zone.addEventListener('dragleave', ()=> zone.classList.remove('dragover'));
    zone.addEventListener('drop', e=>{
      e.preventDefault(); zone.classList.remove('dragover');
      const f = e.dataTransfer.files[0];
      if(f) handleFile(f);
    });
  }
  // Restore saved API key into input
  const savedKey = localStorage.getItem(LOCAL_KEY_SK);
  const keyInput = document.getElementById('gemini-key-input');
  if(savedKey && keyInput) keyInput.value = savedKey;
  // Load saved profile
  profile = loadProfileData();
  if(profile){
    showProfileBanner(profile);
    autoFillFromProfile(profile);
    document.getElementById('resume-upload-section').style.display = 'none';
    checkDailyUpdate();
  }
}
