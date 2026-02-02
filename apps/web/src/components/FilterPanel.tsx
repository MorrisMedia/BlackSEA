'use client';

import React from 'react';

interface FilterPanelProps {
  reviewStatus: string;
  minScore: number;
  onReviewStatusChange: (status: string) => void;
  onMinScoreChange: (score: number) => void;
  onExport: () => void;
}

export default function FilterPanel({
  reviewStatus,
  minScore,
  onReviewStatusChange,
  onMinScoreChange,
  onExport,
}: FilterPanelProps) {
  return (
    <div className="filter-panel">
      <h3 className="text-lg font-semibold mb-3">Filters</h3>

      <div className="mb-3">
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Review Status
        </label>
        <select
          value={reviewStatus}
          onChange={(e) => onReviewStatusChange(e.target.value)}
          className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
        >
          <option value="">All</option>
          <option value="unreviewed">Unreviewed</option>
          <option value="pursue">Pursue</option>
          <option value="monitor">Monitor</option>
          <option value="archive">Archive</option>
        </select>
      </div>

      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Min Score: {minScore}
        </label>
        <input
          type="range"
          min="0"
          max="100"
          value={minScore}
          onChange={(e) => onMinScoreChange(parseInt(e.target.value))}
          className="w-full"
        />
      </div>

      <button
        onClick={onExport}
        className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 transition-colors text-sm"
      >
        Export CSV
      </button>
    </div>
  );
}
