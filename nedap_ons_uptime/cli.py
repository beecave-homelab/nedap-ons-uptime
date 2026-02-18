import asyncio

import typer
from uvicorn import Config, Server

from nedap_ons_uptime.app import create_app
from nedap_ons_uptime.config import get_settings

app = typer.Typer(help="Nedap ONS Uptime Dashboard")


@app.command()
def serve() -> None:
    """Run migrations, start FastAPI server and background worker."""
    import os
    import subprocess
    import sys

    settings = get_settings()

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        env={**os.environ, "DATABASE_URL": settings.database_url},
    )
    if result.returncode != 0:
        typer.echo("Migration failed", err=True)
        raise typer.Exit(1)

    fastapi_app = create_app()
    config = Config(
        app=fastapi_app, host=settings.app_host, port=settings.app_port, log_level="info"
    )
    server = Server(config)

    asyncio.run(server.serve())


@app.command()
def migrate() -> None:
    """Run Alembic migrations."""
    import os
    import subprocess
    import sys

    settings = get_settings()

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        env={**os.environ, "DATABASE_URL": settings.database_url},
    )
    if result.returncode != 0:
        typer.echo("Migration failed", err=True)
        raise typer.Exit(1)

    typer.echo("Migrations completed successfully")


@app.command()
def check_once() -> None:
    """Run a single probe cycle."""
    import asyncio

    from .config import get_settings
    from .db.session import Database, set_database
    from .monitoring import run_checks

    settings = get_settings()
    db = Database(settings.database_url)
    set_database(db)

    async def run() -> None:
        await db.init()
        try:
            await run_checks(settings.concurrency)
        finally:
            await db.close()

    asyncio.run(run())
    typer.echo("Check cycle completed")


if __name__ == "__main__":
    app()
