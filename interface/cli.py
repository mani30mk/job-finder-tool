"""Rich terminal interface for job search."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

import sqlite3
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from database.db import search_jobs, get_stats

console = Console()


def display_jobs(keywords: str, location: str = None, job_type: str = None, limit: int = 50):
    """Search and display jobs in a beautiful table."""
    rows = search_jobs(keywords, location, job_type, limit)

    if not rows:
        console.print(Panel("[yellow]No jobs found matching your criteria.[/yellow]", title="Results"))
        return

    table = Table(
        title=f"[bold cyan]Found {len(rows)} Jobs[/bold cyan]",
        show_lines=True,
        header_style="bold white on blue"
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Title", style="bright_cyan", min_width=30)
    table.add_column("Company", style="bright_green", min_width=15)
    table.add_column("Location", style="bright_yellow", min_width=15)
    table.add_column("Type", style="bright_magenta", width=12)
    table.add_column("Source", style="dim", width=10)
    table.add_column("Apply URL", style="blue underline", min_width=25)

    for idx, row in enumerate(rows, 1):
        table.add_row(
            str(idx),
            row["title"][:60],
            row["company"][:25],
            (row["location"] or "Remote")[:25],
            (row["employment_type"] or "Unknown")[:12],
            row["source_platform"][:10],
            row["apply_url"][:50]
        )

    console.print(table)
    console.print(f"\n[dim]Tip: Open URLs directly or use `streamlit run interface/streamlit_app.py` for clickable links[/dim]")


def display_stats():
    """Show database statistics."""
    stats = get_stats()

    text = Text()
    text.append(f"Total Jobs: {stats['total']}\n", style="bold cyan")
    text.append(f"Active Jobs: {stats['active']}\n", style="bold green")
    text.append(f"New Jobs: {stats['new']}\n\n", style="bold yellow")
    text.append("By Platform:\n", style="bold white")

    for platform, count in sorted(stats["by_platform"].items(), key=lambda x: -x[1]):
        text.append(f"  {platform}: {count}\n", style="dim")

    console.print(Panel(text, title="[bold]Database Stats[/bold]", border_style="blue"))


def interactive_search():
    """Interactive CLI search."""
    console.print(Panel("[bold green]Job Hunter CLI[/bold green]", border_style="green"))
    display_stats()

    while True:
        console.print("\n[dim]Enter search query (or 'quit' to exit):[/dim]")
        query = input("> ").strip()
        if query.lower() in ("quit", "exit", "q"):
            break
        if not query:
            continue

        console.print("[dim]Location filter (optional, press Enter to skip):[/dim]")
        loc = input("Location: ").strip() or None

        console.print("[dim]Job type filter (Full-time/Internship/Contract, press Enter to skip):[/dim]")
        jt = input("Type: ").strip() or None

        display_jobs(query, loc, jt)


if __name__ == "__main__":
    interactive_search()
