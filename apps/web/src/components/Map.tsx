'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import mapboxgl from 'mapbox-gl';
import { fetchNRHPPoints, fetchTargets, getExportUrl, GeoJSONFeatureCollection } from '@/lib/api';
import FilterPanel from './FilterPanel';
import LayerToggle from './LayerToggle';
import TargetDrawer from './TargetDrawer';

// Set Mapbox token
mapboxgl.accessToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN || '';

export default function Map() {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);

  // Layer visibility
  const [showNRHP, setShowNRHP] = useState(false);
  const [showTargets, setShowTargets] = useState(true);

  // Filters
  const [reviewStatus, setReviewStatus] = useState('');
  const [minScore, setMinScore] = useState(0);

  // Selected target
  const [selectedTargetId, setSelectedTargetId] = useState<string | null>(null);

  // Current bbox
  const [currentBbox, setCurrentBbox] = useState<string>('-125,32,-114,42'); // Default to California

  const getBbox = useCallback(() => {
    if (!map.current) return currentBbox;
    const bounds = map.current.getBounds();
    return `${bounds.getWest()},${bounds.getSouth()},${bounds.getEast()},${bounds.getNorth()}`;
  }, [currentBbox]);

  const loadData = useCallback(async () => {
    if (!map.current || !mapLoaded) return;

    const bbox = getBbox();
    setCurrentBbox(bbox);

    try {
      // Load targets if visible
      if (showTargets) {
        const targetsData = await fetchTargets(
          bbox,
          reviewStatus || undefined,
          minScore > 0 ? minScore : undefined
        );

        const source = map.current.getSource('targets') as mapboxgl.GeoJSONSource;
        if (source) {
          source.setData(targetsData as GeoJSONFeatureCollection);
        }
      }

      // Load NRHP points if visible
      if (showNRHP) {
        const nrhpData = await fetchNRHPPoints(bbox);

        const source = map.current.getSource('nrhp') as mapboxgl.GeoJSONSource;
        if (source) {
          source.setData(nrhpData as GeoJSONFeatureCollection);
        }
      }
    } catch (error) {
      console.error('Error loading data:', error);
    }
  }, [mapLoaded, showTargets, showNRHP, reviewStatus, minScore, getBbox]);

  // Initialize map
  useEffect(() => {
    if (map.current || !mapContainer.current) return;

    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/light-v11',
      center: [-119.5, 37], // Center on California
      zoom: 6,
    });

    map.current.addControl(new mapboxgl.NavigationControl(), 'bottom-right');

    map.current.on('load', () => {
      if (!map.current) return;

      // Add empty sources
      map.current.addSource('targets', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
      });

      map.current.addSource('nrhp', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
      });

      // Add NRHP layer (blue circles)
      map.current.addLayer({
        id: 'nrhp-points',
        type: 'circle',
        source: 'nrhp',
        paint: {
          'circle-radius': 6,
          'circle-color': '#3498db',
          'circle-opacity': 0.7,
          'circle-stroke-width': 1,
          'circle-stroke-color': '#2980b9',
        },
      });

      // Add targets layer (red circles)
      map.current.addLayer({
        id: 'target-points',
        type: 'circle',
        source: 'targets',
        paint: {
          'circle-radius': [
            'interpolate',
            ['linear'],
            ['get', 'black_sky_score'],
            0, 6,
            100, 12
          ],
          'circle-color': [
            'match',
            ['get', 'review_status'],
            'pursue', '#27ae60',
            'monitor', '#f39c12',
            'archive', '#95a5a6',
            '#e74c3c' // unreviewed (default)
          ],
          'circle-opacity': 0.8,
          'circle-stroke-width': 2,
          'circle-stroke-color': '#fff',
        },
      });

      // Click handler for targets
      map.current.on('click', 'target-points', (e) => {
        if (e.features && e.features.length > 0) {
          const feature = e.features[0];
          const targetId = feature.properties?.id;
          if (targetId) {
            setSelectedTargetId(targetId);
          }
        }
      });

      // Cursor change on hover
      map.current.on('mouseenter', 'target-points', () => {
        if (map.current) map.current.getCanvas().style.cursor = 'pointer';
      });

      map.current.on('mouseleave', 'target-points', () => {
        if (map.current) map.current.getCanvas().style.cursor = '';
      });

      // NRHP popup on click
      map.current.on('click', 'nrhp-points', (e) => {
        if (!map.current || !e.features || e.features.length === 0) return;

        const feature = e.features[0];
        const props = feature.properties;
        const coords = (feature.geometry as GeoJSON.Point).coordinates;

        new mapboxgl.Popup()
          .setLngLat(coords as [number, number])
          .setHTML(`
            <div style="max-width: 250px;">
              <h4 style="font-weight: bold; margin-bottom: 5px;">${props?.resname || 'Unknown'}</h4>
              <p style="margin: 2px 0; font-size: 12px;"><strong>State:</strong> ${props?.state || 'N/A'}</p>
              <p style="margin: 2px 0; font-size: 12px;"><strong>County:</strong> ${props?.county || 'N/A'}</p>
              <p style="margin: 2px 0; font-size: 12px;"><strong>NRIS#:</strong> ${props?.nris_refnum || 'N/A'}</p>
              <p style="margin: 2px 0; font-size: 12px;"><strong>NHL:</strong> ${props?.is_nhl || 'No'}</p>
              ${props?.nara_url ? `<a href="${props.nara_url}" target="_blank" style="font-size: 12px;">View NARA Record</a>` : ''}
            </div>
          `)
          .addTo(map.current);
      });

      map.current.on('mouseenter', 'nrhp-points', () => {
        if (map.current) map.current.getCanvas().style.cursor = 'pointer';
      });

      map.current.on('mouseleave', 'nrhp-points', () => {
        if (map.current) map.current.getCanvas().style.cursor = '';
      });

      setMapLoaded(true);
    });

    // Reload data on map move
    map.current.on('moveend', () => {
      loadData();
    });

    return () => {
      if (map.current) {
        map.current.remove();
        map.current = null;
      }
    };
  }, []);

  // Load data when map is ready or filters change
  useEffect(() => {
    loadData();
  }, [loadData]);

  // Update layer visibility
  useEffect(() => {
    if (!map.current || !mapLoaded) return;

    map.current.setLayoutProperty(
      'target-points',
      'visibility',
      showTargets ? 'visible' : 'none'
    );
  }, [showTargets, mapLoaded]);

  useEffect(() => {
    if (!map.current || !mapLoaded) return;

    map.current.setLayoutProperty(
      'nrhp-points',
      'visibility',
      showNRHP ? 'visible' : 'none'
    );

    // Load NRHP data when layer is turned on
    if (showNRHP) {
      loadData();
    }
  }, [showNRHP, mapLoaded, loadData]);

  const handleExport = () => {
    const bbox = getBbox();
    const url = getExportUrl(
      bbox,
      reviewStatus || undefined,
      minScore > 0 ? minScore : undefined
    );
    window.open(url, '_blank');
  };

  const handleDrawerClose = () => {
    setSelectedTargetId(null);
  };

  const handleTargetUpdate = () => {
    // Reload data to reflect changes
    loadData();
  };

  return (
    <div className="relative w-full h-screen">
      <div ref={mapContainer} className="map-container" />

      <FilterPanel
        reviewStatus={reviewStatus}
        minScore={minScore}
        onReviewStatusChange={setReviewStatus}
        onMinScoreChange={setMinScore}
        onExport={handleExport}
      />

      <LayerToggle
        showNRHP={showNRHP}
        showTargets={showTargets}
        onToggleNRHP={setShowNRHP}
        onToggleTargets={setShowTargets}
        drawerOpen={selectedTargetId !== null}
      />

      <TargetDrawer
        targetId={selectedTargetId}
        onClose={handleDrawerClose}
        onUpdate={handleTargetUpdate}
      />
    </div>
  );
}
