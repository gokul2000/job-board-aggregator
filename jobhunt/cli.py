import argparse
import logging
import sys

from .config import APP_DIR, DEFAULT_SEARCH_INTERVAL, LOG_PATH
from .db import Database
from .models import Preferences
from .notifier import ConsoleNotifier, EmailNotifier, save_email_config
from .scrapers import ALL_SCRAPERS
from .search import SearchEngine
from .scheduler import run_periodic


def setup_logging(verbose: bool = False):
    APP_DIR.mkdir(parents=True, exist_ok=True)
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH),
            logging.StreamHandler() if verbose else logging.NullHandler(),
        ],
    )


def cmd_configure(args, db: Database):
    print("=== Configure Job Search Preferences ===\n")

    job_title = input("Job title (e.g. 'Python Developer'): ").strip()
    if not job_title:
        print("Job title is required.")
        return

    location = input("Location (or 'remote'): ").strip() or "remote"

    sal_min_str = input("Minimum salary (USD/year, or Enter to skip): ").strip()
    salary_min = int(sal_min_str) if sal_min_str.isdigit() else None

    sal_max_str = input("Maximum salary (USD/year, or Enter to skip): ").strip()
    salary_max = int(sal_max_str) if sal_max_str.isdigit() else None

    remote_input = input("Remote only? [y/N]: ").strip().lower()
    remote_only = remote_input in ("y", "yes")

    exp_level = input("Experience level (entry/mid/senior/any) [any]: ").strip().lower()
    if exp_level not in ("entry", "mid", "senior", "any"):
        exp_level = "any"

    skills_str = input("Skills (comma-separated, e.g. 'python, django, sql'): ").strip()
    skills = [s.strip() for s in skills_str.split(",") if s.strip()] if skills_str else []

    notify_email = input("Notification email (or Enter to skip): ").strip() or None

    pref = Preferences(
        job_title=job_title,
        location=location,
        salary_min=salary_min,
        salary_max=salary_max,
        remote_only=remote_only,
        experience_level=exp_level,
        skills=skills,
        notify_email=notify_email,
    )

    pref_id = db.save_preference(pref)
    print(f"\nPreference saved with ID: {pref_id}")
    _print_preference(pref)


def cmd_preferences(args, db: Database):
    if args.delete:
        db.delete_preference(args.delete)
        print(f"Deleted preference #{args.delete}")
        return

    prefs = db.get_preferences()
    if not prefs:
        print("No preferences configured. Run 'jobhunt configure' to set up.")
        return

    print(f"\n{'='*50}")
    print(f"  Saved Preferences ({len(prefs)})")
    print(f"{'='*50}\n")
    for pref in prefs:
        _print_preference(pref)
        print()


def cmd_search(args, db: Database):
    engine = SearchEngine(db, ALL_SCRAPERS)
    console = ConsoleNotifier(db)
    email = EmailNotifier(db)

    if args.pref:
        pref = db.get_preference(args.pref)
        if not pref:
            print(f"Preference #{args.pref} not found.")
            return
        print(f"Searching for: {pref.job_title} ({pref.location})...")
        new_jobs = engine.run_search(args.pref)
        console.notify(new_jobs)
        if pref.notify_email and email.is_configured():
            email.notify(new_jobs, pref.notify_email)
    else:
        prefs = db.get_preferences()
        if not prefs:
            print("No preferences configured. Run 'jobhunt configure' first.")
            return
        print(f"Searching across {len(prefs)} preference(s)...\n")
        results = engine.run_all()
        for pref_id, new_jobs in results.items():
            pref = db.get_preference(pref_id)
            print(f"\n--- {pref.job_title} ({pref.location}) ---")
            console.notify(new_jobs)
            if pref.notify_email and email.is_configured():
                email.notify(new_jobs, pref.notify_email)


