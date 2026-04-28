"use client";

import { useCallback, useEffect, useRef } from "react";
import Map, { Layer, NavigationControl, Source, type MapRef } from "react-map-gl/maplibre";
import { useQuery } from "@tanstack/react-query";
import { fetchProperties } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import type { Filters, PropertySummary, Tier } from "@/types";
import "maplibre-gl/dist/maplibre-gl.css";

// Free CARTO dark basemap — no account or API key required
const MAP_STYLE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";

// Montgomery County PA initial view
const INITIAL_VIEW = { longitude: -75.35, latitude: 40.18, zoom: 10 };

const TIER_COLORS: Record<Tier, string> = {
  hot: "#ef4444",
  warm: "#f97316",
  cold: "#6b7280",
};

export function PropertyMap() {
  const mapRef = useRef<MapRef>(null);
  const { filters, selectedPropertyId, setSelectedPropertyId } = useAppStore();

  const { data } = useQuery({
    queryKey: ["properties", filters],
    queryFn: () => fetchProperties(filters as Partial<Filters>),
  });

  const properties = data?.results ?? [];

  // Fly to selected property
  useEffect(() => {
    if (!selectedPropertyId || !mapRef.current) return;
    const prop = properties.find((p) => p.id === selectedPropertyId);
    if (prop?.latitude && prop?.longitude) {
      mapRef.current.flyTo({ center: [prop.longitude, prop.latitude], zoom: 15, duration: 800 });
    }
  }, [selectedPropertyId, properties]);

  const handleMapClick = useCallback(
    (e: { features?: Array<{ properties?: Record<string, unknown> }> }) => {
      const feature = e.features?.[0];
      if (!feature?.properties?.id) return;
      setSelectedPropertyId(feature.properties.id as string);
    },
    [setSelectedPropertyId]
  );

  const geojson: GeoJSON.FeatureCollection = {
    type: "FeatureCollection",
    features: properties
      .filter((p): p is PropertySummary & { latitude: number; longitude: number } => p.latitude != null && p.longitude != null)
      .map((p) => ({
        type: "Feature",
        geometry: { type: "Point", coordinates: [p.longitude, p.latitude] },
        properties: {
          id: p.id,
          score: p.score,
          tier: p.tier,
          color: TIER_COLORS[p.tier],
          selected: p.id === selectedPropertyId,
        },
      })),
  };

  return (
    <Map
      ref={mapRef}
      initialViewState={INITIAL_VIEW}
      mapStyle={MAP_STYLE}
      interactiveLayerIds={["property-points"]}
      onClick={handleMapClick}
      style={{ width: "100%", height: "100%" }}
    >
      <NavigationControl position="top-right" />

      <Source id="properties" type="geojson" data={geojson} cluster clusterMaxZoom={14} clusterRadius={50}>
        {/* Cluster circles */}
        <Layer
          id="clusters"
          type="circle"
          filter={["has", "point_count"]}
          paint={{
            "circle-color": ["step", ["get", "point_count"], "#f97316", 10, "#ef4444", 30, "#b91c1c"],
            "circle-radius": ["step", ["get", "point_count"], 20, 10, 30, 30, 40],
            "circle-opacity": 0.85,
          }}
        />
        <Layer
          id="cluster-count"
          type="symbol"
          filter={["has", "point_count"]}
          layout={{ "text-field": "{point_count_abbreviated}", "text-size": 13 }}
          paint={{ "text-color": "#fff" }}
        />
        {/* Individual points */}
        <Layer
          id="property-points"
          type="circle"
          filter={["!", ["has", "point_count"]]}
          paint={{
            "circle-color": ["get", "color"],
            "circle-radius": ["case", ["==", ["get", "selected"], true], 10, 7],
            "circle-stroke-width": ["case", ["==", ["get", "selected"], true], 2, 0],
            "circle-stroke-color": "#fff",
            "circle-opacity": 0.9,
          }}
        />
      </Source>
    </Map>
  );
}
