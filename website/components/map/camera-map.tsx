"use client";

import React, { useEffect, useRef, useCallback } from "react";
import L from "leaflet";
import { Camera } from "@/lib/types";
import { isSignalized, getCameraCoordinatesWithFallback } from "@/lib/utils";

interface CameraMapProps {
  cameras: Camera[];
  selectedCameraId: string | null;
  onSelectCamera: (camera: Camera) => void;
  focusTarget?: { cameraId: string; timestamp: number } | null;
  isPaneOpen?: boolean;
}

export default function CameraMap({
  cameras,
  selectedCameraId,
  onSelectCamera,
  focusTarget,
  isPaneOpen = false,
}: CameraMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const markersRef = useRef<Map<string, L.Marker>>(new Map());
  const hasFittedBoundsRef = useRef(false);
  const lastFocusTimestampRef = useRef<number | null>(null);
  const lastSelectedCameraIdRef = useRef<string | null>(null);

  // Initialize Map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    // Default center to Turin, Italy (Piazza Castello)
    const initialLat = 45.0703;
    const initialLon = 7.6869;

    const map = L.map(mapContainerRef.current, {
      center: [initialLat, initialLon],
      zoom: 14,
      zoomControl: false,
    });

    // Official OpenStreetMap tiles - 100% free, no API key required
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(map);

    // Zoom control at bottom right
    L.control.zoom({ position: "bottomright" }).addTo(map);

    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Dedicated camera transport function
  const flyToCamera = useCallback(
    (targetCameraId: string, duration = 1.0) => {
      const map = mapInstanceRef.current;
      if (!map) return;

      const camera = cameras.find((c) => c.id === targetCameraId);
      if (!camera) return;

      const [lat, lon] = getCameraCoordinatesWithFallback(camera);

      // Invalidate layout size in case drawer was just toggled
      map.invalidateSize();

      const zoom = Math.max(map.getZoom(), 16);
      let targetLatLng: L.LatLngExpression = [lat, lon];

      // If bottom pane is open (~300px height), offset map center downwards
      // so the marker rests comfortably in the visible upper half of the viewport
      if (isPaneOpen) {
        const point = map.project([lat, lon], zoom);
        const offsetPoint = L.point(point.x, point.y + 110);
        targetLatLng = map.unproject(offsetPoint, zoom);
      }

      map.flyTo(targetLatLng, zoom, {
        duration,
      });

      // Open marker tooltip after transport starts
      setTimeout(() => {
        const marker = markersRef.current.get(targetCameraId);
        if (marker) {
          marker.openTooltip();
        }
      }, Math.max(300, Math.round(duration * 600)));
    },
    [cameras, isPaneOpen]
  );

  // Update Markers when cameras list or selection changes
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    // Clear old markers
    markersRef.current.forEach((marker) => marker.remove());
    markersRef.current.clear();

    const bounds: [number, number][] = [];

    cameras.forEach((camera) => {
      const [lat, lon] = getCameraCoordinatesWithFallback(camera);
      bounds.push([lat, lon]);

      const isSelected = selectedCameraId === camera.id;

      // Traffic-light color only applies to operating (online) cameras.
      const currentLight = camera.current_light;
      const isOperating = camera.state === "online";
      const signalized = isSignalized(camera);

      const lightColor = !signalized
        ? "#8a857c"
        : !isOperating
        ? "#8a857c"
        : currentLight === "green"
        ? "#4f9d69"
        : currentLight === "amber"
        ? "#d99a2b"
        : currentLight === "red"
        ? "#d1584f"
        : "#20808d";

      // Subtle pulse ring for operating cameras
      const pulseHtml = isOperating
        ? `<span class="pulse-ring" style="background-color: ${lightColor}26; width: 46px; height: 46px;"></span>`
        : "";

      // 3-lamp signal widget lights up for operating signalized cameras
      const isRedActive = signalized && isOperating && currentLight === "red";
      const isAmberActive = signalized && isOperating && currentLight === "amber";
      const isGreenActive = signalized && isOperating && currentLight === "green";

      const innerGlyph = signalized
        ? `
              <div style="display: flex; flex-direction: column; align-items: center; gap: 2.5px;">
                <span style="
                  width: 6px;
                  height: 6px;
                  border-radius: 50%;
                  background: ${isRedActive ? "#d1584f" : "#d1584f33"};
                  box-shadow: ${isRedActive ? "0 0 3px #d1584f99" : "none"};
                "></span>
                <span style="
                  width: 6px;
                  height: 6px;
                  border-radius: 50%;
                  background: ${isAmberActive ? "#d99a2b" : "#d99a2b33"};
                  box-shadow: ${isAmberActive ? "0 0 3px #d99a2b99" : "none"};
                "></span>
                <span style="
                  width: 6px;
                  height: 6px;
                  border-radius: 50%;
                  background: ${isGreenActive ? "#4f9d69" : "#4f9d6933"};
                  box-shadow: ${isGreenActive ? "0 0 3px #4f9d6999" : "none"};
                "></span>
              </div>`
        : `
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="${lightColor}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z"></path>
                <circle cx="12" cy="13" r="3"></circle>
              </svg>`;

      const customIcon = L.divIcon({
        className: "custom-camera-marker-div",
        iconSize: [44, 44],
        iconAnchor: [22, 22],
        html: `
          <div class="camera-marker-container ${isSelected ? "camera-marker-selected" : ""}" style="width: 44px; height: 44px; cursor: pointer;">
            ${pulseHtml}
            <div style="
              width: 36px;
              height: 36px;
              border-radius: 50%;
              background: #ffffff;
              border: 2.5px solid ${lightColor};
              box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2)${isSelected ? ", 0 0 0 2px " + lightColor + "40" : ""};
              display: flex;
              align-items: center;
              justify-content: center;
              position: relative;
              z-index: 2;
              opacity: ${isOperating ? "1" : "0.55"};
            ">
              ${innerGlyph}
            </div>
          </div>
        `,
      });

      const marker = L.marker([lat, lon], { icon: customIcon });

      // Click handler
      marker.on("click", () => {
        onSelectCamera(camera);
        flyToCamera(camera.id, 0.8);
      });

      // Tooltip
      const tooltipLabel = !signalized
        ? isOperating
          ? "MONITORING"
          : camera.state.toUpperCase()
        : isOperating
        ? `${currentLight ? currentLight.toUpperCase() : "SYNCING"} SIGNAL`
        : camera.state.toUpperCase();

      marker.bindTooltip(
        `<strong style="color: #1f1915;">${camera.name}</strong><br/>
         <div style="display: flex; align-items: center; gap: 6px; margin-top: 3px;">
           <span style="width: 8px; height: 8px; border-radius: 50%; background: ${lightColor};${isOperating ? "" : " opacity: 0.6;"}"></span>
           <span style="color: ${lightColor}; font-weight: 700; text-transform: uppercase; font-size: 11px;">
             ${tooltipLabel}
           </span>
           ${isOperating ? `<span style="color: #6b675f; font-size: 10px;">• ${camera.state}</span>` : ""}
         </div>`,
        {
          direction: "top",
          offset: [0, -20],
          opacity: 0.95,
        }
      );

      marker.addTo(map);
      markersRef.current.set(camera.id, marker);
    });

    // Auto-fit bounds on initial load if we have valid coordinates
    if (bounds.length > 0 && !hasFittedBoundsRef.current) {
      map.fitBounds(bounds, { padding: [60, 60], maxZoom: 15 });
      hasFittedBoundsRef.current = true;
    }
  }, [cameras, selectedCameraId, onSelectCamera, flyToCamera]);

  // Handle explicit focus target dispatch (e.g. from toast click)
  useEffect(() => {
    if (!focusTarget) return;
    if (lastFocusTimestampRef.current === focusTarget.timestamp) return;
    lastFocusTimestampRef.current = focusTarget.timestamp;
    lastSelectedCameraIdRef.current = focusTarget.cameraId;

    flyToCamera(focusTarget.cameraId, 1.0);
  }, [focusTarget, flyToCamera]);

  // Handle external selectedCameraId changes if not already dispatched by focusTarget
  useEffect(() => {
    if (!selectedCameraId) {
      lastSelectedCameraIdRef.current = null;
      return;
    }
    if (lastSelectedCameraIdRef.current !== selectedCameraId) {
      lastSelectedCameraIdRef.current = selectedCameraId;
      flyToCamera(selectedCameraId, 0.8);
    }
  }, [selectedCameraId, flyToCamera]);

  return (
    <div className="relative h-full w-full">
      <div ref={mapContainerRef} className="h-full w-full outline-none z-10" />
    </div>
  );
}
