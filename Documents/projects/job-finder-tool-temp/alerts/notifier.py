"""Alert system for new job matches."""
import httpx
from typing import List, Dict
from rich.console import Console

from database.db import get_new_jobs, mark_notified
from app_config.settings import DISCORD_WEBHOOK

console = Console()


class AlertManager:
    def __init__(self, webhook_url: str = None):
        self.webhook = webhook_url or DISCORD_WEBHOOK

    def check_and_notify(self, keywords: List[str], since_hours: int = 24):
        """Check for new jobs and send notifications."""
        jobs = get_new_jobs(keywords, since_hours)
        if not jobs:
            console.print("[dim]No new jobs found.[/dim]")
            return

        console.print(f"[green]Found {len(jobs)} new jobs![/green]")

        # Terminal alert
        for job in jobs:
            console.print(f"  [cyan]{job['title']}[/cyan] at [green]{job['company']}[/green]")

        # Discord alert
        if self.webhook:
            import asyncio
            asyncio.run(self._send_discord(jobs))

        # Mark as notified
        mark_notified([j["job_id"] for j in jobs])

    async def _send_discord(self, jobs: List[Dict]):
        """Send Discord webhook notification."""
        content = "**New Job Matches Found!**\n\n"
        for job in jobs[:10]:
            content += f"**{job['title']}** at *{job['company']}*\n"
            content += f"Location: {job['location'] or 'Remote'} | Platform: {job['source_platform']}\n"
            content += f"Apply: {job['apply_url']}\n\n"

        try:
            async with httpx.AsyncClient() as client:
                await client.post(self.webhook, json={"content": content[:1900]})
            console.print("[green]Discord alert sent.[/green]")
        except Exception as e:
            console.print(f"[red]Discord alert failed: {e}[/red]")
