from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List
from uuid import UUID
import csv
import io

from database import get_db
from models import NRHPPoint, Target, TargetFlag
from schemas import ReviewUpdate, TargetSummary, TargetFlags, GeoJSONFeature, GeoJSONFeatureCollection

app = FastAPI(title="BS-DIP MVP API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:5000", "http://127.0.0.1:3000", "http://127.0.0.1:3001", "http://127.0.0.1:5000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def parse_bbox(bbox: str) -> tuple:
    """Parse bbox string 'minLon,minLat,maxLon,maxLat' into tuple."""
    parts = bbox.split(",")
    if len(parts) != 4:
        raise HTTPException(status_code=400, detail="bbox must be minLon,minLat,maxLon,maxLat")
    try:
        return tuple(float(p) for p in parts)
    except ValueError:
        raise HTTPException(status_code=400, detail="bbox values must be numeric")


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/nrhp")
def get_nrhp_points(
    bbox: str = Query(..., description="minLon,minLat,maxLon,maxLat"),
    limit: int = Query(5000, le=10000),
    db: Session = Depends(get_db)
):
    """Get NRHP points within bounding box as GeoJSON."""
    min_lon, min_lat, max_lon, max_lat = parse_bbox(bbox)

    query = text("""
        SELECT
            id,
            nris_refnum,
            resname,
            state,
            county,
            status,
            is_nhl,
            nara_url,
            lon,
            lat
        FROM nrhp_points
        WHERE lon >= :min_lon AND lon <= :max_lon
          AND lat >= :min_lat AND lat <= :max_lat
        LIMIT :limit
    """)

    result = db.execute(query, {
        "min_lon": min_lon,
        "min_lat": min_lat,
        "max_lon": max_lon,
        "max_lat": max_lat,
        "limit": limit
    })

    features = []
    for row in result:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [row.lon, row.lat]
            },
            "properties": {
                "id": str(row.id),
                "nris_refnum": row.nris_refnum,
                "resname": row.resname,
                "state": row.state,
                "county": row.county,
                "status": row.status,
                "is_nhl": row.is_nhl,
                "nara_url": row.nara_url
            }
        })

    return {"type": "FeatureCollection", "features": features}


@app.get("/targets")
def get_targets(
    bbox: str = Query(..., description="minLon,minLat,maxLon,maxLat"),
    review_status: Optional[str] = Query(None),
    min_score: Optional[int] = Query(None),
    limit: int = Query(5000, le=10000),
    db: Session = Depends(get_db)
):
    """Get targets within bounding box as GeoJSON."""
    min_lon, min_lat, max_lon, max_lat = parse_bbox(bbox)

    params = {
        "min_lon": min_lon,
        "min_lat": min_lat,
        "max_lon": max_lon,
        "max_lat": max_lat,
        "limit": limit
    }

    where_clauses = [
        "t.lon >= :min_lon AND t.lon <= :max_lon",
        "t.lat >= :min_lat AND t.lat <= :max_lat"
    ]

    if review_status:
        where_clauses.append("t.review_status = :review_status")
        params["review_status"] = review_status

    if min_score is not None:
        where_clauses.append("t.black_sky_score >= :min_score")
        params["min_score"] = min_score

    where_sql = " AND ".join(where_clauses)

    query = text(f"""
        SELECT
            t.id,
            t.name,
            t.target_type,
            t.black_sky_score,
            t.confidence,
            t.review_status,
            t.review_notes,
            t.lon,
            t.lat,
            tf.nrhp_near_count_1km,
            tf.nrhp_min_distance_m,
            tf.nrhp_has_nhl_nearby_1km
        FROM targets t
        LEFT JOIN target_flags tf ON t.id = tf.target_id
        WHERE {where_sql}
        LIMIT :limit
    """)

    result = db.execute(query, params)

    features = []
    for row in result:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [row.lon, row.lat]
            },
            "properties": {
                "id": str(row.id),
                "name": row.name,
                "target_type": row.target_type,
                "black_sky_score": row.black_sky_score,
                "confidence": row.confidence,
                "review_status": row.review_status,
                "review_notes": row.review_notes,
                "nrhp_near_count_1km": row.nrhp_near_count_1km,
                "nrhp_min_distance_m": row.nrhp_min_distance_m,
                "nrhp_has_nhl_nearby_1km": row.nrhp_has_nhl_nearby_1km
            }
        })

    return {"type": "FeatureCollection", "features": features}


