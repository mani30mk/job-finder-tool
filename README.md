# Job Hunter - Zero Budget Universal Job Search

> Personal job aggregator that scrapes every major platform for free.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt
playwright install chromium

# 2. Install Ollama (for LLM parsing)
# https://ollama.com - download for your OS
ollama pull mistral

# 3. Initialize database
python init_db.py

# 4. Run scrapers (no LinkedIn yet)
python run_scrapers.py

# 5. Search jobs in terminal
python -m interface.cli

# 6. Or launch web dashboard
streamlit run interface/streamlit_app.py
```

## LinkedIn Setup (Optional)

LinkedIn requires a logged-in session. Run once:

```bash
python login_linkedin.py
# Enter your email and password
# Complete 2FA if prompted
```

Then `run_scrapers.py` will automatically include LinkedIn.

## Automation

### Linux/Mac (Cron)
```bash
# Run every 6 hours
0 */6 * * * cd /path/to/job-hunter && /path/to/venv/bin/python run_scrapers.py >> logs/cron.log 2>&1
```

### Windows (Task Scheduler)
- Program: `python.exe`
- Arguments: `run_scrapers.py`
- Start in: `C:\path\to\job-hunter`

## Platforms Covered

| Platform | Method | Difficulty |
|----------|--------|------------|
| Greenhouse | JSON Feed | Easy |
| Lever | JSON Feed | Easy |
| Ashby | JSON Feed | Easy |
| Unstop | API | Medium |
| Internshala | HTML | Medium |
| Hacker News | HTML | Easy |
| LinkedIn | Browser | Hard |
| Workday | Browser | Hard |
| Custom Pages | Local LLM | Medium |

## Project Structure

```
job-hunter/
|-- config/           # Settings & company lists
|-- database/         # SQLite + FTS5 schema & queries
|-- scrapers/         # All platform scrapers
|   |-- feeds/        # JSON feed scrapers
|   |-- html/         # HTML scrapers
|   |-- browser/      # Playwright scrapers
|   |-- discovery/    # URL discovery tools
|-- parser/           # Normalizer, dedup, LLM parser
|-- interface/        # CLI (Rich) & Web UI (Streamlit)
|-- alerts/           # Discord notifications
|-- jobs.db           # SQLite database (auto-created)
|-- session_data/     # Playwright sessions
|-- logs/             # Scraping logs
```

## Cost

**0** - Everything runs locally. No APIs. No proxies. No subscriptions.

## Expected Results

- **Week 1:** 5,000-10,000 jobs in database
- **Daily new jobs:** 200-500
- **Platforms:** 10+

## Troubleshooting

**LinkedIn blocked?**
- Reduce `LINKEDIN_MAX_PAGES` in `config/settings.py`
- Increase `REQUEST_DELAY`
- Run during weekdays only

**Ollama not working?**
- Ensure Ollama is running: `ollama serve`
- Check `OLLAMA_HOST` in settings

**Database locked?**
- SQLite handles one writer at a time. Close other connections.

## License

Personal use only. Respect robots.txt and terms of service.
