import json
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .config import EMAIL_CONFIG_PATH
from .db import Database
from .models import Job

logger = logging.getLogger(__name__)


def format_job(job: Job) -> str:
    lines = [
        f"  Title:    {job.title}",
        f"  Company:  {job.company}",
        f"  Location: {job.location}",
    ]
    if job.salary_info:
        lines.append(f"  Salary:   {job.salary_info}")
    if job.remote:
        lines.append(f"  Remote:   Yes")
    if job.tags:
        lines.append(f"  Tags:     {', '.join(job.tags)}")
    lines.append(f"  URL:      {job.url}")
    if job.description_snippet:
        lines.append(f"  Summary:  {job.description_snippet[:150]}...")
    lines.append(f"  Source:   {job.source}")
    return "\n".join(lines)


def format_job_html(job: Job) -> str:
    salary = f"<br><b>Salary:</b> {job.salary_info}" if job.salary_info else ""
    remote = "<br><b>Remote:</b> Yes" if job.remote else ""
    tags = f"<br><b>Tags:</b> {', '.join(job.tags)}" if job.tags else ""
    return f"""
    <div style="margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 5px;">
        <h3><a href="{job.url}">{job.title}</a></h3>
        <b>Company:</b> {job.company}<br>
        <b>Location:</b> {job.location}
        {salary}{remote}{tags}
        <br><b>Source:</b> {job.source}
        <p>{job.description_snippet[:200]}</p>
    </div>
    """


class ConsoleNotifier:
    def __init__(self, db: Database):
        self.db = db

    def notify(self, jobs: list[Job]):
        if not jobs:
            print("\nNo new jobs found.")
            return

        print(f"\n{'='*60}")
        print(f"  {len(jobs)} NEW JOB(S) FOUND")
        print(f"{'='*60}\n")

        for i, job in enumerate(jobs, 1):
            print(f"[{i}]")
            print(format_job(job))
            print()

        self.db.mark_notified([j.id for j in jobs if j.id])


class EmailNotifier:
    def __init__(self, db: Database):
        self.db = db
        self.config = self._load_config()

    def _load_config(self) -> dict | None:
        if not EMAIL_CONFIG_PATH.exists():
            return None
        try:
            return json.loads(EMAIL_CONFIG_PATH.read_text())
        except Exception:
            return None

    def is_configured(self) -> bool:
        return self.config is not None

    def notify(self, jobs: list[Job], to_email: str):
        if not jobs or not self.config:
            return

        subject = f"JobHunt: {len(jobs)} new job(s) found!"
        html_body = f"<h2>{len(jobs)} New Job Listings</h2>"
        for job in jobs:
            html_body += format_job_html(job)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.config["from_email"]
        msg["To"] = to_email

        text_body = "\n\n".join(format_job(j) for j in jobs)
        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        try:
            with smtplib.SMTP(self.config["smtp_host"], self.config["smtp_port"]) as server:
                server.starttls()
                server.login(self.config["smtp_user"], self.config["smtp_password"])
                server.send_message(msg)
            logger.info(f"Email sent to {to_email}")
        except Exception as e:
            logger.error(f"Failed to send email: {e}")

        self.db.mark_notified([j.id for j in jobs if j.id])


def save_email_config(smtp_host: str, smtp_port: int, smtp_user: str,
                       smtp_password: str, from_email: str):
    EMAIL_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    config = {
        "smtp_host": smtp_host,
        "smtp_port": smtp_port,
        "smtp_user": smtp_user,
        "smtp_password": smtp_password,
        "from_email": from_email,
    }
    EMAIL_CONFIG_PATH.write_text(json.dumps(config, indent=2))
    print(f"Email config saved to {EMAIL_CONFIG_PATH}")
