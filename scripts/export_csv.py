#!/usr/bin/env python3
"""
Export targets to CSV file.
Can be used standalone or via the API endpoint.
"""

import argparse
import csv
import sys
from datetime import datetime

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configuration
DATABASE_URL = "postgresql://bsdip:bsdip_dev_password@localhost:5432/bsdip"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def export_targets(
    output_file: str,
    bbox: tuple = None,
    review_status: str = None,
    min_score: int = None
):
    """Export targets to CSV."""
    session = SessionLocal()

    try:
        params = {}
        where_clauses = ["1=1"]

        if bbox:
            min_lon, min_lat, max_lon, max_lat = bbox
            where_clauses.append(
                "geometry && ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326)"
            )
            params.update({
                "min_lon": min_lon,
                "min_lat": min_lat,
                "max_lon": max_lon,
                "max_lat": max_lat
            })

        if review_status:
            where_clauses.append("review_status = :review_status")
            params["review_status"] = review_status

        if min_score is not None:
            where_clauses.append("black_sky_score >= :min_score")
            params["min_score"] = min_score

        where_sql = " AND ".join(where_clauses)

        query = text(f"""
            SELECT
                t.id,
                t.name,
                t.target_type,
                ST_Y(t.geometry) as lat,
                ST_X(t.geometry) as lon,
                t.review_status,
                t.black_sky_score,
                t.confidence,
                t.review_notes,
                tf.nrhp_near_count_1km,
                tf.nrhp_min_distance_m,
                tf.nrhp_has_nhl_nearby_1km
            FROM targets t
            LEFT JOIN target_flags tf ON t.id = tf.target_id
            WHERE {where_sql}
            ORDER BY t.black_sky_score DESC
        """)

        result = session.execute(query, params)

        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                "id", "name", "target_type", "lat", "lon",
                "review_status", "black_sky_score", "confidence",
                "review_notes", "nrhp_near_count_1km",
                "nrhp_min_distance_m", "nrhp_has_nhl_nearby_1km"
            ])

            count = 0
            for row in result:
                writer.writerow([
                    str(row.id),
                    row.name,
                    row.target_type,
                    row.lat,
                    row.lon,
                    row.review_status,
                    row.black_sky_score,
                    row.confidence,
                    row.review_notes,
                    row.nrhp_near_count_1km,
                    row.nrhp_min_distance_m,
                    row.nrhp_has_nhl_nearby_1km
                ])
                count += 1

        print(f"Exported {count} targets to {output_file}")
        return count

    except Exception as e:
        print(f"Error during export: {e}")
        raise
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description="Export targets to CSV")
    parser.add_argument("-o", "--output", default="targets_export.csv",
                        help="Output CSV file path")
    parser.add_argument("--bbox", help="Bounding box: minLon,minLat,maxLon,maxLat")
    parser.add_argument("--review-status",
                        choices=["unreviewed", "pursue", "monitor", "archive"],
                        help="Filter by review status")
    parser.add_argument("--min-score", type=int,
                        help="Minimum black_sky_score")

    args = parser.parse_args()

    bbox = None
    if args.bbox:
        parts = args.bbox.split(",")
        if len(parts) != 4:
            print("Error: bbox must be minLon,minLat,maxLon,maxLat")
            sys.exit(1)
        bbox = tuple(float(p) for p in parts)

    export_targets(
        output_file=args.output,
        bbox=bbox,
        review_status=args.review_status,
        min_score=args.min_score
    )


if __name__ == "__main__":
    main()
