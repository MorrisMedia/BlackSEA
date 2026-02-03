'use client';

import React, { useState, useEffect } from 'react';
import { Target, TargetFlags, fetchTarget, fetchTargetFlags, updateTargetReview } from '@/lib/api';

interface TargetDrawerProps {
  targetId: string | null;
  onClose: () => void;
  onUpdate: () => void;
}

function generateAIOverview(flags: TargetFlags | null): string {
  if (!flags) {
    return 'Flag data not yet computed.';
  }

  const count = flags.nrhp_near_count_1km ?? 0;
  const hasNHL = flags.nrhp_has_nhl_nearby_1km ?? false;

  if (count === 0) {
    return 'No NRHP sensitivity flags within 1 km.';
  }

  if (hasNHL) {
    return 'National Historic Landmark nearby. Treat as high sensitivity; escalate to legal/heritage review.';
  }

  return `NRHP sites detected within 1 km (count=${count}). Treat as culturally sensitive; require counsel review before any field activity.`;
}

export default function TargetDrawer({ targetId, onClose, onUpdate }: TargetDrawerProps) {
  const [target, setTarget] = useState<Target | null>(null);
  const [flags, setFlags] = useState<TargetFlags | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [reviewStatus, setReviewStatus] = useState('');
  const [reviewNotes, setReviewNotes] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!targetId) {
      setTarget(null);
      setFlags(null);
      return;
    }

    setLoading(true);
    setError(null);

    Promise.all([fetchTarget(targetId), fetchTargetFlags(targetId)])
      .then(([targetData, flagsData]) => {
        setTarget(targetData);
        setFlags(flagsData);
        setReviewStatus(targetData.review_status);
        setReviewNotes(targetData.review_notes || '');
      })
      .catch((err) => {
        setError(err.message);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [targetId]);

  const handleSave = async () => {
    if (!targetId) return;

    setSaving(true);
    try {
      await updateTargetReview(targetId, reviewStatus, reviewNotes);
      onUpdate();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const isOpen = targetId !== null;

  return (
    <div className={`drawer ${isOpen ? 'open' : ''}`}>
      {isOpen && (
        <div className="p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold">Target Details</h2>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700 text-2xl"
            >
              &times;
            </button>
          </div>

          {loading && <p className="text-gray-500">Loading...</p>}
          {error && <p className="text-red-500">{error}</p>}

          {target && (
            <>
              <div className="mb-6">
                <h3 className="text-lg font-semibold">{target.name}</h3>
                <p className="text-sm text-gray-600">Type: {target.target_type}</p>
                <p className="text-sm text-gray-600">
                  Coordinates: {target.lat.toFixed(5)}, {target.lon.toFixed(5)}
                </p>
                <p className="text-sm text-gray-600">Score: {target.black_sky_score}</p>
                <p className="text-sm text-gray-600">
                  Confidence: {(target.confidence * 100).toFixed(0)}%
                </p>
              </div>

              {/* AI Overview */}
              <div className="mb-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
                <h4 className="text-sm font-semibold text-blue-800 mb-2">
                  AI Overview
                </h4>
                <p className="text-sm text-blue-900">{generateAIOverview(flags)}</p>
              </div>

              {/* NRHP Flags */}
              <div className="mb-6">
                <h4 className="text-sm font-semibold mb-2">NRHP Proximity Flags</h4>
                <div className="bg-gray-50 p-3 rounded-lg">
                  <div className="flex justify-between text-sm mb-1">
                    <span>Sites within 1km:</span>
                    <span className="font-medium">
                      {flags?.nrhp_near_count_1km ?? 'N/A'}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm mb-1">
                    <span>Min distance:</span>
                    <span className="font-medium">
                      {flags?.nrhp_min_distance_m
                        ? `${Math.round(flags.nrhp_min_distance_m)}m`
                        : 'N/A'}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>NHL nearby:</span>
                    <span
                      className={`font-medium ${
                        flags?.nrhp_has_nhl_nearby_1km
                          ? 'text-red-600'
                          : 'text-green-600'
                      }`}
                    >
                      {flags?.nrhp_has_nhl_nearby_1km ? 'Yes' : 'No'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Review Controls */}
              <div className="mb-4">
                <h4 className="text-sm font-semibold mb-2">Review</h4>

                <label className="block text-sm text-gray-700 mb-1">Status</label>
                <select
                  value={reviewStatus}
                  onChange={(e) => setReviewStatus(e.target.value)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 mb-3"
                >
                  <option value="unreviewed">Unreviewed</option>
                  <option value="pursue">Pursue</option>
                  <option value="monitor">Monitor</option>
                  <option value="archive">Archive</option>
                </select>

                <label className="block text-sm text-gray-700 mb-1">Notes</label>
                <textarea
                  value={reviewNotes}
                  onChange={(e) => setReviewNotes(e.target.value)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 h-24 resize-none"
                  placeholder="Add review notes..."
                />
              </div>

              <button
                onClick={handleSave}
                disabled={saving}
                className="w-full bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700 transition-colors disabled:bg-gray-400"
              >
                {saving ? 'Saving...' : 'Save Review'}
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
