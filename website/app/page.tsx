"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { toast, Toaster } from "sonner";
import { Camera, CameraEvent, CrashEvent } from "@/lib/types";
import { fetchCameras, fetchCameraEvents } from "@/lib/api";
import { hasNotifiedCrash, markCrashAsNotified } from "@/lib/alerts-store";
import { CameraSidebar } from "@/components/sidebar/camera-sidebar";
import { MapWrapper } from "@/components/map/map-wrapper";
import { CameraTelemetryHud } from "@/components/hud/camera-telemetry-hud";
import { CameraEventsPane } from "@/components/events/camera-events-pane";

// Alert threshold: only notify for crashes younger than 15 minutes
const CRASH_RECENCY_WINDOW_MS = 15 * 60 * 1000;

function DashboardContent() {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [selectedCamera, setSelectedCamera] = useState<Camera | null>(null);
  const [editingCamera, setEditingCamera] = useState<Camera | null>(null);
  const [events, setEvents] = useState<CameraEvent[]>([]);
  const [paneFilter, setPaneFilter] = useState<"all" | "crash">("all");
  const [focusTarget, setFocusTarget] = useState<{ cameraId: string; timestamp: number } | null>(null);
  const [isCamerasLoading, setIsCamerasLoading] = useState(true);
  const [isEventsLoading, setIsEventsLoading] = useState(false);
  const [isMockData, setIsMockData] = useState(false);

  // Keep a ref of latest cameras for toast click closures
  const camerasRef = useRef<Camera[]>([]);
  camerasRef.current = cameras;

  // Track latest check timestamp per camera to avoid re-checking stale events
  const cameraLastCheckedRef = useRef<Record<string, number>>({});
  const isInitialLoadRef = useRef(true);

  // Load events when a camera is selected
  const loadEvents = useCallback(async (cameraId: string) => {
    setIsEventsLoading(true);
    try {
      const { data } = await fetchCameraEvents(cameraId);
      setEvents(data.events || []);
    } finally {
      setIsEventsLoading(false);
    }
  }, []);

  const handleSelectCamera = useCallback(
    (camera: Camera, filter: "all" | "crash" = "all") => {
      setSelectedCamera(camera);
      setPaneFilter(filter);
      setFocusTarget({ cameraId: camera.id, timestamp: Date.now() });
      loadEvents(camera.id);
    },
    [loadEvents]
  );

  const handleCloseEventsPane = useCallback(() => {
    setSelectedCamera(null);
    setEvents([]);
    setPaneFilter("all");
    setFocusTarget(null);
  }, []);

  // Inspect fresh camera list for new crashes and dispatch Sonner alerts
  const checkCrashesForCameras = useCallback(
    async (cameraList: Camera[]) => {
      const now = Date.now();
      const cutoff = now - CRASH_RECENCY_WINDOW_MS;

      for (const cam of cameraList) {
        // Skip offline cameras or cameras whose last event is older than cutoff
        if (cam.last_event_timestamp && cam.last_event_timestamp < cutoff) {
          continue;
        }

        // If camera hasn't changed since last check, skip fetching events
        const prevChecked = cameraLastCheckedRef.current[cam.id];
        if (prevChecked && cam.last_event_timestamp && cam.last_event_timestamp <= prevChecked) {
          continue;
        }
        cameraLastCheckedRef.current[cam.id] = cam.last_event_timestamp || now;

        try {
          const { data } = await fetchCameraEvents(cam.id);
          const camEvents = data.events || [];
          const recentCrashes = camEvents.filter(
            (e): e is CrashEvent => e.type === "crash" && e.timestamp >= cutoff
          );

          for (const crash of recentCrashes) {
            const crashKey = crash.photo_id || `${cam.id}_${crash.timestamp}`;
            const alreadyNotified = await hasNotifiedCrash(crashKey);

            if (!alreadyNotified) {
              await markCrashAsNotified(crashKey);

              // If it's not the initial mounting hydration, fire toast
              if (!isInitialLoadRef.current) {
                const minutesAgo = Math.max(0, Math.round((now - crash.timestamp) / 60000));
                toast.warning(`Incident Detected: ${cam.name}`, {
                  description: `Crash reported ${minutesAgo === 0 ? "just now" : `${minutesAgo}m ago`}`,
                  duration: 9000,
                  action: {
                    label: "View Incident",
                    onClick: () => {
                      const latestCam = camerasRef.current.find((c) => c.id === cam.id) || cam;
                      handleSelectCamera(latestCam, "crash");
                    },
                  },
                });
              }
            }
          }
        } catch (err) {
          console.warn(`Failed to inspect events for alerts on ${cam.id}:`, err);
        }
      }

      if (isInitialLoadRef.current) {
        isInitialLoadRef.current = false;
      }
    },
    [handleSelectCamera]
  );

  // Load cameras
  const loadCameras = useCallback(async () => {
    try {
      const { cameras: loadedCameras, isMock } = await fetchCameras();
      setCameras(loadedCameras);
      setIsMockData(isMock);

      // Keep selected camera synced with fresh data if present
      setSelectedCamera((prev) => {
        if (!prev) return null;
        return loadedCameras.find((c) => c.id === prev.id) || prev;
      });

      // Check crashes asynchronously without blocking render
      checkCrashesForCameras(loadedCameras);
    } finally {
      setIsCamerasLoading(false);
    }
  }, [checkCrashesForCameras]);

  // Initial load & 3s auto-polling
  useEffect(() => {
    let isMounted = true;
    (async () => {
      try {
        const { cameras: loadedCameras, isMock } = await fetchCameras();
        if (isMounted) {
          setCameras(loadedCameras);
          setIsMockData(isMock);
          checkCrashesForCameras(loadedCameras);
        }
      } finally {
        if (isMounted) {
          setIsCamerasLoading(false);
        }
      }
    })();

    const interval = setInterval(() => {
      loadCameras();
    }, 3000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [loadCameras, checkCrashesForCameras]);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#faf9f5] font-sans text-[#1f1915] select-none">
      {/* Toast notifications */}
      <Toaster position="top-right" richColors theme="light" />

      {/* 1. Left Sidebar (18 - 20% max width) */}
      <CameraSidebar
        cameras={cameras}
        selectedCameraId={selectedCamera?.id || null}
        onSelectCamera={(c) => handleSelectCamera(c, "all")}
        isLoading={isCamerasLoading}
        onRefresh={loadCameras}
        isMockData={isMockData}
      />

      {/* 2. Main Map Viewport (Takes up the entire rest of viewport) */}
      <main className="relative flex-1 h-full w-full overflow-hidden bg-stone-100">
        {/* OpenStreetMap Layer */}
        <MapWrapper
          cameras={cameras}
          selectedCameraId={selectedCamera?.id || null}
          onSelectCamera={(c) => handleSelectCamera(c, "all")}
          focusTarget={focusTarget}
          isPaneOpen={Boolean(selectedCamera)}
        />

          {/* 3. Top-Right Telemetry & Heartbeat HUD Box */}
          <CameraTelemetryHud
            selectedCamera={selectedCamera}
            allCameras={cameras}
            isMockData={isMockData}
            onEditCamera={setEditingCamera}
          />

        {/* 4. Bottom Detail & Events Feed Pane */}
        {selectedCamera && (
          <CameraEventsPane
            camera={selectedCamera}
            events={events}
            isLoading={isEventsLoading}
            initialFilter={paneFilter}
            onClose={handleCloseEventsPane}
            onRefresh={() => loadEvents(selectedCamera.id)}
          />
        )}
      </main>
    </div>
  );
}
