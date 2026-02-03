#!/usr/bin/env python3
"""
Compute NRHP proximity flags for all targets.
For each target, calculates:
- Count of NRHP points within 1km
- Minimum distance to NRHP point (meters)
- Whether any nearby NHL exists

Uses Haversine formula for distance calculation (no PostGIS required).
"""

import math
import os
import uuid
from datetime import datetime

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://bsdip:bsdip_dev_password@localhost:5432/bsdip")
PROXIMITY_RADIUS_M = 1000  # 1km radius

# Approximate degree to km conversion (varies by latitude)
# At ~37 degrees latitude (California): 1 degree lat ≈ 111km, 1 degree lon ≈ 88km
# We use a generous buffer of 0.02 degrees (~2km) for the bbox filter
DEGREE_BUFFER = 0.015  # ~1.5km buffer in degrees

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points in meters.
    Uses the Haversine formula.
    """
    R = 6371000  # Earth's radius in meters

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def compute_flags_for_target(session, target_id: uuid.UUID, target_lat: float, target_lon: float) -> dict:
    """
    Compute NRHP proximity flags for a single target.
    Uses bounding box filter + Haversine for accurate distance.
    """
    # First, get candidate NRHP points within a bounding box
    result = session.execute(
        text("""
            SELECT id, lat, lon, is_nhl
            FROM nrhp_points
            WHERE lat >= :min_lat AND lat <= :max_lat
              AND lon >= :min_lon AND lon <= :max_lon
        """),
        {
            "min_lat": target_lat - DEGREE_BUFFER,
            "max_lat": target_lat + DEGREE_BUFFER,
            "min_lon": target_lon - DEGREE_BUFFER,
            "max_lon": target_lon + DEGREE_BUFFER
        }
    ).fetchall()

    # Calculate actual distances and filter by radius
    count = 0
    min_distance = None
    has_nhl = False

    for nrhp in result:
        distance = haversine_distance(target_lat, target_lon, nrhp.lat, nrhp.lon)

        if distance <= PROXIMITY_RADIUS_M:
            count += 1
            if min_distance is None or distance < min_distance:
                min_distance = distance

            # Check if this is an NHL
            is_nhl_val = nrhp.is_nhl or ""
            if is_nhl_val and is_nhl_val != "0" and is_nhl_val.lower() not in ("false", "no", ""):
                has_nhl = True

    return {
        "nrhp_near_count_1km": count,
        "nrhp_min_distance_m": min_distance,
        "nrhp_has_nhl_nearby_1km": has_nhl
    }


def upsert_target_flag(session, target_id: uuid.UUID, flags: dict):
    """Upsert target flags."""
    session.execute(
        text("""
            INSERT INTO target_flags (
                target_id, nrhp_near_count_1km, nrhp_min_distance_m,
                nrhp_has_nhl_nearby_1km, computed_at
            )
            VALUES (
                :target_id, :nrhp_near_count_1km, :nrhp_min_distance_m,
                :nrhp_has_nhl_nearby_1km, :computed_at
            )
            ON CONFLICT (target_id)
            DO UPDATE SET
                nrhp_near_count_1km = EXCLUDED.nrhp_near_count_1km,
                nrhp_min_distance_m = EXCLUDED.nrhp_min_distance_m,
                nrhp_has_nhl_nearby_1km = EXCLUDED.nrhp_has_nhl_nearby_1km,
                computed_at = EXCLUDED.computed_at
        """),
        {
            "target_id": target_id,
            "nrhp_near_count_1km": flags["nrhp_near_count_1km"],
            "nrhp_min_distance_m": flags["nrhp_min_distance_m"],
            "nrhp_has_nhl_nearby_1km": flags["nrhp_has_nhl_nearby_1km"],
            "computed_at": datetime.utcnow()
        }
    )


def compute_all_flags():
    """Compute flags for all targets."""
    session = SessionLocal()

    try:
        # Get all targets with coordinates
        targets = session.execute(
            text("SELECT id, name, lat, lon FROM targets ORDER BY created_at")
        ).fetchall()

        if not targets:
            print("No targets found. Run seed_targets_demo.py first.")
            return

        print(f"Computing flags for {len(targets)} targets...")

        computed = 0
        with_nrhp = 0
        with_nhl = 0

        for target in targets:
            flags = compute_flags_for_target(session, target.id, target.lat, target.lon)
            upsert_target_flag(session, target.id, flags)

            if flags["nrhp_near_count_1km"] > 0:
                with_nrhp += 1
            if flags["nrhp_has_nhl_nearby_1km"]:
                with_nhl += 1

            computed += 1
            if computed % 25 == 0:
                session.commit()
                print(f"  Computed {computed}/{len(targets)}...")

        session.commit()

        print(f"\nFlag computation complete!")
        print(f"  Total targets: {len(targets)}")
        print(f"  Targets near NRHP (1km): {with_nrhp}")
        print(f"  Targets near NHL: {with_nhl}")

        # Show sample results
        print("\nSample results:")
        sample = session.execute(
            text("""
                SELECT t.name, tf.nrhp_near_count_1km, tf.nrhp_min_distance_m,
                       tf.nrhp_has_nhl_nearby_1km
                FROM targets t
                JOIN target_flags tf ON t.id = tf.target_id
                WHERE tf.nrhp_near_count_1km > 0
                ORDER BY tf.nrhp_near_count_1km DESC
                LIMIT 5
            """)
        )
        for row in sample:
            dist_str = f"{row.nrhp_min_distance_m:.0f}m" if row.nrhp_min_distance_m else "N/A"
            print(f"  {row.name}: count={row.nrhp_near_count_1km}, "
                  f"min_dist={dist_str}, nhl={row.nrhp_has_nhl_nearby_1km}")

    except Exception as e:
        session.rollback()
        print(f"Error during flag computation: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    print("Computing target flags...")
    print(f"Database: {DATABASE_URL}")
    print(f"Proximity radius: {PROXIMITY_RADIUS_M}m")
    print()
    compute_all_flags()
