// ── Constants ─────────────────────────────────────────────────────────────────
const SK = 'huntr_v1';

// ── State ─────────────────────────────────────────────────────────────────────
let state = { jobs:[], saved:{}, page:1, hasMore:false, activeTab:'r', activeFilter:'all' };
let activeSources = { jsearch:true, adzuna:true, remoteok:true, gemini:true };

function persist(){ try{ localStorage.setItem(SK, JSON.stringify(state)); }catch(e){} }
function restore(){
  try{
    const d = JSON.parse(localStorage.getItem(SK)||'null');
    if(d){ state = d; renderCards(); updateCounts(); }
    if(state.jobs.length>0){
      showEl('btn-clear'); showEl('save-note');
      document.getElementById('stats-row').style.display = 'flex';
      document.getElementById('filter-bar').style.display = 'flex';
      setStatus(`Restored ${state.jobs.length} jobs from last session.`,'ok');
      if(state.hasMore) showEl('btn-more');
    }
    updateCounts();
  }catch(e){}
  // Init resume module
  if(typeof initResume === 'function') initResume();
}

// ── UI ────────────────────────────────────────────────────────────────────────
function showEl(id){ const e=document.getElementById(id); if(e) e.style.display=''; }
function hideEl(id){ const e=document.getElementById(id); if(e) e.style.display='none'; }
function setStatus(msg, type='info'){
  const el = document.getElementById('status-bar');
  el.style.display = 'block';
  el.textContent = msg;
  el.className = 'status-bar ' + type;
}
function setProgress(pct, steps, activeIdx){
  document.getElementById('prog-wrap').style.display = 'block';
  document.getElementById('prog-fill').style.width = pct + '%';
  const wrap = document.getElementById('prog-steps');
  wrap.innerHTML = steps.map((s,i) =>
    `<span class="p-step ${i<activeIdx?'done':i===activeIdx?'active':''}">${i<activeIdx?'✓ ':i===activeIdx?'▶ ':''}${s}</span>`
  ).join('');
}
function hideProgress(){ hideEl('prog-wrap'); }
function toggleSrc(btn){
  const src = btn.dataset.src;
  activeSources[src] = !activeSources[src];
  btn.classList.toggle('on', activeSources[src]);
}
function updateCounts(){
  const sc = Object.keys(state.saved).length;
  document.getElementById('rc').textContent = `(${state.jobs.length})`;
  document.getElementById('sc').textContent = `(${sc})`;
  document.getElementById('st-total').textContent = state.jobs.length;
  document.getElementById('st-saved').textContent = sc;
  // per-source counts
  const cnts = {};
  state.jobs.forEach(j => { cnts[j._src] = (cnts[j._src]||0)+1; });
  ['JSearch','Adzuna','RemoteOK','Gemini'].forEach(src => {
    const chip = document.getElementById('st-'+src.toLowerCase().replace(' ','-')+'-chip');
    const val = document.getElementById('st-'+src.toLowerCase().replace(' ','-')+ (src==='Gemini'?'-cnt':''));
    if(val) val.textContent = cnts[src]||0;
    if(chip) chip.style.display = cnts[src] ? '' : 'none';
  });
}

// ── Source APIs (via serverless proxies) ──────────────────────────────────────

// JSearch (RapidAPI) — scrapes LinkedIn, Indeed, Glassdoor, ZipRecruiter
async function fetchJSearch(query, location, employmentType, remoteOnly, page){
  let q = query;
  if(location && !remoteOnly) q += ' ' + location;
  const params = new URLSearchParams({
    query: q,
    page: page,
    num_pages: '1',
    date_posted: 'month',
    ...(remoteOnly ? {remote_jobs_only:'true'} : {}),
    ...(employmentType ? {employment_types: employmentType.toUpperCase()} : {})
  });
  const res = await fetch('/api/jsearch?' + params);
  if(!res.ok){
    const err = await res.json().catch(()=>({}));
    throw new Error(err.error || `JSearch HTTP ${res.status}`);
  }
  const d = await res.json();
  return (d.data||[]).map(j => ({
    _src: 'JSearch',
    _id: 'js-' + j.job_id,
    title: j.job_title,
    company: j.employer_name,
    location: j.job_city ? `${j.job_city}, ${j.job_country||''}` : (j.job_is_remote ? 'Remote' : j.job_country||''),
    type: j.job_employment_type ? j.job_employment_type.replace('_',' ') : '',
    posted: j.job_posted_at_datetime_utc ? j.job_posted_at_datetime_utc.slice(0,10) : '',
    url: j.job_apply_link || j.job_google_link || '',
    linkedin_url: '',
    salary: j.job_min_salary ? `$${Math.round(j.job_min_salary/1000)}k–$${Math.round((j.job_max_salary||j.job_min_salary)/1000)}k` : '',
    description: j.job_description ? j.job_description.slice(0,300) + '…' : '',
    skills: j.job_required_skills || [],
    source_logo: j.employer_logo || '',
    _verified_url: true
  }));
}

