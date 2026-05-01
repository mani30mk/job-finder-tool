export default async function handler(req, res) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const appId = process.env.ADZUNA_APP_ID;
  const appKey = process.env.ADZUNA_APP_KEY;
  if (!appId || !appKey) {
    return res.status(500).json({ error: 'ADZUNA_APP_ID or ADZUNA_APP_KEY not configured on server' });
  }

  const { query, country, page, location, salary_min } = req.query;

  if (!query) {
    return res.status(400).json({ error: 'Missing required parameter: query' });
  }

  const c = country || 'in';
  const p = page || '1';

  const params = new URLSearchParams({
    app_id: appId,
    app_key: appKey,
    results_per_page: '20',
    what: query,
    content_type: 'application/json',
    ...(location ? { where: location } : {}),
    ...(salary_min ? { salary_min } : {})
  });

  try {
    const url = `https://api.adzuna.com/v1/api/jobs/${c}/search/${p}?${params}`;
    const response = await fetch(url, {
      headers: {
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
      }
    });

    if (!response.ok) {
      const txt = await response.text();
      return res.status(response.status).json({ error: `Adzuna API error: ${txt.slice(0, 200)}` });
    }

    const data = await response.json();
    return res.status(200).json(data);
  } catch (e) {
    return res.status(500).json({ error: `Server error: ${e.message}` });
  }
}
