from contextlib import contextmanager
from pathlib import Path

from app.services.database import connection as database_connection, execute, run_migrations, uses_postgres


@contextmanager
def connection(database_path: Path):
    """Commit and close a short-lived delivery connection for the configured database."""
    with database_connection(database_path) as con:
        yield con


def initialize_delivery_table(database_path: Path) -> None:
    """Create persistent delivery state used to prevent duplicate digest sends."""
    run_migrations(database_path)


def claim_delivery(database_path: Path, day: str, channel: str, attempted_at: str) -> bool:
    """Claim a digest send unless another worker already sent or is sending it."""
    with connection(database_path) as con:
        if not uses_postgres(database_path):
            execute(con, "BEGIN IMMEDIATE")
        execute(con, "INSERT INTO digest_deliveries(day, channel, status, attempted_at) VALUES (?, ?, 'pending', ?) ON CONFLICT(day, channel) DO NOTHING", (day, channel, attempted_at))
        lock = " FOR UPDATE" if uses_postgres(database_path) else ""
        row = execute(con, f"SELECT status FROM digest_deliveries WHERE day=? AND channel=?{lock}", (day, channel)).fetchone()
        if row and row["status"] in {"sent", "sending"}:
            return False
        execute(con, "UPDATE digest_deliveries SET status='sending', attempted_at=?, provider_message_id=NULL, sent_at=NULL, error_message=NULL WHERE day=? AND channel=?", (attempted_at, day, channel))
        return True


def mark_sent(database_path: Path, day: str, channel: str, provider_message_id: str, sent_at: str) -> None:
    """Record a successfully accepted provider delivery."""
    with connection(database_path) as con:
        execute(con, "UPDATE digest_deliveries SET status='sent', provider_message_id=?, sent_at=?, error_message=NULL WHERE day=? AND channel=?", (provider_message_id, sent_at, day, channel))


def mark_failed(database_path: Path, day: str, channel: str, error_message: str) -> None:
    """Make a failed job eligible for a later scheduler retry."""
    with connection(database_path) as con:
        execute(con, "UPDATE digest_deliveries SET status='failed', error_message=? WHERE day=? AND channel=?", (error_message, day, channel))
