#!/usr/bin/env python3
"""
Ingest NRHP points from ArcGIS REST API into database.
Handles pagination and upserts using NRIS_Refnum as natural key.
"""

import hashlib
import json
import sys
import time
import uuid
from datetime import datetime
from typing import Optional

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configuration
DATABASE_URL = "postgresql://bsdip:bsdip_dev_password@localhost:5432/bsdip"
NRHP_QUERY_URL = "https://mapservices.nps.gov/arcgis/rest/services/cultural_resources/nrhp_locations/MapServer/0/query"
PAGE_SIZE = 2000
OUT_FIELDS = "RESNAME,NRIS_Refnum,State,County,STATUS,Is_NHL,NARA_URL,PROPERTY_ID,CR_ID,GEOM_ID,EDIT_DATE,SOURCE"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def get_or_create_source(session) -> uuid.UUID:
    """Get or create the NRHP source record."""
    result = session.execute(
        text("SELECT id FROM sources WHERE name = 'NRHP ArcGIS MapServer'")
    ).fetchone()

    if result:
        return result[0]

    source_id = uuid.uuid4()
    session.execute(
        text("""
            INSERT INTO sources (id, name, category, url, api_type, created_at)
            VALUES (:id, :name, :category, :url, :api_type, :created_at)
        """),
        {
            "id": source_id,
            "name": "NRHP ArcGIS MapServer",
            "category": "cultural_resources",
            "url": "https://mapservices.nps.gov/arcgis/rest/services/cultural_resources/nrhp_locations/MapServer",
            "api_type": "arcgis_rest",
            "created_at": datetime.utcnow()
        }
    )
    session.commit()
    print(f"Created source: NRHP ArcGIS MapServer (id={source_id})")
    return source_id


def save_raw_document(session, source_id: uuid.UUID, content: str) -> uuid.UUID:
    """Save raw JSON response as a document."""
    doc_id = uuid.uuid4()
    content_hash = hashlib.sha256(content.encode()).hexdigest()

    session.execute(
        text("""
            INSERT INTO raw_documents (id, source_id, fetched_at, content_type, content, hash)
            VALUES (:id, :source_id, :fetched_at, :content_type, :content, :hash)
        """),
        {
            "id": doc_id,
            "source_id": source_id,
            "fetched_at": datetime.utcnow(),
            "content_type": "geojson",
            "content": content,
            "hash": content_hash
        }
    )
    return doc_id


def generate_fallback_key(feature: dict) -> Optional[str]:
    """Generate fallback key when NRIS_Refnum is missing."""
    props = feature.get("properties", {})
    geom = feature.get("geometry", {})
    coords = geom.get("coordinates", [])

    if len(coords) < 2:
        return None

    lon, lat = coords[0], coords[1]
    resname = props.get("RESNAME", "") or ""
    state = props.get("State", "") or ""
    county = props.get("County", "") or ""

    # Round coordinates to 5 decimal places
    key_parts = [
        resname.strip().lower(),
        state.strip().lower(),
        county.strip().lower(),
        f"{round(lat, 5)}",
        f"{round(lon, 5)}"
    ]
    return "|".join(key_parts)


def upsert_nrhp_point(session, feature: dict) -> bool:
    """Upsert a single NRHP point. Returns True if successful."""
    props = feature.get("properties", {})
    geom = feature.get("geometry", {})
    coords = geom.get("coordinates", [])

    if len(coords) < 2:
        return False

    lon, lat = coords[0], coords[1]
    nris_refnum = props.get("NRIS_Refnum")

    # Skip if no valid identifier
    if not nris_refnum:
        fallback_key = generate_fallback_key(feature)
        if not fallback_key:
            return False
        # Use fallback key as nris_refnum for uniqueness
        nris_refnum = f"FALLBACK:{fallback_key}"

    point_data = {
        "nris_refnum": nris_refnum,
        "resname": props.get("RESNAME"),
        "state": props.get("State"),
        "county": props.get("County"),
        "status": props.get("STATUS"),
        "is_nhl": str(props.get("Is_NHL", "")) if props.get("Is_NHL") is not None else None,
        "nara_url": props.get("NARA_URL"),
        "edit_date": props.get("EDIT_DATE"),
        "source": props.get("SOURCE"),
        "lon": lon,
        "lat": lat,
        "updated_at": datetime.utcnow()
    }

    # Upsert using ON CONFLICT (non-PostGIS version)
    session.execute(
        text("""
            INSERT INTO nrhp_points (
                id, nris_refnum, resname, state, county, status,
                is_nhl, nara_url, edit_date, source, lon, lat,
                created_at, updated_at
            )
            VALUES (
                :id, :nris_refnum, :resname, :state, :county, :status,
                :is_nhl, :nara_url, :edit_date, :source, :lon, :lat,
                :created_at, :updated_at
            )
            ON CONFLICT (nris_refnum)
            DO UPDATE SET
                resname = EXCLUDED.resname,
                state = EXCLUDED.state,
                county = EXCLUDED.county,
                status = EXCLUDED.status,
                is_nhl = EXCLUDED.is_nhl,
                nara_url = EXCLUDED.nara_url,
                edit_date = EXCLUDED.edit_date,
                source = EXCLUDED.source,
                lon = EXCLUDED.lon,
                lat = EXCLUDED.lat,
                updated_at = EXCLUDED.updated_at
        """),
        {
            **point_data,
            "id": uuid.uuid4(),
            "created_at": datetime.utcnow()
        }
    )
    return True


def fetch_page(client: httpx.Client, offset: int) -> dict:
    """Fetch a single page of NRHP points."""
    params = {
        "where": "1=1",
        "outFields": OUT_FIELDS,
        "returnGeometry": "true",
        "f": "geojson",
        "resultOffset": offset,
        "resultRecordCount": PAGE_SIZE
    }

    response = client.get(NRHP_QUERY_URL, params=params, timeout=60.0)
    response.raise_for_status()
    return response.json()


def ingest_all():
    """Main ingestion function."""
    session = SessionLocal()

    try:
        source_id = get_or_create_source(session)
        total_ingested = 0
        offset = 0

        with httpx.Client() as client:
            while True:
                print(f"Fetching page at offset {offset}...")

                try:
                    data = fetch_page(client, offset)
                except httpx.HTTPError as e:
                    print(f"HTTP error at offset {offset}: {e}")
                    time.sleep(5)
                    continue

                # Save raw document
                raw_json = json.dumps(data)
                save_raw_document(session, source_id, raw_json)

                features = data.get("features", [])
                if not features:
                    print("No more features to fetch.")
                    break

                # Process features
                page_count = 0
                for feature in features:
                    if upsert_nrhp_point(session, feature):
                        page_count += 1

                session.commit()
                total_ingested += page_count
                print(f"  Ingested {page_count} points (total: {total_ingested})")

                # Check if we got fewer than PAGE_SIZE records (last page)
                if len(features) < PAGE_SIZE:
                    print("Reached last page.")
                    break

                offset += PAGE_SIZE
                time.sleep(0.5)  # Be nice to the server

        print(f"\nIngestion complete! Total points: {total_ingested}")

    except Exception as e:
        session.rollback()
        print(f"Error during ingestion: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    print("Starting NRHP points ingestion...")
    print(f"Source: {NRHP_QUERY_URL}")
    print(f"Database: {DATABASE_URL}")
    print()
    ingest_all()
