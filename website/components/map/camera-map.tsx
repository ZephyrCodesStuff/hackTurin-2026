"use client";

import React, { useEffect, useRef } from "react";
import L from "leaflet";
import { Camera } from "@/lib/types";

interface CameraMapProps {
  cameras: Camera[];
  selectedCameraId: string | null;
  onSelectCamera: (camera: Camera) => void;
}

export default function CameraMap({
  cameras,
  selectedCameraId,
  onSelectCamera,
}: CameraMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const markersRef = useRef<Map<string, L.Marker>>(new Map());
  const hasFittedBoundsRef = useRef(false);

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
      className: "osm-dark-tiles",
    }).addTo(map);

    // Zoom control at bottom right
    L.control.zoom({ position: "bottomright" }).addTo(map);

    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Update Markers when cameras list or selection changes
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    // Clear old markers
    markersRef.current.forEach((marker) => marker.remove());
    markersRef.current.clear();

    const bounds: [number, number][] = [];

    cameras.forEach((camera) => {
      let lat: number | null = null;
      let lon: number | null = null;

      if (Array.isArray(camera.location) && camera.location.length >= 2) {
        lat = camera.location[0];
        lon = camera.location[1];
      } else if (camera.latitude != null && camera.longitude != null) {
        lat = camera.latitude;
        lon = camera.longitude;
      }

      if (lat == null || lon == null) return;

      bounds.push([lat, lon]);

      const isSelected = selectedCameraId === camera.id;

      // Color primarily driven by current traffic light state, fallback to operational state
      const currentLight = camera.current_light;
      const isOffline = camera.state === "offline";

      const lightColor =
        currentLight === "green"
          ? "#10b981"
          : currentLight === "amber"
          ? "#f59e0b"
          : currentLight === "red"
          ? "#ef4444"
          : camera.state === "online"
          ? "#3b82f6"
          : camera.state === "maintenance"
          ? "#f59e0b"
          : "#64748b";

      const pulseHtml = !isOffline
        ? `<span class="pulse-ring" style="background-color: ${lightColor}40; width: 46px; height: 46px;"></span>`
        : "";

      // Traffic Signal Icon with 3 mini lamps (Red, Yellow, Green)
      const isRedActive = currentLight === "red";
      const isAmberActive = currentLight === "amber";
      const isGreenActive = currentLight === "green";

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
              background: #090d16;
              border: 2.5px solid ${lightColor};
              box-shadow: 0 0 ${isSelected ? "18px" : "10px"} ${lightColor}bb;
              display: flex;
              align-items: center;
              justify-content: center;
              position: relative;
              z-index: 2;
              opacity: ${isOffline ? "0.6" : "1"};
            ">
              <!-- Mini 3-lamp traffic signal widget -->
              <div style="display: flex; flex-direction: column; align-items: center; gap: 2.5px;">
                <span style="
                  width: 6px;
                  height: 6px;
                  border-radius: 50%;
                  background: ${isRedActive ? "#ef4444" : "#ef444433"};
                  box-shadow: ${isRedActive ? "0 0 6px #ef4444" : "none"};
                "></span>
                <span style="
                  width: 6px;
                  height: 6px;
                  border-radius: 50%;
                  background: ${isAmberActive ? "#f59e0b" : "#f59e0b33"};
                  box-shadow: ${isAmberActive ? "0 0 6px #f59e0b" : "none"};
                "></span>
                <span style="
                  width: 6px;
                  height: 6px;
                  border-radius: 50%;
                  background: ${isGreenActive ? "#10b981" : "#10b98133"};
                  box-shadow: ${isGreenActive ? "0 0 6px #10b981" : "none"};
                "></span>
              </div>
            </div>
          </div>
        `,
      });

      const marker = L.marker([lat, lon], { icon: customIcon });

      // Click handler
      marker.on("click", () => {
        onSelectCamera(camera);
        map.flyTo([lat, lon], Math.max(map.getZoom(), 15), {
          duration: 0.8,
        });
      });

      // Tooltip hover with live traffic light color badge
      const lightLabel = currentLight ? currentLight.toUpperCase() : "SYNCING";
      marker.bindTooltip(
        `<strong>${camera.name}</strong><br/>
         <div style="display: flex; align-items: center; gap: 6px; margin-top: 3px;">
           <span style="width: 8px; height: 8px; border-radius: 50%; background: ${lightColor}; box-shadow: 0 0 6px ${lightColor};"></span>
           <span style="color: ${lightColor}; font-weight: 700; text-transform: uppercase; font-size: 11px;">
             ${lightLabel} SIGNAL
           </span>
           <span style="color: #64748b; font-size: 10px;">• ${camera.state}</span>
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
  }, [cameras, selectedCameraId, onSelectCamera]);

  // Fly to selected camera when selectedCameraId updates externally
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !selectedCameraId) return;

    const camera = cameras.find((c) => c.id === selectedCameraId);
    if (!camera) return;

    let lat: number | null = null;
    let lon: number | null = null;

    if (Array.isArray(camera.location) && camera.location.length >= 2) {
      lat = camera.location[0];
      lon = camera.location[1];
    } else if (camera.latitude != null && camera.longitude != null) {
      lat = camera.latitude;
      lon = camera.longitude;
    }

    if (lat != null && lon != null) {
      map.flyTo([lat, lon], 16, {
        duration: 1.0,
      });
    }
  }, [selectedCameraId, cameras]);

  return (
    <div className="relative h-full w-full">
      <div ref={mapContainerRef} className="h-full w-full outline-none z-10" />
    </div>
  );
}
