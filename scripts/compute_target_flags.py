#!/usr/bin/env python3
"""
Compute NRHP proximity flags for all targets.
For each target, calculates:
- Count of NRHP points within 1km
- Minimum distance to NRHP point (meters)
- Whether any nearby NHL exists
"""

import uuid
from datetime import datetime

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configuration
DATABASE_URL = "postgresql://bsdip:bsdip_dev_password@localhost:5432/bsdip"
PROXIMITY_RADIUS_M = 1000  # 1km radius

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def compute_flags_for_target(session, target_id: uuid.UUID) -> dict:
    """
    Compute NRHP proximity flags for a single target.
    Uses PostGIS geography for accurate meter-based distances.
    """
    result = session.execute(
        text("""
            SELECT
                COUNT(*) AS cnt,
                MIN(ST_Distance(t.geometry::geography, n.geometry::geography)) AS min_m,
                BOOL_OR(
                    COALESCE(n.is_nhl, '') <> ''
                    AND n.is_nhl <> '0'
                    AND LOWER(n.is_nhl) <> 'false'
                    AND LOWER(n.is_nhl) <> 'no'
                ) AS has_nhl
            FROM targets t
            LEFT JOIN nrhp_points n
                ON ST_DWithin(t.geometry::geography, n.geometry::geography, :radius)
            WHERE t.id = :target_id
            GROUP BY t.id
        """),
        {"target_id": target_id, "radius": PROXIMITY_RADIUS_M}
    ).fetchone()

    if result:
        return {
            "nrhp_near_count_1km": result.cnt or 0,
            "nrhp_min_distance_m": result.min_m,
            "nrhp_has_nhl_nearby_1km": result.has_nhl or False
        }
    return {
        "nrhp_near_count_1km": 0,
        "nrhp_min_distance_m": None,
        "nrhp_has_nhl_nearby_1km": False
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
        # Get all target IDs
        targets = session.execute(
            text("SELECT id, name FROM targets ORDER BY created_at")
        ).fetchall()

        if not targets:
            print("No targets found. Run seed_targets_demo.py first.")
            return

        print(f"Computing flags for {len(targets)} targets...")

        computed = 0
        with_nrhp = 0
        with_nhl = 0

        for target in targets:
            flags = compute_flags_for_target(session, target.id)
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
            print(f"  {row.name}: count={row.nrhp_near_count_1km}, "
                  f"min_dist={row.nrhp_min_distance_m:.0f}m, nhl={row.nrhp_has_nhl_nearby_1km}")

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
