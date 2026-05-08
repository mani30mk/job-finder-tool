import urllib.request
import json

req = urllib.request.Request('https://api.github.com/repos/mani30mk/job-finder-tool/actions/runs')
req.add_header('Accept', 'application/vnd.github.v3+json')
with urllib.request.urlopen(req) as res:
    data = json.loads(res.read())
    print("Latest runs:")
    for r in data.get("workflow_runs", [])[:3]:
        print(f"- {r['name']} ({r['status']}/{r['conclusion']}): {r['html_url']}")
