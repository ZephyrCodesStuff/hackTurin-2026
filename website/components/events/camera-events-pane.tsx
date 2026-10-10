"use client";

import React, { useState } from "react";
import {
  X,
  AlertTriangle,
  Radio,
  Footprints,
  Activity,
  Image as ImageIcon,
  ChevronUp,
  ChevronDown,
  RefreshCw,
  Gauge,
  Circle,
  Pencil,
  BarChart3,
  ScrollText,
} from "lucide-react";
import { Camera, CameraEvent, CrashEvent } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatRelativeTime, formatDateTime } from "@/lib/utils";
import { CrashPhotoModal } from "./crash-photo-modal";

interface CameraEventsPaneProps {
  camera: Camera | null;
  events: CameraEvent[];
  isLoading: boolean;
  onClose: () => void;
  onRefresh: () => void;
  initialFilter?: EventFilter;
}

type EventFilter = "all" | "crash" | "light_change" | "illegal_crossing" | "object_detected";

export function CameraEventsPane({
  camera,
  events,
  isLoading,
  onClose,
  onRefresh,
  initialFilter = "all",
}: CameraEventsPaneProps) {
  const [userSelectedFilter, setUserSelectedFilter] = useState<EventFilter | null>(null);
  const [prevInitialFilter, setPrevInitialFilter] = useState<EventFilter>(initialFilter);
  const [prevCameraId, setPrevCameraId] = useState<string | undefined>(camera?.id);

  if (initialFilter !== prevInitialFilter || camera?.id !== prevCameraId) {
    setPrevInitialFilter(initialFilter);
    setPrevCameraId(camera?.id);
    setUserSelectedFilter(null);
  }

  const filter = userSelectedFilter ?? initialFilter;
  const setFilter = (newFilter: EventFilter) => setUserSelectedFilter(newFilter);

  const [isMinimized, setIsMinimized] = useState(false);
  const [activePhoto, setActivePhoto] = useState<{
    photoId: string;
    timestamp: number;
  } | null>(null);

  if (!camera) return null;

  const filteredEvents = events.filter((e) => {
    if (filter === "all") return true;
    return e.type === filter;
  });

  const crashesCount = events.filter((e) => e.type === "crash").length;
  const lightCount = events.filter((e) => e.type === "light_change").length;
  const crossingCount = events.filter((e) => e.type === "illegal_crossing").length;
  const objectsCount = events.filter((e) => e.type === "object_detected").length;

  // Metric derivations
  const pedestrianCount = events.filter(
    (e) => (e.type === "object_detected" || e.type === "illegal_crossing") && e.entity_type === "pedestrian"
  ).length;
  const vehicleCount = events.filter(
    (e) =>
      e.type === "object_detected" &&
      (e.entity_type === "car" ||
        e.entity_type === "truck" ||
        e.entity_type === "motorbike" ||
        e.entity_type === "bike")
  ).length;
  const dangerLevel = crashesCount >= 3 ? "CRITICAL" : crashesCount >= 1 ? "ELEVATED" : "NORMAL";

  const latLonString = Array.isArray(camera.location)
    ? `${camera.location[0].toFixed(4)}, ${camera.location[1].toFixed(4)}`
    : camera.location || "Coordinates Unavailable";

  return (
    <>
      <div
        className={`absolute bottom-0 left-0 right-0 z-30 transition-all duration-300 ease-in-out border-t border-[#e7e5e0] bg-[#faf9f5] shadow-[0_-1px_3px_rgba(0,0,0,0.06)] ${
          isMinimized ? "h-14" : "h-72 md:h-80"
        } flex flex-col`}
      >
        {/* Pane Header */}
        <div className="flex h-14 items-center justify-between border-b border-[#e7e5e0] px-5">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-[#1f1915] text-sm sm:text-base">
                {camera.name}
              </span>
              <span className="font-mono text-xs text-[#8a857c]">
                ({camera.id.slice(0, 8)})
              </span>
            </div>
            <div className="hidden items-center gap-2 text-xs text-[#6b675f] sm:flex">
              <span>•</span>
              <span className="font-mono text-[11px] text-[#8a857c]">
                {latLonString}
              </span>
            </div>
            <Badge
              variant={
                camera.state === "online"
                  ? "success"
                  : camera.state === "maintenance"
                  ? "warning"
                  : "danger"
              }
              className="capitalize text-[10px]"
            >
              {camera.state}
            </Badge>
          </div>

          {/* Header Controls */}
          <div className="flex items-center gap-1.5">
            {onEditCamera && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onEditCamera(camera)}
                title="Edit camera settings"
                className="h-8 px-2 text-[#6b675f] hover:text-[#20808d]"
              >
                <Pencil className="h-3.5 w-3.5" />
                <span className="ml-1.5 hidden text-xs sm:inline">Edit</span>
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={onRefresh}
              disabled={isLoading}
              title="Refresh events"
              className="h-8 px-2 text-[#6b675f] hover:text-[#1f1915]"
            >
              <RefreshCw
                className={`h-3.5 w-3.5 ${isLoading ? "animate-spin text-[#20808d]" : ""}`}
              />
              <span className="ml-1.5 hidden text-xs sm:inline">Refresh</span>
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setIsMinimized(!isMinimized)}
              title={isMinimized ? "Expand pane" : "Minimize pane"}
              className="h-8 w-8 text-[#6b675f] hover:text-[#1f1915]"
            >
              {isMinimized ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={onClose}
              title="Close pane"
              className="h-8 w-8 text-[#6b675f] hover:text-[#c25450]"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Pane Body (Hidden when minimized) */}
        {!isMinimized && (
          <div className="flex flex-1 flex-col overflow-hidden">
            {/* Top Toolbar / Mode Selectors & Filters */}
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#e7e5e0] bg-[#f5f4ef] px-5 py-1.5 text-xs">
              <div className="flex items-center gap-1">
                {/* 1. General Metrics Overview Button (WIP) */}
                <button
                  onClick={() => setViewMode("metrics")}
                  title="General metrics overview (WIP)"
                  className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 font-medium transition-colors ${
                    viewMode === "metrics"
                      ? "bg-[#20808d] text-white shadow-xs"
                      : "text-[#6b675f] hover:bg-[#e7e5e0]/60 hover:text-[#1f1915]"
                  }`}
                >
                  <BarChart3 className="h-3.5 w-3.5" />
                  <span>Metrics</span>
                  <span
                    className={`rounded px-1 py-0.2 text-[9px] font-bold uppercase tracking-wider ${
                      viewMode === "metrics"
                        ? "bg-white/20 text-white"
                        : "bg-[#8a857c]/15 text-[#8a857c]"
                    }`}
                  >
                    WIP
                  </span>
                </button>

                {/* 2. Event Logs View Button */}
                <button
                  onClick={() => {
                    setViewMode("logs");
                  }}
                  title="Event logs (crashes, signal changes, crossings, detections)"
                  className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 font-medium transition-colors ${
                    viewMode === "logs"
                      ? "bg-[#20808d] text-white shadow-xs"
                      : "text-[#6b675f] hover:bg-[#e7e5e0]/60 hover:text-[#1f1915]"
                  }`}
                >
                  <ScrollText className="h-3.5 w-3.5" />
                  <span>Logs</span>
                  <span
                    className={`rounded-full px-1.5 py-0.2 text-[10px] font-mono ${
                      viewMode === "logs"
                        ? "bg-white/20 text-white"
                        : "bg-[#8a857c]/15 text-[#6b675f]"
                    }`}
                  >
                    {events.length}
                  </span>
                </button>
              </div>

              {/* Log Subfilters (Visible when in Logs mode) */}
              {viewMode === "logs" && (
                <div className="flex items-center gap-1 overflow-x-auto">
                  <span className="text-[#8a857c] mr-1 hidden sm:inline">Filter:</span>
                  <button
                    onClick={() => setFilter("all")}
                    className={`rounded-md px-2 py-0.5 text-xs font-medium transition-colors ${
                      filter === "all"
                        ? "bg-[#1f1915]/10 text-[#1f1915] font-semibold"
                        : "text-[#6b675f] hover:text-[#1f1915]"
                    }`}
                  >
                    All ({events.length})
                  </button>
                  <button
                    onClick={() => setFilter("crash")}
                    className={`flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium transition-colors ${
                      filter === "crash"
                        ? "bg-[#c25450]/15 text-[#a8423e] border border-[#c25450]/30 font-semibold"
                        : "text-[#6b675f] hover:text-[#1f1915]"
                    }`}
                  >
                    <AlertTriangle className="h-3 w-3 text-[#c25450]" />
                    Crashes ({crashesCount})
                  </button>
                  <button
                    onClick={() => setFilter("light_change")}
                    className={`flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium transition-colors ${
                      filter === "light_change"
                        ? "bg-[#c08a2d]/15 text-[#9a6e22] border border-[#c08a2d]/30 font-semibold"
                        : "text-[#6b675f] hover:text-[#1f1915]"
                    }`}
                  >
                    <Activity className="h-3 w-3 text-[#c08a2d]" />
                    Signals ({lightCount})
                  </button>
                  <button
                    onClick={() => setFilter("illegal_crossing")}
                    className={`flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium transition-colors ${
                      filter === "illegal_crossing"
                        ? "bg-[#8c6ba8]/15 text-[#6f5090] border border-[#8c6ba8]/30 font-semibold"
                        : "text-[#6b675f] hover:text-[#1f1915]"
                    }`}
                  >
                    <Footprints className="h-3 w-3 text-[#8c6ba8]" />
                    Crossings ({crossingCount})
                  </button>
                  <button
                    onClick={() => setFilter("object_detected")}
                    className={`flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium transition-colors ${
                      filter === "object_detected"
                        ? "bg-[#20808d]/15 text-[#20808d] border border-[#20808d]/30 font-semibold"
                        : "text-[#6b675f] hover:text-[#1f1915]"
                    }`}
                  >
                    <Radio className="h-3 w-3 text-[#20808d]" />
                    Detections ({objectsCount})
                  </button>
                </div>
              )}
            </div>

            {/* Pane Content View: Metrics (WIP) or Logs Feed */}
            {viewMode === "metrics" ? (
              <div className="flex-1 overflow-y-auto p-4">
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  {/* Metric 1: Danger Level Heuristic */}
                  <div className="rounded-lg border border-[#e7e5e0] bg-[#fdfbfa] p-3 shadow-2xs">
                    <div className="flex items-center justify-between text-xs text-[#6b675f]">
                      <span className="font-medium">Danger Level</span>
                      <AlertTriangle className={`h-3.5 w-3.5 ${dangerLevel === "CRITICAL" ? "text-[#c25450]" : dangerLevel === "ELEVATED" ? "text-[#c08a2d]" : "text-[#4f9d69]"}`} />
                    </div>
                    <div className="mt-2 flex items-baseline gap-2">
                      <span
                        className={`text-xl font-bold font-mono ${
                          dangerLevel === "CRITICAL"
                            ? "text-[#c25450]"
                            : dangerLevel === "ELEVATED"
                            ? "text-[#c08a2d]"
                            : "text-[#4f9d69]"
                        }`}
                      >
                        {dangerLevel}
                      </span>
                    </div>
                    <p className="mt-1 text-[11px] text-[#8a857c]">
                      {crashesCount} incident{crashesCount === 1 ? "" : "s"} logged on this node
                    </p>
                  </div>

                  {/* Metric 2: Pedestrians Tracked */}
                  <div className="rounded-lg border border-[#e7e5e0] bg-[#fdfbfa] p-3 shadow-2xs">
                    <div className="flex items-center justify-between text-xs text-[#6b675f]">
                      <span className="font-medium">Pedestrians Active</span>
                      <Footprints className="h-3.5 w-3.5 text-[#8c6ba8]" />
                    </div>
                    <div className="mt-2 flex items-baseline gap-2">
                      <span className="text-xl font-bold font-mono text-[#1f1915]">
                        {pedestrianCount}
                      </span>
                      <span className="text-xs text-[#8a857c]">detected</span>
                    </div>
                    <p className="mt-1 text-[11px] text-[#8a857c]">
                      {crossingCount} jaywalk / illegal crossing events
                    </p>
                  </div>

                  {/* Metric 3: Vehicles Tracked */}
                  <div className="rounded-lg border border-[#e7e5e0] bg-[#fdfbfa] p-3 shadow-2xs">
                    <div className="flex items-center justify-between text-xs text-[#6b675f]">
                      <span className="font-medium">Vehicles Tracked</span>
                      <Radio className="h-3.5 w-3.5 text-[#20808d]" />
                    </div>
                    <div className="mt-2 flex items-baseline gap-2">
                      <span className="text-xl font-bold font-mono text-[#1f1915]">
                        {vehicleCount}
                      </span>
                      <span className="text-xs text-[#8a857c]">units</span>
                    </div>
                    <p className="mt-1 text-[11px] text-[#8a857c]">
                      Realtime optical frame detections
                    </p>
                  </div>

                  {/* Metric 4: Traffic Signal Phase Cycling */}
                  <div className="rounded-lg border border-[#e7e5e0] bg-[#fdfbfa] p-3 shadow-2xs">
                    <div className="flex items-center justify-between text-xs text-[#6b675f]">
                      <span className="font-medium">Signal Cycles</span>
                      <Activity className="h-3.5 w-3.5 text-[#c08a2d]" />
                    </div>
                    <div className="mt-2 flex items-baseline gap-2">
                      <span className="text-xl font-bold font-mono text-[#1f1915]">
                        {lightCount}
                      </span>
                      <span className="text-xs text-[#8a857c]">state switches</span>
                    </div>
                    <p className="mt-1 text-[11px] text-[#8a857c]">
                      Red / Amber / Green phase triggers
                    </p>
                  </div>
                </div>

                <div className="mt-3 rounded-lg border border-dashed border-[#e7e5e0] bg-[#f5f4ef]/50 p-3 text-center text-xs text-[#8a857c]">
                  Detailed temporal charts and 10s throughput heuristics are coming up next. Click <strong>Logs</strong> above to inspect raw events.
                </div>
              </div>
            ) : (
              /* Events List Feed */
              <div className="flex-1 overflow-y-auto p-4">
              {isLoading ? (
                <div className="flex h-36 items-center justify-center text-sm text-[#6b675f]">
                  <RefreshCw className="mr-2 h-4 w-4 animate-spin text-[#20808d]" />
                  Loading camera events...
                </div>
              ) : filteredEvents.length === 0 ? (
                <div className="flex h-36 flex-col items-center justify-center text-center text-sm text-[#6b675f]">
                  <p className="font-medium text-[#1f1915]">No events captured</p>
                  <p className="text-xs text-[#8a857c] mt-0.5">
                    No matching events recorded for this camera yet.
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  {filteredEvents.map((evt) => (
                    <div
                      key={`${evt.type}-${evt.id}`}
                      className="group flex items-center justify-between rounded-lg border border-[#e7e5e0] bg-[#fdfbfa] p-2.5 transition-all hover:border-[#d6d3cc] hover:bg-[#f5f4ef]"
                    >
                      {/* Left: Event Type & Badge */}
                      <div className="flex items-center gap-3">
                        {evt.type === "crash" && (
                          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-[#c25450]/10 text-[#c25450] border border-[#c25450]/30">
                            <AlertTriangle className="h-4 w-4" />
                          </div>
                        )}
                        {evt.type === "light_change" && (
                          <div
                            className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-md border ${
                              evt.color === "red"
                                ? "bg-[#c25450]/10 text-[#c25450] border-[#c25450]/30"
                                : evt.color === "amber"
                                ? "bg-[#c08a2d]/10 text-[#c08a2d] border-[#c08a2d]/30"
                                : "bg-[#4f9d69]/10 text-[#4f9d69] border-[#4f9d69]/30"
                            }`}
                          >
                            <Circle className="h-4 w-4 fill-current" />
                          </div>
                        )}
                        {evt.type === "illegal_crossing" && (
                          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-[#8c6ba8]/10 text-[#8c6ba8] border border-[#8c6ba8]/30">
                            <Footprints className="h-4 w-4" />
                          </div>
                        )}
                        {evt.type === "object_detected" && (
                          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-[#20808d]/10 text-[#20808d] border border-[#20808d]/30">
                            <Radio className="h-4 w-4" />
                          </div>
                        )}

                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-semibold capitalize text-[#1f1915]">
                              {evt.type.replace("_", " ")}
                            </span>

                            {evt.type === "light_change" && (
                              <Badge
                                variant={
                                  evt.color === "green"
                                    ? "success"
                                    : evt.color === "amber"
                                    ? "warning"
                                    : "danger"
                                }
                                className="text-[10px] capitalize font-semibold"
                              >
                                {evt.color}
                              </Badge>
                            )}

                            {evt.type === "illegal_crossing" && (
                              <Badge
                                variant="outline"
                                className="text-[10px] capitalize border-[#8c6ba8]/30 text-[#6f5090] bg-[#8c6ba8]/10"
                              >
                                {evt.entity_type}
                              </Badge>
                            )}

                            {evt.type === "object_detected" && (
                              <Badge
                                variant="outline"
                                className="text-[10px] capitalize border-[#20808d]/30 text-[#20808d] bg-[#20808d]/10"
                              >
                                {evt.entity_type}
                              </Badge>
                            )}

                            {evt.type === "object_detected" &&
                              evt.velocity !== null &&
                              evt.velocity !== undefined && (
                                <span className="inline-flex items-center gap-1 text-[11px] font-mono text-[#20808d] bg-[#20808d]/10 border border-[#20808d]/30 px-1.5 py-0.5 rounded">
                                  <Gauge className="h-3 w-3" />
                                  {evt.velocity.toFixed(1)} km/h
                                </span>
                              )}
                          </div>

                          <div className="flex items-center gap-2 text-[11px] text-[#6b675f] mt-0.5">
                            <span>{formatDateTime(evt.timestamp)}</span>
                            <span>•</span>
                            <span className="text-[#8a857c]">
                              {formatRelativeTime(evt.timestamp)}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Right: Actions / Buttons */}
                      <div>
                        {evt.type === "crash" && (
                          <Button
                            size="sm"
                            variant="destructive"
                            onClick={() =>
                              setActivePhoto({
                                photoId: (evt as CrashEvent).photo_id,
                                timestamp: evt.timestamp,
                              })
                            }
                            className="h-7 gap-1.5 text-xs"
                          >
                            <ImageIcon className="h-3.5 w-3.5" />
                            View Photo
                          </Button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>

      {/* Crash Photo Lightbox Modal */}
      {activePhoto && (
        <CrashPhotoModal
          isOpen={!!activePhoto}
          onClose={() => setActivePhoto(null)}
          photoId={activePhoto.photoId}
          timestamp={activePhoto.timestamp}
          cameraName={camera.name}
        />
      )}
    </>
  );
}