@app.get("/targets/{target_id}")
def get_target(target_id: UUID, db: Session = Depends(get_db)):
    """Get single target summary."""
    query = text("""
        SELECT
            id,
            name,
            target_type,
            black_sky_score,
            confidence,
            review_status,
            review_notes,
            lon,
            lat,
            created_at,
            updated_at
        FROM targets
        WHERE id = :target_id
    """)

    result = db.execute(query, {"target_id": target_id}).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Target not found")

    return {
        "id": str(result.id),
        "name": result.name,
        "target_type": result.target_type,
        "lat": result.lat,
        "lon": result.lon,
        "black_sky_score": result.black_sky_score,
        "confidence": result.confidence,
        "review_status": result.review_status,
        "review_notes": result.review_notes,
        "created_at": result.created_at.isoformat() if result.created_at else None,
        "updated_at": result.updated_at.isoformat() if result.updated_at else None
    }


@app.get("/targets/{target_id}/flags")
def get_target_flags(target_id: UUID, db: Session = Depends(get_db)):
    """Get target flags."""
    flag = db.query(TargetFlag).filter(TargetFlag.target_id == target_id).first()

    if not flag:
        return {
            "target_id": str(target_id),
            "nrhp_near_count_1km": None,
            "nrhp_min_distance_m": None,
            "nrhp_has_nhl_nearby_1km": None,
            "computed_at": None
        }

    return {
        "target_id": str(flag.target_id),
        "nrhp_near_count_1km": flag.nrhp_near_count_1km,
        "nrhp_min_distance_m": flag.nrhp_min_distance_m,
        "nrhp_has_nhl_nearby_1km": flag.nrhp_has_nhl_nearby_1km,
        "computed_at": flag.computed_at.isoformat() if flag.computed_at else None
    }


@app.post("/targets/{target_id}/review")
def update_target_review(target_id: UUID, review: ReviewUpdate, db: Session = Depends(get_db)):
    """Update target review status and notes."""
    valid_statuses = ["unreviewed", "pursue", "monitor", "archive"]
    if review.review_status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"review_status must be one of: {valid_statuses}"
        )

    target = db.query(Target).filter(Target.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    target.review_status = review.review_status
    if review.review_notes is not None:
        target.review_notes = review.review_notes

    db.commit()
    db.refresh(target)

    return {"status": "updated", "target_id": str(target_id)}


@app.get("/export.csv")
def export_csv(
    bbox: str = Query(..., description="minLon,minLat,maxLon,maxLat"),
    review_status: Optional[str] = Query(None),
    min_score: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Export targets as CSV."""
    min_lon, min_lat, max_lon, max_lat = parse_bbox(bbox)

    params = {
        "min_lon": min_lon,
        "min_lat": min_lat,
        "max_lon": max_lon,
        "max_lat": max_lat
    }

    where_clauses = [
        "t.lon >= :min_lon AND t.lon <= :max_lon",
        "t.lat >= :min_lat AND t.lat <= :max_lat"
    ]

    if review_status:
        where_clauses.append("t.review_status = :review_status")
        params["review_status"] = review_status

    if min_score is not None:
        where_clauses.append("t.black_sky_score >= :min_score")
        params["min_score"] = min_score

    where_sql = " AND ".join(where_clauses)

    query = text(f"""
        SELECT
            t.id,
            t.name,
            t.target_type,
            t.lat,
            t.lon,
            t.review_status,
            t.black_sky_score,
            tf.nrhp_near_count_1km,
            tf.nrhp_min_distance_m
        FROM targets t
        LEFT JOIN target_flags tf ON t.id = tf.target_id
        WHERE {where_sql}
        ORDER BY t.black_sky_score DESC
    """)

    result = db.execute(query, params)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "name", "target_type", "lat", "lon",
        "review_status", "black_sky_score",
        "nrhp_near_count_1km", "nrhp_min_distance_m"
    ])

    for row in result:
        writer.writerow([
            str(row.id),
            row.name,
            row.target_type,
            row.lat,
            row.lon,
            row.review_status,
            row.black_sky_score,
            row.nrhp_near_count_1km,
            row.nrhp_min_distance_m
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=targets_export.csv"}
    )
