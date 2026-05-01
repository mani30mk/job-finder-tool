// ── Constants ─────────────────────────────────────────────────────────────────
const SK = 'huntr_v1';

// ── State ─────────────────────────────────────────────────────────────────────
let state = { jobs:[], saved:{}, page:1, hasMore:false, activeTab:'r', activeFilter:'all' };
let activeSources = { 
  jsearch:true, adzuna:true, remoteok:true, 
  linkedin:true, indeed:true, wellfound:true,
  greenhouse:true, lever:true, hn:true, wwr:true
};

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
  ['JSearch','Adzuna','RemoteOK','LinkedIn','Indeed','Wellfound','Greenhouse','Lever','HackerNews','WeWorkRemotely','Gemini'].forEach(src => {
    const chip = document.getElementById('st-'+src.toLowerCase().replace(/[^a-z]/g,'')+'-chip');
    const val = document.getElementById('st-'+src.toLowerCase().replace(/[^a-z]/g,'')+'-cnt');
    if(val) val.textContent = cnts[src]||0;
    if(chip) chip.style.display = cnts[src] ? '' : 'none';
  });
}

// ── Unified API Call ──────────────────────────────────────────────────────────
async function fetchUnifiedJobs(query, location, level, country, page) {
  const active = Object.entries(activeSources)
    .filter(([k,v]) => v)
    .map(([k]) => k)
    .join(',');

  const params = new URLSearchParams({
    query: query,
    page: page.toString(),
    source: active
  });
  if(location) params.append('location', location);
  if(level) params.append('level', level);
  if(country) params.append('country', country);

  const res = await fetch('/api/jobs?' + params);
  if(!res.ok){
    const err = await res.json().catch(()=>({}));
    throw new Error(err.error || `API HTTP ${res.status}`);
  }
  const d = await res.json();
  return {
    jobs: d.jobs || [],
    total: d.total || 0,
    hasMore: d.hasMore || false,
    errors: d.errors || []
  };
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

  const STEPS = ['Searching Internet...','Parsing Results...','AI Scoring...','Merging','Done'];
  setProgress(5, STEPS, 0);
  setStatus('Searching 10+ job sources across the internet...','info');

  try {
    // Single unified API call gets ALL sources
    const result = await fetchUnifiedJobs(q, loc, level, country, page);

    setProgress(50, STEPS, 1);

    let jobs = result.jobs;

    // ── AI Scoring against profile ──────────────────────────────────────
    if(profile && jobs.length > 0 && typeof scoreJobsWithProfile === 'function'){
      setStatus('⚡ Scoring jobs against your profile...','info');
      setProgress(75, STEPS, 2);
      try{
        jobs = await scoreJobsWithProfile(jobs, profile);
        jobs.sort((a,b) => (b._score||50) - (a._score||50));
      } catch(e){ /* keep unscored */ }
    }

    // Mark new jobs
    jobs.forEach(j => { if(typeof isNewJob==='function') j._isNew = isNewJob(j.posted); });

    if(fresh) state.jobs = jobs;
    else state.jobs = dedup([...state.jobs, ...jobs]);

    state.page = page + 1;
    state.hasMore = result.hasMore;
    persist();

    // Save daily date
    if(typeof saveDailyDate === 'function') saveDailyDate();
    if(typeof checkDailyUpdate === 'function') checkDailyUpdate();

    setProgress(100, STEPS, 4);
    setTimeout(hideProgress, 700);

    btn.disabled=false; btn.textContent='▶ HUNT JOBS';

    const srcCounts = {};
    jobs.forEach(j => { srcCounts[j._src] = (srcCounts[j._src]||0)+1; });
    const summary = Object.entries(srcCounts).map(([s,c])=>`${c} from ${s}`).join(', ');

    const scoreNote = profile ? ' AI-scored against your profile.' : '';
    setStatus(
      jobs.length
        ? `✓ Found ${jobs.length} jobs${fresh?'':' more'} — ${summary}.${scoreNote}${result.errors?.length?' Some sources skipped.':''}`
        : `No results. Try broader keywords or remove location filter.`,
      jobs.length ? 'ok' : 'warn'
    );

    showEl('btn-clear'); showEl('save-note');
    document.getElementById('stats-row').style.display='flex';
    document.getElementById('filter-bar').style.display='flex';
    if(state.hasMore) showEl('btn-more'); else hideEl('btn-more');

    renderCards(); updateCounts();

  } catch(e) {
    btn.disabled=false; btn.textContent='▶ HUNT JOBS';
    hideProgress();
    setStatus('Error: ' + e.message, 'err');
    console.error('[HUNTR] Search error:', e);
  }
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
  const map = {
    'JSearch':'b-jsearch', 'Adzuna':'b-adzuna', 'RemoteOK':'b-remoteok',
    'LinkedIn':'b-linkedin', 'Indeed':'b-indeed', 'Wellfound':'b-wellfound',
    'Greenhouse':'b-greenhouse', 'Lever':'b-lever', 'HackerNews':'b-hn',
    'WeWorkRemotely':'b-wwr', 'Gemini':'b-gemini'
  };
  return map[src] || 'b-type';
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
