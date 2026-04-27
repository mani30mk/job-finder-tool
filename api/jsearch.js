export default async function handler(req, res) {
  // Only allow GET requests
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const apiKey = process.env.JSEARCH_API_KEY;
  if (!apiKey) {
    return res.status(500).json({ error: 'JSEARCH_API_KEY not configured on server' });
  }

  // Forward query params from frontend
  const { query, page, num_pages, date_posted, remote_jobs_only, employment_types } = req.query;

  if (!query) {
    return res.status(400).json({ error: 'Missing required parameter: query' });
  }

  const params = new URLSearchParams({
    query,
    page: page || '1',
    num_pages: num_pages || '1',
    date_posted: date_posted || 'month',
    ...(remote_jobs_only ? { remote_jobs_only } : {}),
    ...(employment_types ? { employment_types } : {})
  });

  try {
    const response = await fetch('https://jsearch.p.rapidapi.com/search?' + params, {
      headers: {
        'X-RapidAPI-Key': apiKey,
        'X-RapidAPI-Host': 'jsearch.p.rapidapi.com'
      }
    });

    if (!response.ok) {
      const txt = await response.text();
      return res.status(response.status).json({ error: `JSearch API error: ${txt.slice(0, 200)}` });
    }

    const data = await response.json();
    return res.status(200).json(data);
  } catch (e) {
    return res.status(500).json({ error: `Server error: ${e.message}` });
  }
}
