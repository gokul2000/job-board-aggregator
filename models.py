from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Preferences:
    job_title: str
    location: str
    salary_min: int | None = None
    salary_max: int | None = None
    remote_only: bool = False
    experience_level: str = "any"  # entry, mid, senior, any
    skills: list[str] = field(default_factory=list)
    notify_email: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    id: int | None = None


@dataclass
class Job:
    source: str
    external_id: str
    title: str
    company: str
    location: str
    url: str
    preference_id: int
    salary_info: str | None = None
    remote: bool = False
    description_snippet: str = ""
    tags: list[str] = field(default_factory=list)
    found_at: str = field(default_factory=lambda: datetime.now().isoformat())
    notified: bool = False
    id: int | None = None