// Adzuna — aggregates company sites, boards, startups
async function fetchAdzuna(query, country, location, salaryMin, page){
  const params = new URLSearchParams({
    query: query,
    country: country,
    page: page,
    ...(location ? {location: location} : {}),
    ...(salaryMin ? {salary_min: salaryMin} : {})
  });
  const res = await fetch('/api/adzuna?' + params);
  if(!res.ok){
    const err = await res.json().catch(()=>({}));
    throw new Error(err.error || `Adzuna HTTP ${res.status}`);
  }
  const d = await res.json();
  return (d.results||[]).map(j => ({
    _src: 'Adzuna',
    _id: 'az-' + j.id,
    title: j.title,
    company: j.company?.display_name || 'Unknown',
    location: j.location?.display_name || '',
    type: j.contract_time ? (j.contract_time==='full_time'?'Full-time':'Part-time') : '',
    posted: j.created ? j.created.slice(0,10) : '',
    url: j.redirect_url || '',
    linkedin_url: '',
    salary: j.salary_min ? `£${Math.round(j.salary_min/1000)}k–£${Math.round((j.salary_max||j.salary_min)/1000)}k` : '',
    description: j.description ? j.description.slice(0,300) + '…' : '',
    skills: [],
    _verified_url: true
  }));
}

// RemoteOK — free public API, real-time remote jobs from startups
async function fetchRemoteOK(query){
  const res = await fetch('https://remoteok.com/api', {
    headers:{ 'User-Agent': 'HUNTR Job Finder (personal use)' }
  });
  if(!res.ok) throw new Error(`RemoteOK HTTP ${res.status}`);
  const d = await res.json();
  const jobs = (Array.isArray(d) ? d : []).filter(j => j.slug); // skip header entry
  const q = query.toLowerCase();
  return jobs
    .filter(j => {
      const text = ((j.position||'') + ' ' + (j.tags||[]).join(' ') + ' ' + (j.company||'')).toLowerCase();
      return q.split(' ').some(word => word.length>2 && text.includes(word));
    })
    .slice(0, 20)
    .map(j => ({
      _src: 'RemoteOK',
      _id: 'ro-' + j.id,
      title: j.position || j.slug,
      company: j.company || 'Unknown',
      location: 'Remote',
      type: 'Full-time',
      posted: j.date ? j.date.slice(0,10) : '',
      url: j.url || `https://remoteok.com/remote-jobs/${j.slug}`,
      linkedin_url: '',
      salary: j.salary || '',
      description: j.description ? j.description.replace(/<[^>]+>/g,'').slice(0,300) + '…' : '',
      skills: j.tags || [],
      _verified_url: true
    }));
}

// Gemini — AI fallback + enrichment (via serverless proxy)
async function geminiSearch(query, level, location, skills, page){
  const levelMap = {internship:'internship/fresher',entry:'entry-level 0-2yr',mid:'mid-level 2-5yr',senior:'senior 5+yr','':'any level'};
  const lv = levelMap[level]||'any level';
  const pageHint = page>1 ? `Page ${page}: find DIFFERENT jobs not in previous pages.` : '';
  const prompt = `You are a job search assistant. Use Google Search to find REAL current job postings (last 30 days).

Search: "${query}" ${lv} jobs${location?' in '+location:''}${skills?', skills: '+skills:''}.
${pageHint}

Search sources: LinkedIn, Greenhouse.io, Lever.co, Workday, Wellfound/AngelList, company career pages.

Return ONLY a valid JSON array with 6 objects. No prose, no markdown:
[{"title":"","company":"","location":"","type":"Internship|Full-time|Contract","posted":"YYYY-MM-DD","url":"ONLY use the exact URL you found — never invent one. Use company careers page if specific URL unknown.","skills":[""],"description":"2-3 sentences","salary":"","source":"LinkedIn|Greenhouse|Lever|Company Career Page|Wellfound"}]

RULES: Never fabricate numeric job IDs. Prefer greenhouse.io, lever.co, workday URLs. If no verified URL found, use https://careers.[company].com or leave empty.`;

  const body = {
    contents:[{role:'user',parts:[{text:prompt}]}],
    generationConfig:{ temperature:0.15, maxOutputTokens:2500 },
    tools:[{google_search:{}}]
  };
  
  let d;
  if(typeof callGemini === 'function'){
    d = await callGemini(body);
  } else {
    // Fallback if resume.js isn't loaded for some reason
    const res = await fetch('/api/gemini', {
      method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)
    });
    if(!res.ok){
      const e = await res.json().catch(()=>({}));
      throw new Error(e.error || `HTTP ${res.status}`);
    }
    d = await res.json();
  }
  
  const text = d?.candidates?.[0]?.content?.parts?.[0]?.text||'';
  const m = text.match(/```(?:json)?\s*(\[[\s\S]*?\])\s*```/) || text.match(/(\[[\s\S]*\])/);
  if(!m) return [];
  try{
    return JSON.parse(m[1]).map((j,i) => ({
      _src: 'Gemini',
      _id: 'gm-' + Date.now() + i,
      title: j.title||'',
      company: j.company||'',
      location: j.location||'',
      type: j.type||'',
      posted: j.posted||'',
      url: j.url||'',
      linkedin_url: '',
      salary: j.salary||'',
      description: j.description||'',
      skills: j.skills||[],
      _verified_url: false // Gemini URLs still need validation
    }));
  }catch(e){ return []; }
}

