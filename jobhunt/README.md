# JobHunt - Job Board Aggregator CLI

A Python CLI tool that aggregates job listings from multiple job boards, filters them by your preferences (title, salary, location, skills), and notifies you when new matches are found.

## Job Sources

| Source | Type | Auth Required |
|---|---|---|
| [RemoteOK](https://remoteok.com) | JSON API | None |
| [LinkedIn](https://linkedin.com/jobs) | HTML Scraping | None |
| [The Muse](https://www.themuse.com) | JSON API | None |
| [Adzuna](https://www.adzuna.com) | JSON API | Free API key |
| [Arbeitnow](https://www.arbeitnow.com) | JSON API | None |

## Prerequisites

- Python 3.10 or higher

## Installation

```bash
# Clone the repository
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install the package
pip install -e .
```

## Quick Start

```bash
# 1. Set up your job search preferences
jobhunt configure

# 2. Search all job boards
jobhunt search

# 3. View saved results
jobhunt results
```

## Usage

### Configure Preferences

Set up what kind of jobs you're looking for. You can create multiple preference profiles.

```bash
jobhunt configure
```

You'll be prompted for:
- **Job title** — e.g. "Python Developer", "Data Engineer"
- **Location** — e.g. "San Francisco, CA", "Remote"
- **Salary range** — minimum and/or maximum (USD/year)
- **Remote only** — filter for remote positions only
- **Experience level** — entry, mid, senior, or any
- **Skills** — comma-separated list, e.g. "python, django, sql"
- **Notification email** — optional, for email alerts

### Search Jobs

```bash
# Search all job boards for all saved preferences
jobhunt search

# Search for a specific preference only
jobhunt search --pref 1
```

### View Results

```bash
# List all saved job results
jobhunt results

# Filter by preference
jobhunt results --pref 1

# Limit number of results
jobhunt results --limit 10

# View full details of a specific job
jobhunt results --detail 42
```

### Manage Preferences

```bash
# List all saved preferences
jobhunt preferences

# Delete a preference
jobhunt preferences --delete 1
```

### Schedule Periodic Searches

```bash
# Search every 60 minutes (default)
jobhunt schedule

# Search every 30 minutes
jobhunt schedule --interval 30
```

Alternatively, use system cron for background scheduling:

```bash
crontab -e
```

Add this line to search every hour:

```
0 * * * * /path/to/venv/bin/jobhunt search
```

### Email Notifications

```bash
# Configure SMTP settings for email alerts
jobhunt email-config
```

You'll need your SMTP server details (e.g. for Gmail: `smtp.gmail.com`, port `587`).

### Verbose Logging

```bash
# Enable debug output
jobhunt -v search
```

Logs are saved to `~/.jobhunt/jobhunt.log`.

## Adzuna API Setup (Optional)

Adzuna provides excellent salary data and multi-country support. To enable it:

1. Sign up at [developer.adzuna.com](https://developer.adzuna.com/)
2. Copy your **Application ID** and **Application Key** from the dashboard
3. Configure using either method:

**Environment variables:**

```bash
export ADZUNA_APP_ID=your_app_id
export ADZUNA_APP_KEY=your_app_key
```

**Config file:**

```bash
echo '{"app_id": "your_app_id", "app_key": "your_app_key"}' > ~/.jobhunt/adzuna.conf
```

Without credentials, Adzuna is skipped and the other 4 sources still work.

## Project Structure

```
jobhunt/
├── __init__.py          # Package version
├── cli.py               # CLI entry point (argparse)
├── config.py            # Paths and constants
├── db.py                # SQLite database layer
├── models.py            # Job & Preferences dataclasses
├── notifier.py          # Console + email notifications
├── scheduler.py         # Periodic search loop
├── search.py            # Search orchestrator
└── scrapers/
    ├── __init__.py      # Scraper registry
    ├── base.py          # Abstract base scraper
    ├── remoteok.py      # RemoteOK scraper
    ├── linkedin.py      # LinkedIn scraper
    ├── themuse.py       # The Muse scraper
    ├── adzuna.py        # Adzuna scraper
    └── arbeitnow.py     # Arbeitnow scraper
```

## Data Storage

All data is stored locally at `~/.jobhunt/`:

| File | Purpose |
|---|---|
| `jobhunt.db` | SQLite database (preferences + job results) |
| `jobhunt.log` | Application logs |
| `email.conf` | SMTP configuration (if set up) |
| `adzuna.conf` | Adzuna API credentials (if set up) |

## Adding a New Job Board

1. Create a new file in `jobhunt/scrapers/` (e.g. `myjobboard.py`)
2. Implement a class extending `BaseScraper` with a `search()` method
3. Add it to `ALL_SCRAPERS` in `jobhunt/scrapers/__init__.py`

```python
from jobhunt.scrapers.base import BaseScraper
from jobhunt.models import Job, Preferences

class MyJobBoardScraper(BaseScraper):
    name = "myjobboard"

    def search(self, preferences: Preferences) -> list[Job]:
        # Fetch and parse jobs, return list of Job objects
        ...
```

## License

MIT
