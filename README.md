# Nedap ONS Uptime

A minimal self-hosted uptime dashboard for monitoring HTTP/HTTPS endpoints.

## Features

- Monitor HTTP/HTTPS endpoints with configurable intervals and timeouts
- Real-time status dashboard with latency and error tracking
- 30+ days of historical data with automatic retention cleanup
- Simple web UI for managing targets
- RESTful API for integrations
- PostgreSQL for reliable data storage
- Docker Compose for easy deployment

## Quick Start

### Docker Compose (Recommended)

```bash
docker compose up -d --build
```

Access the dashboard at http://localhost:8000

### Local Development with PDM

Install PDM:
```bash
python3 -m pip install -U pdm
```

Install dependencies:
```bash
pdm install
```

Set up PostgreSQL and configure `DATABASE_URL` environment variable:
```bash
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/uptime"
```

Run migrations:
```bash
pdm run nedap-ons-uptime migrate
```

Start the server:
```bash
pdm run nedap-ons-uptime serve
```

## Configuration

Environment variables:

- `DATABASE_URL` - PostgreSQL connection URL (required)
- `APP_HOST` - Host to bind to (default: `0.0.0.0`)
- `APP_PORT` - Port to listen on (default: `8000`)
- `CONCURRENCY` - Max concurrent checks (default: `20`)
- `RETENTION_DAYS` - Days to keep historical data (default: `35`)
- `APP_TIMEZONE` - Timezone used for UI date/time display (default: `Europe/Amsterdam`)

## CLI Commands

```bash
pdm run nedap-ons-uptime serve      # Run server and worker
pdm run nedap-ons-uptime migrate    # Run database migrations
pdm run nedap-ons-uptime check-once # Run a single check cycle
```

## API Endpoints

### Targets
- `GET /api/targets` - List all targets
- `POST /api/targets` - Create a new target
- `GET /api/targets/{id}` - Get target details
- `PATCH /api/targets/{id}` - Update a target
- `DELETE /api/targets/{id}` - Delete a target

### Status
- `GET /api/status` - Get latest status for all targets
- `GET /api/targets/{id}/history?hours=24` - Get check history
- `GET /api/targets/{id}/uptime?days=30` - Get uptime percentage

### Config
- `GET /api/config` - Get application config (including configured timezone)

### Health
- `GET /healthz` - Health check endpoint

## License

MIT