def cmd_results(args, db: Database):
    if args.detail:
        jobs = db.get_jobs()
        job = next((j for j in jobs if j.id == args.detail), None)
        if job:
            from .notifier import format_job
            print(format_job(job))
        else:
            print(f"Job #{args.detail} not found.")
        return

    jobs = db.get_jobs(
        preference_id=args.pref,
        limit=args.limit,
    )

    if not jobs:
        print("No results found. Run 'jobhunt search' first.")
        return

    print(f"\n{'='*50}")
    print(f"  Job Results ({len(jobs)})")
    print(f"{'='*50}\n")

    for job in jobs:
        remote_tag = " [Remote]" if job.remote else ""
        salary_tag = f" | {job.salary_info}" if job.salary_info else ""
        print(f"  [{job.id}] {job.title}{remote_tag}")
        print(f"      {job.company} - {job.location}{salary_tag}")
        print(f"      {job.url}")
        print(f"      Source: {job.source} | Found: {job.found_at[:10]}")
        print()


def cmd_schedule(args, db: Database):
    prefs = db.get_preferences()
    if not prefs:
        print("No preferences configured. Run 'jobhunt configure' first.")
        return

    engine = SearchEngine(db, ALL_SCRAPERS)
    run_periodic(engine, db, interval_minutes=args.interval)


def cmd_email_config(args, db: Database):
    print("=== Configure Email Notifications ===\n")
    smtp_host = input("SMTP host (e.g. smtp.gmail.com): ").strip()
    smtp_port = int(input("SMTP port (e.g. 587): ").strip() or "587")
    smtp_user = input("SMTP username: ").strip()
    smtp_password = input("SMTP password: ").strip()
    from_email = input("From email address: ").strip()
    save_email_config(smtp_host, smtp_port, smtp_user, smtp_password, from_email)


def _print_preference(pref: Preferences):
    remote_str = "Yes" if pref.remote_only else "No"
    salary_str = ""
    if pref.salary_min or pref.salary_max:
        parts = []
        if pref.salary_min:
            parts.append(f"${pref.salary_min:,}")
        if pref.salary_max:
            parts.append(f"${pref.salary_max:,}")
        salary_str = " - ".join(parts)

    print(f"  [#{pref.id}] {pref.job_title}")
    print(f"      Location:    {pref.location}")
    if salary_str:
        print(f"      Salary:      {salary_str}")
    print(f"      Remote only: {remote_str}")
    print(f"      Experience:  {pref.experience_level}")
    if pref.skills:
        print(f"      Skills:      {', '.join(pref.skills)}")
    if pref.notify_email:
        print(f"      Email:       {pref.notify_email}")


def main():
    parser = argparse.ArgumentParser(
        prog="jobhunt",
        description="Job Board Aggregator - Search multiple job boards and get updates",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # configure
    subparsers.add_parser("configure", help="Set up job search preferences")

    # preferences
    pref_parser = subparsers.add_parser("preferences", help="List saved preferences")
    pref_parser.add_argument("--delete", type=int, metavar="ID", help="Delete a preference")

    # search
    search_parser = subparsers.add_parser("search", help="Search job boards now")
    search_parser.add_argument("--pref", type=int, metavar="ID", help="Search for a specific preference")

    # results
    results_parser = subparsers.add_parser("results", help="View saved job results")
    results_parser.add_argument("--pref", type=int, metavar="ID", help="Filter by preference ID")
    results_parser.add_argument("--limit", type=int, default=20, help="Max results to show")
    results_parser.add_argument("--detail", type=int, metavar="ID", help="Show full details of a job")

    # schedule
    schedule_parser = subparsers.add_parser("schedule", help="Run periodic searches")
    schedule_parser.add_argument(
        "--interval", type=int, default=DEFAULT_SEARCH_INTERVAL,
        help=f"Search interval in minutes (default: {DEFAULT_SEARCH_INTERVAL})",
    )

    # email-config
    subparsers.add_parser("email-config", help="Configure email notifications")

    args = parser.parse_args()
    setup_logging(args.verbose)

    if not args.command:
        parser.print_help()
        return

    db = Database()
    try:
        commands = {
            "configure": cmd_configure,
            "preferences": cmd_preferences,
            "search": cmd_search,
            "results": cmd_results,
            "schedule": cmd_schedule,
            "email-config": cmd_email_config,
        }
        commands[args.command](args, db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
