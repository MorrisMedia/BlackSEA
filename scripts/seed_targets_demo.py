#!/usr/bin/env python3
"""
Seed demo targets by sampling NRHP points in California and jittering coordinates.
Creates 50-200 demo targets for testing the flagging system.
"""

import random
import uuid
from datetime import datetime

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configuration
DATABASE_URL = "postgresql://bsdip:bsdip_dev_password@localhost:5432/bsdip"
TARGET_COUNT = 150  # Number of demo targets to create
JITTER_RANGE = 0.02  # ~2km jitter in degrees

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# Demo target names and types
TARGET_NAMES = [
    "Wreck Site Alpha", "Survey Point Beta", "Anomaly Gamma",
    "Debris Field Delta", "Contact Echo", "Object Foxtrot",
    "Target Golf", "Site Hotel", "Feature India", "Location Juliet",
    "Mark Kilo", "Point Lima", "Area Mike", "Zone November",
    "Spot Oscar", "Region Papa", "Sector Quebec", "Field Romeo",
    "Area Sierra", "Zone Tango", "Point Uniform", "Site Victor",
    "Location Whiskey", "Feature X-ray", "Target Yankee", "Zone Zulu"
]

TARGET_TYPES = ["wreck", "anomaly", "debris", "survey_point", "contact", "unknown"]


def get_ca_nrhp_points(session, limit: int = 500) -> list:
    """Get NRHP points from California."""
    result = session.execute(
        text("""
            SELECT
                ST_X(geometry) as lon,
                ST_Y(geometry) as lat,
                resname
            FROM nrhp_points
            WHERE state = 'CA'
            LIMIT :limit
        """),
        {"limit": limit}
    )
    return [dict(row._mapping) for row in result]


def jitter_coordinate(value: float, jitter: float) -> float:
    """Add random jitter to a coordinate."""
    return value + random.uniform(-jitter, jitter)


def create_demo_target(session, base_lon: float, base_lat: float, index: int) -> uuid.UUID:
    """Create a single demo target with jittered coordinates."""
    target_id = uuid.uuid4()

    # Jitter the coordinates
    lon = jitter_coordinate(base_lon, JITTER_RANGE)
    lat = jitter_coordinate(base_lat, JITTER_RANGE)

    # Generate name and type
    name_base = random.choice(TARGET_NAMES)
    name = f"{name_base} {index:03d}"
    target_type = random.choice(TARGET_TYPES)

    # Random score and confidence
    black_sky_score = random.randint(0, 100)
    confidence = round(random.uniform(0.3, 0.95), 2)

    session.execute(
        text("""
            INSERT INTO targets (
                id, name, target_type, geometry,
                black_sky_score, confidence, review_status,
                created_at, updated_at
            )
            VALUES (
                :id, :name, :target_type,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326),
                :black_sky_score, :confidence, 'unreviewed',
                :created_at, :updated_at
            )
        """),
        {
            "id": target_id,
            "name": name,
            "target_type": target_type,
            "lon": lon,
            "lat": lat,
            "black_sky_score": black_sky_score,
            "confidence": confidence,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    )

    return target_id


def seed_targets():
    """Main seeding function."""
    session = SessionLocal()

    try:
        # Check existing targets
        existing = session.execute(text("SELECT COUNT(*) FROM targets")).scalar()
        if existing > 0:
            print(f"Warning: {existing} targets already exist.")
            response = input("Delete existing and reseed? (y/N): ")
            if response.lower() == 'y':
                session.execute(text("DELETE FROM target_flags"))
                session.execute(text("DELETE FROM targets"))
                session.commit()
                print("Deleted existing targets.")
            else:
                print("Aborting.")
                return

        # Get CA NRHP points as base locations
        print("Fetching California NRHP points as base locations...")
        ca_points = get_ca_nrhp_points(session, limit=500)

        if not ca_points:
            print("No California NRHP points found. Run ingest_nrhp_points.py first.")
            return

        print(f"Found {len(ca_points)} CA points to use as bases.")

        # Create targets
        print(f"Creating {TARGET_COUNT} demo targets...")
        created = 0

        for i in range(TARGET_COUNT):
            # Pick a random base point
            base = random.choice(ca_points)
            create_demo_target(session, base["lon"], base["lat"], i + 1)
            created += 1

            if created % 25 == 0:
                print(f"  Created {created} targets...")

        session.commit()
        print(f"\nSuccessfully created {created} demo targets!")

        # Show sample
        sample = session.execute(
            text("""
                SELECT name, target_type, black_sky_score, review_status,
                       ST_X(geometry) as lon, ST_Y(geometry) as lat
                FROM targets
                LIMIT 5
            """)
        )
        print("\nSample targets:")
        for row in sample:
            print(f"  {row.name} ({row.target_type}) - score: {row.black_sky_score}, "
                  f"status: {row.review_status}, coords: ({row.lon:.4f}, {row.lat:.4f})")

    except Exception as e:
        session.rollback()
        print(f"Error during seeding: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    print("Seeding demo targets...")
    print(f"Database: {DATABASE_URL}")
    print(f"Target count: {TARGET_COUNT}")
    print()
    seed_targets()
