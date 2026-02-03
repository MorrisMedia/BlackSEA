# BlackSEA - BS-DIP MVP

Black Sea Data Intelligence Platform - MVP for NRHP proximity analysis.

## Overview

This MVP provides:
- Ingestion of NRHP (National Register of Historic Places) points from ArcGIS REST API
- Interactive Mapbox map showing targets and NRHP points
- Review workflow for targets (pursue/monitor/archive)
- Proximity flags computed using PostGIS (count within 1km, min distance, NHL nearby)
- CSV export with filters

## Quick Start

### 1. Start Database

```bash
cd infra
docker compose up -d
```

### 2. Set Up API

```bash
cd apps/api
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start API server
uvicorn main:app --reload --port 8000
```

### 3. Ingest NRHP Data

```bash
cd scripts
python ingest_nrhp_points.py
```

This fetches all NRHP points from the NPS ArcGIS service (~100k points).

### 4. Seed Demo Targets

```bash
python seed_targets_demo.py
```

Creates 150 demo targets near California NRHP points.

### 5. Compute Flags

```bash
python compute_target_flags.py
```

Computes NRHP proximity flags for all targets.

### 6. Start Web App

```bash
cd apps/web
npm install

# Create .env.local with your Mapbox token
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
echo "NEXT_PUBLIC_MAPBOX_TOKEN=your_mapbox_token_here" >> .env.local

npm run dev
```

Open http://localhost:3000

## Project Structure

```
BlackSEA/
├── apps/
│   ├── api/           # FastAPI backend
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── database.py
│   │   └── alembic/
│   └── web/           # Next.js frontend
│       └── src/
│           ├── app/
│           ├── components/
│           └── lib/
├── scripts/
│   ├── ingest_nrhp_points.py
│   ├── seed_targets_demo.py
│   ├── compute_target_flags.py
│   └── export_csv.py
├── infra/
│   └── docker-compose.yml
└── docs/
    └── claude_prompt.md
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/nrhp?bbox=...` | GET | Get NRHP points in bounding box (GeoJSON) |
| `/targets?bbox=...` | GET | Get targets in bounding box (GeoJSON) |
| `/targets/{id}` | GET | Get single target details |
| `/targets/{id}/flags` | GET | Get target proximity flags |
| `/targets/{id}/review` | POST | Update review status/notes |
| `/export.csv?bbox=...` | GET | Export targets as CSV |

## Database Schema

### Tables

- **sources**: Data source metadata
- **raw_documents**: Raw JSON snapshots from API fetches
- **nrhp_points**: NRHP point locations with attributes
- **targets**: Target locations with review status
- **target_flags**: Computed NRHP proximity flags

## Features

### Map View
- Toggle layers: Targets (red) and NRHP points (blue)
- Target markers sized by score, colored by review status
- Click NRHP points for popup with details
- Click targets to open review drawer

### Target Drawer
- View target details and coordinates
- **AI Overview**: Rule-based sensitivity assessment
- NRHP proximity flags display
- Review status dropdown (unreviewed/pursue/monitor/archive)
- Notes text area
- Save button persists changes

### Filters
- Filter by review status
- Filter by minimum score
- Export visible targets to CSV

## Environment Variables

### API (.env)
```
DATABASE_URL=postgresql://bsdip:bsdip_dev_password@localhost:5432/bsdip
```

### Web (.env.local)
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_MAPBOX_TOKEN=your_mapbox_token
```

## Requirements

- Docker & Docker Compose
- Python 3.10+
- Node.js 18+
- Mapbox account (for map token)
