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
}

type EventFilter = "all" | "crash" | "light_change" | "illegal_crossing" | "object_detected";

export function CameraEventsPane({
  camera,
  events,
  isLoading,
  onClose,
  onRefresh,
}: CameraEventsPaneProps) {
  const [filter, setFilter] = useState<EventFilter>("all");
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

  const latLonString = Array.isArray(camera.location)
    ? `${camera.location[0].toFixed(4)}, ${camera.location[1].toFixed(4)}`
    : camera.location || "Coordinates Unavailable";

  return (
    <>
      <div
        className={`absolute bottom-0 left-[20%] right-0 z-30 transition-all duration-300 ease-in-out border-t border-slate-800 bg-slate-950/95 shadow-2xl backdrop-blur-xl ${
          isMinimized ? "h-14" : "h-72 md:h-80"
        } flex flex-col`}
      >
        {/* Pane Header */}
        <div className="flex h-14 items-center justify-between border-b border-slate-800 px-5">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-white text-sm sm:text-base">
                {camera.name}
              </span>
              <span className="font-mono text-xs text-slate-400">
                ({camera.id.slice(0, 8)})
              </span>
            </div>
            <div className="hidden items-center gap-2 text-xs text-slate-400 sm:flex">
              <span>•</span>
              <span className="font-mono text-[11px] text-slate-400">
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
              className="uppercase tracking-wider text-[10px]"
            >
              {camera.state}
            </Badge>
          </div>

          {/* Header Controls */}
          <div className="flex items-center gap-1.5">
            <Button
              variant="ghost"
              size="sm"
              onClick={onRefresh}
              disabled={isLoading}
              title="Refresh events"
              className="h-8 px-2 text-slate-400 hover:text-white"
            >
              <RefreshCw
                className={`h-3.5 w-3.5 ${isLoading ? "animate-spin text-blue-400" : ""}`}
              />
              <span className="ml-1.5 hidden text-xs sm:inline">Refresh</span>
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setIsMinimized(!isMinimized)}
              title={isMinimized ? "Expand pane" : "Minimize pane"}
              className="h-8 w-8 text-slate-400 hover:text-white"
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
              className="h-8 w-8 text-slate-400 hover:text-rose-400"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Pane Body (Hidden when minimized) */}
        {!isMinimized && (
          <div className="flex flex-1 flex-col overflow-hidden">
            {/* Filter Tabs */}
            <div className="flex items-center gap-1 border-b border-slate-800/80 bg-slate-900/60 px-5 py-1.5 text-xs">
              <button
                onClick={() => setFilter("all")}
                className={`rounded-md px-2.5 py-1 font-medium transition-colors ${
                  filter === "all"
                    ? "bg-slate-800 text-blue-400 shadow-sm"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                All Events ({events.length})
              </button>
              <button
                onClick={() => setFilter("crash")}
                className={`flex items-center gap-1 rounded-md px-2.5 py-1 font-medium transition-colors ${
                  filter === "crash"
                    ? "bg-rose-950/60 text-rose-300 border border-rose-800/40"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <AlertTriangle className="h-3 w-3 text-rose-400" />
                Crashes ({crashesCount})
              </button>
              <button
                onClick={() => setFilter("light_change")}
                className={`flex items-center gap-1 rounded-md px-2.5 py-1 font-medium transition-colors ${
                  filter === "light_change"
                    ? "bg-amber-950/60 text-amber-300 border border-amber-800/40"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <Activity className="h-3 w-3 text-amber-400" />
                Signal Changes ({lightCount})
              </button>
              <button
                onClick={() => setFilter("illegal_crossing")}
                className={`flex items-center gap-1 rounded-md px-2.5 py-1 font-medium transition-colors ${
                  filter === "illegal_crossing"
                    ? "bg-purple-950/60 text-purple-300 border border-purple-800/40"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <Footprints className="h-3 w-3 text-purple-400" />
                Crossings ({crossingCount})
              </button>
              <button
                onClick={() => setFilter("object_detected")}
                className={`flex items-center gap-1 rounded-md px-2.5 py-1 font-medium transition-colors ${
                  filter === "object_detected"
                    ? "bg-blue-950/60 text-blue-300 border border-blue-800/40"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <Radio className="h-3 w-3 text-blue-400" />
                Detections ({objectsCount})
              </button>
            </div>

            {/* Events List */}
            <div className="flex-1 overflow-y-auto p-4">
              {isLoading ? (
                <div className="flex h-36 items-center justify-center text-sm text-slate-400">
                  <RefreshCw className="mr-2 h-4 w-4 animate-spin text-blue-500" />
                  Loading camera events...
                </div>
              ) : filteredEvents.length === 0 ? (
                <div className="flex h-36 flex-col items-center justify-center text-center text-sm text-slate-400">
                  <p className="font-medium text-slate-300">No events captured</p>
                  <p className="text-xs text-slate-500 mt-0.5">
                    No matching events recorded for this camera yet.
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  {filteredEvents.map((evt) => (
                    <div
                      key={`${evt.type}-${evt.id}`}
                      className="group flex items-center justify-between rounded-lg border border-slate-800/80 bg-slate-900/50 p-2.5 transition-all hover:border-slate-700 hover:bg-slate-900"
                    >
                      {/* Left: Event Type & Badge */}
                      <div className="flex items-center gap-3">
                        {evt.type === "crash" && (
                          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-rose-500/15 text-rose-400 border border-rose-500/30">
                            <AlertTriangle className="h-4 w-4" />
                          </div>
                        )}
                        {evt.type === "light_change" && (
                          <div
                            className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-md border ${
                              evt.color === "red"
                                ? "bg-rose-500/20 text-rose-400 border-rose-500/40"
                                : evt.color === "amber"
                                ? "bg-amber-500/20 text-amber-400 border-amber-500/40"
                                : "bg-emerald-500/20 text-emerald-400 border-emerald-500/40"
                            }`}
                          >
                            <Circle className="h-4 w-4 fill-current" />
                          </div>
                        )}
                        {evt.type === "illegal_crossing" && (
                          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-purple-500/15 text-purple-400 border border-purple-500/30">
                            <Footprints className="h-4 w-4" />
                          </div>
                        )}
                        {evt.type === "object_detected" && (
                          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-blue-500/15 text-blue-400 border border-blue-500/30">
                            <Radio className="h-4 w-4" />
                          </div>
                        )}

                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-semibold uppercase tracking-wider text-slate-200">
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
                                className="text-[10px] uppercase font-bold"
                              >
                                {evt.color}
                              </Badge>
                            )}

                            {evt.type === "illegal_crossing" && (
                              <Badge
                                variant="outline"
                                className="text-[10px] capitalize border-purple-800 text-purple-300 bg-purple-950/40"
                              >
                                {evt.entity_type}
                              </Badge>
                            )}

                            {evt.type === "object_detected" && (
                              <Badge
                                variant="outline"
                                className="text-[10px] capitalize border-blue-800 text-blue-300 bg-blue-950/40"
                              >
                                {evt.entity_type}
                              </Badge>
                            )}

                            {evt.type === "object_detected" &&
                              evt.velocity !== null &&
                              evt.velocity !== undefined && (
                                <span className="inline-flex items-center gap-1 text-[11px] font-mono text-cyan-400 bg-cyan-950/40 border border-cyan-800/40 px-1.5 py-0.5 rounded">
                                  <Gauge className="h-3 w-3" />
                                  {evt.velocity.toFixed(1)} km/h
                                </span>
                              )}
                          </div>

                          <div className="flex items-center gap-2 text-[11px] text-slate-400 mt-0.5">
                            <span>{formatDateTime(evt.timestamp)}</span>
                            <span>•</span>
                            <span className="text-slate-500">
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
                            className="h-7 gap-1.5 text-xs bg-rose-600/90 hover:bg-rose-500"
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
