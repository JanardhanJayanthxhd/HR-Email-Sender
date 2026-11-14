from datetime import datetime, timedelta
from pathlib import Path

import aiosqlite


async def init_db(db_path: Path) -> None:
    """Initialize database schema

    Args:
        db_path: Path to SQLite database file.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(db_path) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            role TEXT NOT NULL,
            hr_email TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            status TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON applications(timestamp)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_status ON applications(status)")
        await db.commit()


async def insert_application(
    db_path: Path, company: str, role: str, hr_email: str, subject: str, body: str, status: str
) -> None:
    """Insert application record.

    Args:
        db_path: Path to SQLite database file.
        company: Company name.
        role: Job role.
        hr_email: HR email address.
        subject: Email subject.
        body: Email body.
        status: Application status ('sent' or 'skipped').
    """
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT INTO applications (company, role, hr_email, subject, body, status) VALUES (?, ?, ?, ?, ?, ?)",
            (company, role, hr_email, subject, body, status),
        )
        await db.commit()


async def get_daily_send_count(db_path: Path) -> int:
    """Count emails sent in last 24 hours.

    Args:
        db_path: Path to SQLite database file.

    Returns:
        Number of emails with status='sent' in last 24 hours.
    """
    cutoff = (datetime.now() - timedelta(hours=24)).isoformat()

    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM applications WHERE status='sent' AND timestamp > ?", (cutoff,)
        )
        result = await cursor.fetchone()
        return result[0] if result else 0
