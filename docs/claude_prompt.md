# BS-DIP MVP Claude Code Prompt

This document contains the original prompt used to generate this MVP.

## Overview

Build a local MVP in 3 days:
- Ingest NRHP points (ArcGIS REST) → store in Postgres/PostGIS
- Display on interactive Mapbox map
- Allow review + notes
- Compute NRHP proximity flags for targets
- Export CSV

## Primary Data Source

NRHP ArcGIS MapServer:
- Service root: https://mapservices.nps.gov/arcgis/rest/services/cultural_resources/nrhp_locations/MapServer?f=pjson
- Layer 0 points: https://mapservices.nps.gov/arcgis/rest/services/cultural_resources/nrhp_locations/MapServer/0
- Query endpoint: https://mapservices.nps.gov/arcgis/rest/services/cultural_resources/nrhp_locations/MapServer/0/query

## Tech Stack

- **Database**: Postgres + PostGIS via Docker
- **Backend**: FastAPI + SQLAlchemy + Alembic
- **Frontend**: Next.js + Mapbox GL JS

## Non-goals for MVP

- No auth
- No background orchestrators (no Dagster/Temporal)
- No OCR
- No S3/R2 (store raw docs in DB text)
- No PMTiles
- No polygons (NRHP points only)