// ── Deduplication ─────────────────────────────────────────────────────────────
function dedup(jobs){
  const seen = new Set();
  return jobs.filter(j => {
    const key = (j.title + '|' + j.company).toLowerCase().replace(/\s+/g,'');
    if(seen.has(key)) return false;
    seen.add(key); return true;
  });
}

// ── Main Search ───────────────────────────────────────────────────────────────
async function doSearch(fresh){
  const q = document.getElementById('q').value.trim();
  if(!q){ setStatus('Enter a role or keyword first.','warn'); return; }

  const level = document.getElementById('level').value;
  const loc   = document.getElementById('loc').value.trim();
  const skills= document.getElementById('skills').value.trim();
  const salaryMin = document.getElementById('salary-min').value.trim();
  const jtype = document.getElementById('jtype').value;
  const country = document.getElementById('country').value;
  const perPage = parseInt(document.getElementById('per-page').value)||20;
  const page  = fresh ? 1 : state.page;

  const isRemote = loc.toLowerCase().includes('remote');

  if(fresh){ state.jobs=[]; state.page=1; }

  const btn = document.getElementById('btn-search');
  btn.disabled=true; btn.textContent='⏳ HUNTING…';
  hideEl('btn-more');

  const STEPS = ['JSearch','Adzuna','RemoteOK','Gemini AI','Merging'];
  setProgress(5, STEPS, 0);
  setStatus('Fetching from all sources simultaneously…','info');

  let allJobs = [];
  let sourceErrors = [];

  // ── Parallel fetch from all sources ──────────────────────────────────────
  const promises = [];

  if(activeSources.jsearch){
    promises.push(
      fetchJSearch(q, loc, jtype, isRemote, page)
        .then(jobs => { allJobs.push(...jobs); setProgress(30, STEPS, 1); })
        .catch(e => { sourceErrors.push(`JSearch: ${e.message}`); })
    );
  }

  if(activeSources.adzuna){
    promises.push(
      fetchAdzuna(q, country, loc, salaryMin, page)
        .then(jobs => { allJobs.push(...jobs); setProgress(55, STEPS, 2); })
        .catch(e => { sourceErrors.push(`Adzuna: ${e.message}`); })
    );
  }

  if(activeSources.remoteok){
    promises.push(
      fetchRemoteOK(q)
        .then(jobs => { allJobs.push(...jobs); setProgress(70, STEPS, 3); })
        .catch(e => { sourceErrors.push(`RemoteOK: ${e.message}`); })
    );
  }

  if(activeSources.gemini){
    promises.push(
      geminiSearch(q, level, loc, skills, page)
        .then(jobs => { allJobs.push(...jobs); setProgress(85, STEPS, 4); })
        .catch(e => { sourceErrors.push(`Gemini: ${e.message}`); })
    );
  }

  await Promise.allSettled(promises);

  setProgress(95, STEPS, 4);

  // ── Dedup & merge ────────────────────────────────────────────────────────
  const before = allJobs.length;
  let deduped = dedup(allJobs);
  const removed = before - deduped.length;

  // ── AI Scoring against profile ──────────────────────────────────────────
  if(profile && deduped.length > 0 && typeof scoreJobsWithProfile === 'function'){
    setStatus('⚡ Scoring jobs against your profile…','info');
    try{
      deduped = await scoreJobsWithProfile(deduped, profile);
      deduped.sort((a,b) => (b._score||50) - (a._score||50));
    } catch(e){ /* keep unscored */ }
  }

  // Mark new jobs
  deduped.forEach(j => { if(typeof isNewJob==='function') j._isNew = isNewJob(j.posted); });

  if(fresh) state.jobs = deduped;
  else state.jobs = dedup([...state.jobs, ...deduped]);

  state.page = page + 1;
  state.hasMore = allJobs.length >= 15;
  persist();

  // Save daily date
  if(typeof saveDailyDate === 'function') saveDailyDate();
  if(typeof checkDailyUpdate === 'function') checkDailyUpdate();

  setProgress(100, STEPS, 5);
  setTimeout(hideProgress, 700);

  btn.disabled=false; btn.textContent='▶ HUNT JOBS';

  const srcCounts = {};
  deduped.forEach(j => { srcCounts[j._src] = (srcCounts[j._src]||0)+1; });
  const summary = Object.entries(srcCounts).map(([s,c])=>`${c} from ${s}`).join(', ');

  const scoreNote = profile ? ' AI-scored against your profile.' : '';
  setStatus(
    deduped.length
      ? `✓ Found ${deduped.length} jobs${fresh?'':' more'} — ${summary}.${scoreNote}${sourceErrors.length?' Some sources skipped.':''}`
      : `No results. ${sourceErrors.join(' | ')}`,
    deduped.length ? 'ok' : 'warn'
  );

  if(removed>0){
    const dn = document.getElementById('dedup-note');
    dn.style.display=''; dn.textContent=`✦ ${removed} duplicate${removed>1?'s':''} removed across sources`;
  }

  showEl('btn-clear'); showEl('save-note');
  document.getElementById('stats-row').style.display='flex';
  document.getElementById('filter-bar').style.display='flex';
  if(state.hasMore) showEl('btn-more'); else hideEl('btn-more');

  renderCards(); updateCounts();
}

