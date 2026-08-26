# backend/worker.py
"""
Background worker process entry point for AI Code Understanding Engine.

Infrastructure scaffolding for asynchronous job execution (Phase 2+ repository indexing,
AST parsing, vector embedding generation, symbol graph building).

Listens for PostgreSQL job queue items when active.
"""

import asyncio
import logging
import signal
import sys
from contextlib import suppress

from sqlalchemy import text

from backend.db.config import db_settings
from backend.db.session import async_session_factory

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("codelens.worker")


class Worker:
    """Background worker scaffolding for PostgreSQL job polling."""

    def __init__(self) -> None:
        self.running: bool = True

    def stop(self, *args: object) -> None:
        """Handle shutdown signals gracefully."""
        logger.info("Shutdown signal received. Stopping worker process...")
        self.running = False

    async def check_db_connection(self) -> bool:
        """Verify database connection readiness."""
        db_url = db_settings.database_url
        if not db_url:
            logger.warning("DATABASE_URL is not configured.")
            return False

        try:
            async with async_session_factory() as session:
                await session.execute(text("SELECT 1"))
            logger.info("Database connection established successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            return False

    async def start(self) -> None:
        """Start worker process polling loop."""
        logger.info("Starting AI Code Understanding Engine Background Worker...")

        db_ok = await self.check_db_connection()
        if not db_ok:
            logger.warning("Worker starting in degraded mode (Database offline or unreachable).")

        logger.info("Worker polling loop initialised (waiting for job queue tasks)...")

        poll_interval = 5.0
        while self.running:
            try:
                # Scaffolding: Future job queue polling will query the `jobs` table here.
                await asyncio.sleep(poll_interval)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"Error in worker polling loop: {exc}")
                await asyncio.sleep(poll_interval)

        logger.info("Worker process stopped cleanly.")


def main() -> None:
    """Worker process entry point."""
    worker = Worker()

    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(ValueError, AttributeError):
            signal.signal(sig, worker.stop)

    try:
        asyncio.run(worker.start())
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()
