// /api/jobs.js — UNIFIED JOB SCRAPER (replaces all individual API files)

export default async function handler(req, res) {
    if (req.method !== 'GET') {
        return res.status(405).json({ error: 'Method not allowed' });
    }

    const { query, location, page, level, country } = req.query;
    if (!query) {
        return res.status(400).json({ error: 'Missing required parameter: query' });
    }

    const p = parseInt(page) || 1;
    const allJobs = [];
    const errors = [];

    // ── Helper: JSearch ──────────────────────────────────────────────────────
    async function fetchJSearch(q, loc, pageNum) {
        const apiKey = process.env.JSEARCH_API_KEY;
        if (!apiKey) throw new Error('JSEARCH_API_KEY not configured');

        let searchQ = q;
        if (loc && !loc.toLowerCase().includes('remote')) searchQ += ' ' + loc;

        const params = new URLSearchParams({
            query: searchQ,
            page: pageNum.toString(),
            num_pages: '1',
            date_posted: 'month'
        });

        const response = await fetch('https://jsearch.p.rapidapi.com/search?' + params, {
            headers: {
                'X-RapidAPI-Key': apiKey,
                'X-RapidAPI-Host': 'jsearch.p.rapidapi.com'
            }
        });
        if (!response.ok) throw new Error(`JSearch HTTP ${response.status}`);
        const d = await response.json();
        return (d.data || []).map(j => ({
            _src: 'JSearch', _id: 'js-' + j.job_id,
            title: j.job_title, company: j.employer_name,
            location: j.job_city ? `${j.job_city}, ${j.job_country}` : (j.job_is_remote ? 'Remote' : j.job_country || ''),
            type: j.job_employment_type ? j.job_employment_type.replace('_', ' ') : '',
            posted: j.job_posted_at_datetime_utc ? j.job_posted_at_datetime_utc.slice(0, 10) : '',
            url: j.job_apply_link || j.job_google_link || '',
            salary: j.job_min_salary ? `$${Math.round(j.job_min_salary / 1000)}k–$${Math.round((j.job_max_salary || j.job_min_salary) / 1000)}k` : '',
            description: j.job_description ? j.job_description.slice(0, 300) + '…' : '',
            skills: j.job_required_skills || [],
            _verified_url: true
        }));
    }

    // ── Helper: Adzuna ───────────────────────────────────────────────────────
    async function fetchAdzuna(q, ctry, loc, pageNum) {
        const appId = process.env.ADZUNA_APP_ID;
        const appKey = process.env.ADZUNA_APP_KEY;
        if (!appId || !appKey) throw new Error('Adzuna credentials not configured');

        const params = new URLSearchParams({
            app_id: appId, app_key: appKey,
            results_per_page: '20', what: q
        });
        if (loc) params.append('where', loc);

        const response = await fetch(`https://api.adzuna.com/v1/api/jobs/${ctry || 'us'}/search/${pageNum}?${params}`);
        if (!response.ok) throw new Error(`Adzuna HTTP ${response.status}`);
        const d = await response.json();
        return (d.results || []).map(j => ({
            _src: 'Adzuna', _id: 'az-' + j.id,
            title: j.title, company: j.company?.display_name || 'Unknown',
            location: j.location?.display_name || '',
            type: j.contract_time ? (j.contract_time === 'full_time' ? 'Full-time' : 'Part-time') : '',
            posted: j.created ? j.created.slice(0, 10) : '',
            url: j.redirect_url || '',
            salary: j.salary_min ? `£${Math.round(j.salary_min / 1000)}k–£${Math.round((j.salary_max || j.salary_min) / 1000)}k` : '',
            description: j.description ? j.description.slice(0, 300) + '…' : '',
            skills: [], _verified_url: true
        }));
    }

    // ── Helper: RemoteOK ─────────────────────────────────────────────────────
    async function fetchRemoteOK(q) {
        const response = await fetch('https://remoteok.com/api', {
            headers: { 'User-Agent': 'HUNTR Job Finder (personal use)' }
        });
        if (!response.ok) throw new Error(`RemoteOK HTTP ${response.status}`);
        const d = await response.json();
        const jobs = (Array.isArray(d) ? d : []).filter(j => j.slug);
        const cleanQ = q.toLowerCase().replace(/,/g, '');
        const queryWords = cleanQ.split(' ').filter(w => w.length > 2);
        return jobs
            .filter(j => {
                const text = ((j.position || '') + ' ' + (j.tags || []).join(' ') + ' ' + (j.company || '')).toLowerCase();
                return queryWords.some(word => text.includes(word));
            })
            .slice(0, 20)
            .map(j => ({
                _src: 'RemoteOK', _id: 'ro-' + j.id,
                title: j.position || j.slug, company: j.company || 'Unknown',
                location: 'Remote', type: 'Full-time',
                posted: j.date ? j.date.slice(0, 10) : '',
                url: j.url || `https://remoteok.com/remote-jobs/${j.slug}`,
                salary: j.salary || '',
                description: j.description ? j.description.replace(/<[^>]+>/g, '').slice(0, 300) + '…' : '',
                skills: j.tags || [], _verified_url: true
            }));
    }

    // ── Helper: LinkedIn (public, no auth) ───────────────────────────────────
    async function fetchLinkedIn(q, loc, pageNum, lvl) {
        const locParam = loc ? `&location=${encodeURIComponent(loc)}` : '';
        const lvlParam = lvl === 'internship' ? '&f_E=1' : lvl === 'entry' ? '&f_E=2' : lvl === 'mid' ? '&f_E=3%2C4' : '';
        const url = `https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=${encodeURIComponent(q)}${locParam}${lvlParam}&start=${(pageNum - 1) * 25}`;

        const response = await fetch(url, {
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1', 'Connection': 'keep-alive'
            }
        });
        if (!response.ok) throw new Error(`LinkedIn HTTP ${response.status}`);

        const html = await response.text();
        const jobs = [];
        const regex = /<li[^>]*data-entity-urn="urn:li:jobPosting:(\d+)"[^>]*>[\s\S]*?<\/li>/g;
        let match;
        while ((match = regex.exec(html)) !== null) {
            const card = match[0];
            const jobId = match[1];
            const titleMatch = card.match(/<a[^>]*class="base-card__full-link"[^>]*>([^<]*)<\/a>/);
            const companyMatch = card.match(/<a[^>]*class="hidden-nested-link"[^>]*>([^<]*)<\/a>/);
            const locMatch = card.match(/<span[^>]*class="job-search-card__location"[^>]*>([^<]*)<\/span>/);
            const timeMatch = card.match(/<time[^>]*datetime="([^"]*)"/);
            if (titleMatch) {
                jobs.push({
                    _src: 'LinkedIn', _id: 'li-' + jobId,
                    title: titleMatch[1].trim(), company: companyMatch ? companyMatch[1].trim() : 'Unknown',
                    location: locMatch ? locMatch[1].trim() : '', type: '',
                    posted: timeMatch ? timeMatch[1].slice(0, 10) : '',
                    url: `https://www.linkedin.com/jobs/view/${jobId}`,
                    description: '', salary: '', skills: [], _verified_url: true
                });
            }
        }
        return jobs;
    }

    // ── Helper: Indeed ───────────────────────────────────────────────────────
    async function fetchIndeed(q, loc, pageNum, lvl) {
        const lvlParam = lvl === 'internship' ? '&jt=internship' : '';
        const url = `https://www.indeed.com/jobs?q=${encodeURIComponent(q)}&l=${encodeURIComponent(loc || '')}${lvlParam}&start=${(pageNum - 1) * 10}`;

        const response = await fetch(url, {
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5'
            }
        });
        if (!response.ok) throw new Error(`Indeed HTTP ${response.status}`);

        const html = await response.text();
        const jobs = [];
        const regex = /<div[^>]*class="job_seen_beacon"[^>]*>[\s\S]*?<\/div>\s*<\/div>/g;
        let match;
        while ((match = regex.exec(html)) !== null) {
            const card = match[0];
            const titleMatch = card.match(/<h2[^>]*class="jobTitle"[^>]*>(?:<span>)?([^<]*)<\/span>?<\/h2>/);
            const companyMatch = card.match(/<span[^>]*class="companyName"[^>]*>([^<]*)<\/span>/);
            const locMatch = card.match(/<div[^>]*class="companyLocation"[^>]*>([^<]*)<\/div>/);
            const salaryMatch = card.match(/<div[^>]*class="metadata salary-snippet-container"[^>]*>([^<]*)<\/div>/);
            const timeMatch = card.match(/<span[^>]*class="date"[^>]*>([^<]*)<\/span>/);
            const linkMatch = card.match(/<a[^>]*href="(\/rc\/clk\?[^"]*)"/);
            if (titleMatch) {
                jobs.push({
                    _src: 'Indeed', _id: 'in-' + Math.random().toString(36).slice(2),
                    title: titleMatch[1].trim(), company: companyMatch ? companyMatch[1].trim() : 'Unknown',
                    location: locMatch ? locMatch[1].trim() : '', type: '',
                    posted: timeMatch ? timeMatch[1].trim() : '',
                    url: linkMatch ? 'https://www.indeed.com' + linkMatch[1] : '',
                    salary: salaryMatch ? salaryMatch[1].trim() : '',
                    description: '', skills: [], _verified_url: true
                });
            }
        }
        return jobs;
    }

    // ── Helper: Wellfound (AngelList) ────────────────────────────────────────
    async function fetchWellfound(q, loc, pageNum) {
        const url = `https://wellfound.com/api/jobs?query=${encodeURIComponent(q)}&location=${encodeURIComponent(loc || 'Remote')}&page=${pageNum}`;
        const response = await fetch(url, {
            headers: { 'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json' }
        });
        if (!response.ok) throw new Error(`Wellfound HTTP ${response.status}`);
        const d = await response.json();
        return (d.jobs || []).map(j => ({
            _src: 'Wellfound', _id: 'wf-' + j.id,
            title: j.title, company: j.startup?.name || 'Unknown',
            location: j.locations?.map(l => l.name).join(', ') || 'Remote',
            type: j.jobType || '',
            posted: j.createdAt ? j.createdAt.slice(0, 10) : '',
            url: `https://wellfound.com/jobs/${j.id}`,
            salary: j.compensation ? `$${j.compensation.min}–$${j.compensation.max}` : '',
            description: j.description ? j.description.slice(0, 300) + '…' : '',
            skills: j.skills || [], _verified_url: true
        }));
    }

    // ── Helper: Greenhouse ───────────────────────────────────────────────────
    async function fetchGreenhouse(q, pageNum) {
        const boards = ['stripe', 'airbnb', 'netflix', 'spotify', 'uber', 'meta', 'openai', 'anthropic'];
        const allJobs = [];
        for (const board of boards.slice(0, 4)) {
            try {
                const response = await fetch(`https://boards-api.greenhouse.io/v1/boards/${board}/jobs`, {
                    headers: { 'User-Agent': 'HUNTR Job Finder (personal use)' }
                });
                if (!response.ok) continue;
                const d = await response.json();
                const cleanQ = q.toLowerCase().replace(/,/g, '');
                const queryWords = cleanQ.split(' ').filter(w => w.length > 2);
                const filtered = (d.jobs || []).filter(j => {
                    const text = (j.title + ' ' + (j.location?.name || '')).toLowerCase();
                    return queryWords.some(word => text.includes(word));
                });
                allJobs.push(...filtered.map(j => ({
                    _src: 'Greenhouse', _id: 'gh-' + j.id,
                    title: j.title, company: board.charAt(0).toUpperCase() + board.slice(1),
                    location: j.location?.name || 'Remote',
                    type: j.metadata?.find(m => m.name === 'Employment Type')?.value || '',
                    posted: j.updated_at ? j.updated_at.slice(0, 10) : '',
                    url: j.absolute_url,
                    description: j.content ? j.content.replace(/<[^>]+>/g, '').slice(0, 300) + '…' : '',
                    salary: '', skills: [], _verified_url: true
                })));
            } catch (e) { }
        }
        return allJobs;
    }

    // ── Helper: Lever ────────────────────────────────────────────────────────
    async function fetchLever(q, pageNum) {
        const companies = ['notion', 'figma', 'linear', 'vercel', 'supabase', 'render'];
        const allJobs = [];
        for (const company of companies.slice(0, 4)) {
            try {
                const response = await fetch(`https://api.lever.co/v0/postings/${company}?mode=json`, {
                    headers: { 'User-Agent': 'HUNTR Job Finder (personal use)' }
                });
                if (!response.ok) continue;
                const d = await response.json();
                const cleanQ = q.toLowerCase().replace(/,/g, '');
                const queryWords = cleanQ.split(' ').filter(w => w.length > 2);
                const filtered = (Array.isArray(d) ? d : []).filter(j => {
                    const text = (j.text + ' ' + (j.categories?.location || '')).toLowerCase();
                    return queryWords.some(word => text.includes(word));
                });
                allJobs.push(...filtered.map(j => ({
                    _src: 'Lever', _id: 'lv-' + j.id,
                    title: j.text, company: company.charAt(0).toUpperCase() + company.slice(1),
                    location: j.categories?.location || 'Remote',
                    type: j.categories?.commitment || '',
                    posted: j.createdAt ? j.createdAt.slice(0, 10) : '',
                    url: j.applyUrl || j.hostedUrl,
                    description: j.description ? j.description.replace(/<[^>]+>/g, '').slice(0, 300) + '…' : '',
                    salary: '', skills: j.tags || [], _verified_url: true
                })));
            } catch (e) { }
        }
        return allJobs;
    }

    // ── Helper: Hacker News "Who is Hiring" ──────────────────────────────────
    async function fetchHN(q, pageNum) {
        try {
            const response = await fetch('https://hn.algolia.com/api/v1/search_by_date?tags=story&query=%22Who%20is%20hiring%22&hitsPerPage=1', {
                headers: { 'User-Agent': 'HUNTR Job Finder' }
            });
            if (!response.ok) return [];
            const data = await response.json();
            const postId = data.hits[0]?.objectID;
            if (!postId) return [];

            const commentsRes = await fetch(`https://hn.algolia.com/api/v1/search?tags=comment,story_${postId}&hitsPerPage=100`, {
                headers: { 'User-Agent': 'HUNTR Job Finder' }
            });
            if (!commentsRes.ok) return [];
            const comments = await commentsRes.json();
            const cleanQ = q.toLowerCase().replace(/,/g, '');
            const queryWords = cleanQ.split(' ').filter(w => w.length > 2);

            return (comments.hits || [])
                .filter(c => c.text && queryWords.some(w => c.text.toLowerCase().includes(w)))
                .slice(0, 20)
                .map((c, i) => ({
                    _src: 'HackerNews', _id: 'hn-' + c.objectID,
                    title: c.text.split('\n')[0].slice(0, 80),
                    company: 'Startup (HN)', location: 'Remote / Various', type: '',
                    posted: new Date(c.created_at).toISOString().slice(0, 10),
                    url: `https://news.ycombinator.com/item?id=${c.objectID}`,
                    description: c.text ? c.text.slice(0, 300) + '…' : '',
                    salary: '', skills: [], _verified_url: true
                }));
        } catch (e) { return []; }
    }

    // ── Helper: We Work Remotely ─────────────────────────────────────────────
    async function fetchWWR(q, pageNum) {
        try {
            const response = await fetch('https://weworkremotely.com/remote-jobs/search?term=' + encodeURIComponent(q), {
                headers: { 'User-Agent': 'Mozilla/5.0' }
            });
            if (!response.ok) throw new Error(`WWR HTTP ${response.status}`);
            const html = await response.text();
            const jobs = [];
            const regex = /<li class="feature--">[\s\S]*?<\/li>/g;
            let match;
            while ((match = regex.exec(html)) !== null) {
                const card = match[0];
                const titleMatch = card.match(/<span class="title">([^<]*)<\/span>/);
                const companyMatch = card.match(/<span class="company">([^<]*)<\/span>/);
                const linkMatch = card.match(/<a href="([^"]*)"/);
                if (titleMatch) {
                    jobs.push({
                        _src: 'WeWorkRemotely', _id: 'wwr-' + Math.random().toString(36).slice(2),
                        title: titleMatch[1].trim(), company: companyMatch ? companyMatch[1].trim() : 'Unknown',
                        location: 'Remote', type: 'Full-time', posted: '',
                        url: linkMatch ? 'https://weworkremotely.com' + linkMatch[1] : '',
                        description: '', salary: '', skills: [], _verified_url: true
                    });
                }
            }
            return jobs;
        } catch (e) { return []; }
    }

    // ── Execute all sources in parallel ──────────────────────────────────────
    const sources = ['jsearch', 'adzuna', 'remoteok', 'linkedin', 'indeed', 'wellfound', 'greenhouse', 'lever', 'hn', 'wwr'];

    const promises = sources.map(async (src) => {
        try {
            let jobs = [];
            switch (src) {
                case 'jsearch': jobs = await fetchJSearch(query, location, p); break;
                case 'adzuna': jobs = await fetchAdzuna(query, country || 'us', location, p); break;
                case 'remoteok': jobs = await fetchRemoteOK(query); break;
                case 'linkedin': jobs = await fetchLinkedIn(query, location, p, level); break;
                case 'indeed': jobs = await fetchIndeed(query, location, p, level); break;
                case 'wellfound': jobs = await fetchWellfound(query, location, p); break;
                case 'greenhouse': jobs = await fetchGreenhouse(query, p); break;
                case 'lever': jobs = await fetchLever(query, p); break;
                case 'hn': jobs = await fetchHN(query, p); break;
                case 'wwr': jobs = await fetchWWR(query, p); break;
            }
            allJobs.push(...jobs);
        } catch (e) {
            errors.push(`${src}: ${e.message}`);
        }
    });

    await Promise.allSettled(promises);

    // Deduplicate
    const seen = new Set();
    const deduped = allJobs.filter(j => {
        const key = (j.title + '|' + j.company).toLowerCase().replace(/\s+/g, '');
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
    });

    return res.status(200).json({
        jobs: deduped,
        total: deduped.length,
        sources: sources.length,
        errors: errors.length > 0 ? errors : undefined,
        page: p,
        hasMore: deduped.length >= 10
    });
}