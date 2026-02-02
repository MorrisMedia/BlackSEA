'use client';

import React from 'react';

interface LayerToggleProps {
  showNRHP: boolean;
  showTargets: boolean;
  onToggleNRHP: (show: boolean) => void;
  onToggleTargets: (show: boolean) => void;
  drawerOpen: boolean;
}

export default function LayerToggle({
  showNRHP,
  showTargets,
  onToggleNRHP,
  onToggleTargets,
  drawerOpen,
}: LayerToggleProps) {
  return (
    <div
      className="layer-toggle"
      style={{ right: drawerOpen ? '420px' : '10px' }}
    >
      <h4 className="text-sm font-semibold mb-2">Layers</h4>

      <label className="flex items-center mb-2 cursor-pointer">
        <input
          type="checkbox"
          checked={showTargets}
          onChange={(e) => onToggleTargets(e.target.checked)}
          className="mr-2"
        />
        <span className="text-sm flex items-center">
          <span
            className="inline-block w-3 h-3 rounded-full mr-2"
            style={{ backgroundColor: '#e74c3c' }}
          />
          Targets
        </span>
      </label>

      <label className="flex items-center cursor-pointer">
        <input
          type="checkbox"
          checked={showNRHP}
          onChange={(e) => onToggleNRHP(e.target.checked)}
          className="mr-2"
        />
        <span className="text-sm flex items-center">
          <span
            className="inline-block w-3 h-3 rounded-full mr-2"
            style={{ backgroundColor: '#3498db' }}
          />
          NRHP Points
        </span>
      </label>
    </div>
  );
}
