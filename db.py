import json
import sqlite3
from pathlib import Path

from .config import APP_DIR, DB_PATH
from .models import Job, Preferences


class Database:
    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.init_db()

    def init_db(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_title TEXT NOT NULL,
                location TEXT NOT NULL,
                salary_min INTEGER,
                salary_max INTEGER,
                remote_only INTEGER DEFAULT 0,
                experience_level TEXT DEFAULT 'any',
                skills TEXT DEFAULT '[]',
                notify_email TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                external_id TEXT NOT NULL,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                location TEXT NOT NULL,
                url TEXT NOT NULL,
                salary_info TEXT,
                remote INTEGER DEFAULT 0,
                description_snippet TEXT DEFAULT '',
                tags TEXT DEFAULT '[]',
                found_at TEXT NOT NULL,
                preference_id INTEGER NOT NULL,
                notified INTEGER DEFAULT 0,
                UNIQUE(source, external_id),
                FOREIGN KEY (preference_id) REFERENCES preferences(id)
            );
        """)
        self.conn.commit()

    def save_preference(self, pref: Preferences) -> int:
        if pref.id:
            self.conn.execute(
                """UPDATE preferences SET job_title=?, location=?, salary_min=?,
                   salary_max=?, remote_only=?, experience_level=?, skills=?,
                   notify_email=?, created_at=? WHERE id=?""",
                (pref.job_title, pref.location, pref.salary_min, pref.salary_max,
                 int(pref.remote_only), pref.experience_level,
                 json.dumps(pref.skills), pref.notify_email, pref.created_at, pref.id),
            )
        else:
            cursor = self.conn.execute(
                """INSERT INTO preferences (job_title, location, salary_min, salary_max,
                   remote_only, experience_level, skills, notify_email, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (pref.job_title, pref.location, pref.salary_min, pref.salary_max,
                 int(pref.remote_only), pref.experience_level,
                 json.dumps(pref.skills), pref.notify_email, pref.created_at),
            )
            pref.id = cursor.lastrowid
        self.conn.commit()
        return pref.id

    def get_preferences(self) -> list[Preferences]:
        rows = self.conn.execute("SELECT * FROM preferences ORDER BY id").fetchall()
        return [self._row_to_pref(r) for r in rows]

    def get_preference(self, pref_id: int) -> Preferences | None:
        row = self.conn.execute(
            "SELECT * FROM preferences WHERE id=?", (pref_id,)
        ).fetchone()
        return self._row_to_pref(row) if row else None

    def delete_preference(self, pref_id: int):
        self.conn.execute("DELETE FROM jobs WHERE preference_id=?", (pref_id,))
        self.conn.execute("DELETE FROM preferences WHERE id=?", (pref_id,))
        self.conn.commit()

    def save_jobs(self, jobs: list[Job]) -> int:
        new_count = 0
        for job in jobs:
            try:
                self.conn.execute(
                    """INSERT INTO jobs (source, external_id, title, company, location,
                       url, salary_info, remote, description_snippet, tags, found_at,
                       preference_id, notified) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (job.source, job.external_id, job.title, job.company, job.location,
                     job.url, job.salary_info, int(job.remote), job.description_snippet,
                     json.dumps(job.tags), job.found_at, job.preference_id, int(job.notified)),
                )
                new_count += 1
            except sqlite3.IntegrityError:
                pass  # duplicate, skip
        self.conn.commit()
        return new_count

    def get_jobs(self, preference_id: int | None = None, limit: int = 50, offset: int = 0) -> list[Job]:
        if preference_id:
            rows = self.conn.execute(
                "SELECT * FROM jobs WHERE preference_id=? ORDER BY found_at DESC LIMIT ? OFFSET ?",
                (preference_id, limit, offset),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM jobs ORDER BY found_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return [self._row_to_job(r) for r in rows]

    def get_unnotified_jobs(self, preference_id: int) -> list[Job]:
        rows = self.conn.execute(
            "SELECT * FROM jobs WHERE preference_id=? AND notified=0 ORDER BY found_at DESC",
            (preference_id,),
        ).fetchall()
        return [self._row_to_job(r) for r in rows]

    def mark_notified(self, job_ids: list[int]):
        if not job_ids:
            return
        placeholders = ",".join("?" * len(job_ids))
        self.conn.execute(
            f"UPDATE jobs SET notified=1 WHERE id IN ({placeholders})", job_ids
        )
        self.conn.commit()

    def _row_to_pref(self, row: sqlite3.Row) -> Preferences:
        return Preferences(
            id=row["id"],
            job_title=row["job_title"],
            location=row["location"],
            salary_min=row["salary_min"],
            salary_max=row["salary_max"],
            remote_only=bool(row["remote_only"]),
            experience_level=row["experience_level"],
            skills=json.loads(row["skills"]),
            notify_email=row["notify_email"],
            created_at=row["created_at"],
        )

    def _row_to_job(self, row: sqlite3.Row) -> Job:
        return Job(
            id=row["id"],
            source=row["source"],
            external_id=row["external_id"],
            title=row["title"],
            company=row["company"],
            location=row["location"],
            url=row["url"],
            salary_info=row["salary_info"],
            remote=bool(row["remote"]),
            description_snippet=row["description_snippet"],
            tags=json.loads(row["tags"]),
            found_at=row["found_at"],
            preference_id=row["preference_id"],
            notified=bool(row["notified"]),
        )

    def close(self):
        self.conn.close()
