from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime
from uuid import UUID


class ReviewUpdate(BaseModel):
    review_status: str
    review_notes: Optional[str] = None


class TargetSummary(BaseModel):
    id: UUID
    name: Optional[str]
    target_type: Optional[str]
    lat: float
    lon: float
    black_sky_score: int
    confidence: float
    review_status: str
    review_notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TargetFlags(BaseModel):
    target_id: UUID
    nrhp_near_count_1km: Optional[int]
    nrhp_min_distance_m: Optional[float]
    nrhp_has_nhl_nearby_1km: Optional[bool]
    computed_at: Optional[datetime]

    class Config:
        from_attributes = True


class GeoJSONFeature(BaseModel):
    type: str = "Feature"
    geometry: dict
    properties: dict


class GeoJSONFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: List[GeoJSONFeature]
