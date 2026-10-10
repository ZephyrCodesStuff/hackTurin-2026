"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Camera, CameraEvent } from "@/lib/types";
import { fetchCameras, fetchCameraEvents } from "@/lib/api";
import { CameraSidebar } from "@/components/sidebar/camera-sidebar";
import { MapWrapper } from "@/components/map/map-wrapper";
import { CameraTelemetryHud } from "@/components/hud/camera-telemetry-hud";
import { CameraEventsPane } from "@/components/events/camera-events-pane";
import { LoginGate } from "@/components/auth/login-gate";
import { EditCameraDialog } from "@/components/cameras/edit-camera-dialog";

function DashboardContent() {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [selectedCamera, setSelectedCamera] = useState<Camera | null>(null);
  const [editingCamera, setEditingCamera] = useState<Camera | null>(null);
  const [events, setEvents] = useState<CameraEvent[]>([]);
  const [isCamerasLoading, setIsCamerasLoading] = useState(true);
  const [isEventsLoading, setIsEventsLoading] = useState(false);
  const [isMockData, setIsMockData] = useState(false);

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
    } finally {
      setIsCamerasLoading(false);
    }
  }, []);

  // Initial load & auto-polling
  useEffect(() => {
    let isMounted = true;
    (async () => {
      try {
        const { cameras: loadedCameras, isMock } = await fetchCameras();
        if (isMounted) {
          setCameras(loadedCameras);
          setIsMockData(isMock);
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
  }, [loadCameras]);

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
    (camera: Camera) => {
      setSelectedCamera(camera);
      loadEvents(camera.id);
    },
    [loadEvents]
  );

  const handleCloseEventsPane = useCallback(() => {
    setSelectedCamera(null);
    setEvents([]);
  }, []);

  const handleCameraUpdated = useCallback((updatedCamera: Camera) => {
    setCameras((prev) =>
      prev.map((c) => (c.id === updatedCamera.id ? updatedCamera : c))
    );
    setSelectedCamera((prev) =>
      prev?.id === updatedCamera.id ? updatedCamera : prev
    );
  }, []);

  return (
    <>
      <div className="flex h-screen w-screen overflow-hidden bg-[#faf9f5] font-sans text-[#1f1915] select-none">
        {/* 1. Left Sidebar (18 - 20% max width) */}
        <CameraSidebar
          cameras={cameras}
          selectedCameraId={selectedCamera?.id || null}
          onSelectCamera={handleSelectCamera}
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
            onSelectCamera={handleSelectCamera}
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
              onClose={handleCloseEventsPane}
              onRefresh={() => loadEvents(selectedCamera.id)}
              onEditCamera={setEditingCamera}
            />
          )}
        </main>
      </div>

      {/* Fullscreen Camera Configuration Dialog */}
      <EditCameraDialog
        isOpen={!!editingCamera}
        camera={editingCamera}
        onClose={() => setEditingCamera(null)}
        onCameraUpdated={handleCameraUpdated}
      />
    </>
  );
}

export default function DashboardPage() {
  return (
    <LoginGate>
      <DashboardContent />
    </LoginGate>
  );
}
