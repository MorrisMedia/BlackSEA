const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface Target {
  id: string;
  name: string;
  target_type: string;
  lat: number;
  lon: number;
  black_sky_score: number;
  confidence: number;
  review_status: string;
  review_notes: string | null;
  nrhp_near_count_1km: number | null;
  nrhp_min_distance_m: number | null;
  nrhp_has_nhl_nearby_1km: boolean | null;
}

export interface NRHPPoint {
  id: string;
  nris_refnum: string;
  resname: string;
  state: string;
  county: string;
  status: string;
  is_nhl: string;
  nara_url: string;
}

export interface TargetFlags {
  target_id: string;
  nrhp_near_count_1km: number | null;
  nrhp_min_distance_m: number | null;
  nrhp_has_nhl_nearby_1km: boolean | null;
  computed_at: string | null;
}

export interface GeoJSONFeatureCollection {
  type: 'FeatureCollection';
  features: GeoJSONFeature[];
}

export interface GeoJSONFeature {
  type: 'Feature';
  geometry: {
    type: 'Point';
    coordinates: [number, number];
  };
  properties: Record<string, unknown>;
}

export async function fetchNRHPPoints(bbox: string): Promise<GeoJSONFeatureCollection> {
  const response = await fetch(`${API_URL}/nrhp?bbox=${bbox}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch NRHP points: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchTargets(
  bbox: string,
  reviewStatus?: string,
  minScore?: number
): Promise<GeoJSONFeatureCollection> {
  const params = new URLSearchParams({ bbox });
  if (reviewStatus) params.append('review_status', reviewStatus);
  if (minScore !== undefined) params.append('min_score', minScore.toString());

  const response = await fetch(`${API_URL}/targets?${params}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch targets: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchTarget(targetId: string): Promise<Target> {
  const response = await fetch(`${API_URL}/targets/${targetId}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch target: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchTargetFlags(targetId: string): Promise<TargetFlags> {
  const response = await fetch(`${API_URL}/targets/${targetId}/flags`);
  if (!response.ok) {
    throw new Error(`Failed to fetch target flags: ${response.statusText}`);
  }
  return response.json();
}

export async function updateTargetReview(
  targetId: string,
  reviewStatus: string,
  reviewNotes?: string
): Promise<void> {
  const response = await fetch(`${API_URL}/targets/${targetId}/review`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      review_status: reviewStatus,
      review_notes: reviewNotes,
    }),
  });
  if (!response.ok) {
    throw new Error(`Failed to update review: ${response.statusText}`);
  }
}

export function getExportUrl(
  bbox: string,
  reviewStatus?: string,
  minScore?: number
): string {
  const params = new URLSearchParams({ bbox });
  if (reviewStatus) params.append('review_status', reviewStatus);
  if (minScore !== undefined) params.append('min_score', minScore.toString());
  return `${API_URL}/export.csv?${params}`;
}