// ── Render ─────────────────────────────────────────────────────────────────────
function renderCards(){
  const wrap = document.getElementById('cards');
  let jobs = state.activeTab==='s'
    ? state.jobs.filter(j => state.saved[j._id])
    : state.jobs;
  if(state.activeFilter && state.activeFilter!=='all'){
    jobs = jobs.filter(j => j._src===state.activeFilter);
  }
  if(!jobs.length){
    wrap.innerHTML = `<div class="empty"><div class="empty-icon">${state.activeTab==='s'?'★':'⚡'}</div>${state.activeTab==='s'?'No saved jobs yet.':'No results for this filter.'}</div>`;
    return;
  }
  wrap.innerHTML = jobs.map((j,i) => cardHTML(j,i)).join('');
}

function h(s){ return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

function isValidUrl(url){
  if(!url) return false;
  try{
    const u = new URL(url);
    return (u.protocol==='https:'||u.protocol==='http:') && u.hostname!=='example.com' && !/\[|\]/.test(url);
  }catch(e){ return false; }
}

function fallbackLinks(j){
  const q = encodeURIComponent(`${j.title} ${j.company}`);
  return {
    google: `https://www.google.com/search?q=${q}+job+apply`,
    linkedin: `https://www.linkedin.com/jobs/search/?keywords=${q}`,
    indeed: `https://www.indeed.com/jobs?q=${encodeURIComponent(j.title)}&l=${encodeURIComponent(j.location||'')}`
  };
}

function srcBadgeClass(src){
  return {JSearch:'b-jsearch',Adzuna:'b-adzuna',RemoteOK:'b-remoteok',Gemini:'b-gemini'}[src]||'b-type';
}

function cardHTML(j, i){
  const sv = !!state.saved[j._id];
  const isRemote = /remote|anywhere/i.test(j.location||'');
  const skills = (j.skills||[]).slice(0,7);
  const delay = Math.min(i,10)*0.04;
  const hasUrl = isValidUrl(j.url);
  const hasLi  = isValidUrl(j.linkedin_url);
  const fb = fallbackLinks(j);

  // Score display
  const sc = j._score || 0;
  const hasScore = profile && sc > 0;
  const pillClass = sc>=80?'sp-excellent':sc>=60?'sp-good':sc>=40?'sp-fair':'sp-poor';

  let applyBtns = '';
  if(hasUrl){
    applyBtns += `<a class="btn-apply" href="${h(j.url)}" target="_blank" rel="noopener">Apply →</a>`;
  } else {
    applyBtns += `<a class="btn-apply fallback" href="${fb.google}" target="_blank" rel="noopener" title="Search Google for this job">🔍 Find Job</a>`;
  }
  if(hasLi){
    applyBtns += `<a class="btn-li" href="${h(j.linkedin_url)}" target="_blank" rel="noopener">LinkedIn</a>`;
  }
  applyBtns += `<a class="btn-fallback" href="${fb.indeed}" target="_blank" rel="noopener" title="Search Indeed">Indeed</a>`;
  applyBtns += `<a class="btn-fallback" href="${fb.linkedin}" target="_blank" rel="noopener" title="Search LinkedIn">LinkedIn Search</a>`;

  // Match reasons HTML
  let matchHtml = '';
  if(hasScore && ((j._reasons||[]).length || (j._missing||[]).length)){
    matchHtml = '<div class="match-reasons">' +
      (j._reasons||[]).map(r=>'<div class="reason reason-ok">✓ '+h(r)+'</div>').join('') +
      (j._missing||[]).map(r=>'<div class="reason reason-miss">✗ '+h(r)+'</div>').join('') +
      '</div>';
  }

  return `
<div class="card" id="c-${j._id}" style="animation-delay:${delay}s">
  <div class="card-top">
    <div class="card-left">
      <div class="card-title" title="${h(j.title)}">${h(j.title)}</div>
      <div class="card-meta">
        <span class="card-company">${h(j.company)}</span>
        <span class="dot-sep">·</span>
        <span class="card-loc">${h(j.location||'')}</span>
        ${isRemote?'<span class="badge b-remote">Remote</span>':''}
        ${j.type?`<span class="badge b-type">${h(j.type)}</span>`:''}
        <span class="badge ${srcBadgeClass(j._src)}">${h(j._src)}</span>
        ${j.salary?`<span class="badge b-salary">💰 ${h(j.salary)}</span>`:''}
        ${j._isNew?'<span class="badge b-new">🆕 New</span>':''}
        ${!hasUrl&&!hasLi&&j._src==='Gemini'?'<span class="badge" style="background:rgba(255,204,0,.07);color:var(--warn);border:1px solid rgba(255,204,0,.2)">⚠ link unverified</span>':''}
      </div>
    </div>
    <div class="card-actions">
      ${hasScore?`<span class="score-pill ${pillClass}">${sc}%</span>`:''}
      <button class="btn-star${sv?' on':''}" onclick="toggleSave('${j._id}')" title="${sv?'Unsave':'Save'}">${sv?'★':'☆'}</button>
      <button class="btn-exp" onclick="toggleExp('${j._id}')">▼</button>
    </div>
  </div>
  <div class="card-body" id="b-${j._id}">
    ${matchHtml}
    ${j.description?`<p class="card-desc">${h(j.description)}</p>`:''}
    ${skills.length?`<div class="card-skills">${skills.map(s=>`<span class="skill-tag">${h(s)}</span>`).join('')}</div>`:''}
    <div class="card-footer">
      <span class="card-posted">${j.posted?'📅 '+h(j.posted):''}</span>
      <div class="apply-btns">${applyBtns}</div>
    </div>
  </div>
</div>`;
}

function toggleExp(id){
  const b=document.getElementById('b-'+id);
  const c=document.getElementById('c-'+id);
  const btn=c.querySelector('.btn-exp');
  const open=b.classList.toggle('open');
  btn.textContent=open?'▲':'▼';
}
function toggleSave(id){
  if(state.saved[id]) delete state.saved[id];
  else state.saved[id]=true;
  persist();
  const c=document.getElementById('c-'+id);
  if(c){
    const btn=c.querySelector('.btn-star');
    btn.className='btn-star'+(state.saved[id]?' on':'');
    btn.textContent=state.saved[id]?'★':'☆';
  }
  updateCounts();
}
function switchTab(t){
  state.activeTab=t;
  document.getElementById('tab-r').classList.toggle('active',t==='r');
  document.getElementById('tab-s').classList.toggle('active',t==='s');
  renderCards();
}
function filterBy(btn, f){
  state.activeFilter=f;
  document.querySelectorAll('.filter-btn').forEach(b=>b.classList.toggle('active',b.dataset.f===f));
  renderCards();
}
function clearAll(){
  if(!confirm('Clear all results? Saved jobs will be kept.')) return;
  state.jobs=[]; state.page=1; state.hasMore=false;
  persist(); renderCards(); updateCounts();
  hideEl('stats-row'); hideEl('save-note'); hideEl('btn-clear'); hideEl('btn-more');
  hideEl('dedup-note'); hideEl('filter-bar');
  document.getElementById('status-bar').style.display='none';
}

document.addEventListener('keydown', e=>{
  if(e.key==='Enter' && ['INPUT','SELECT'].includes(document.activeElement.tagName)) doSearch(true);
});

restore();
