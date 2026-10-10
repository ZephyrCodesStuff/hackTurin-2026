"use client";

import React, { useState } from "react";
import {
  Search,
  Cctv,
  Battery,
  Wifi,
  RefreshCw,
  ChevronRight,
  Radio,
} from "lucide-react";
import { Camera, CameraState } from "@/lib/types";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatRelativeTime } from "@/lib/utils";

interface CameraSidebarProps {
  cameras: Camera[];
  selectedCameraId: string | null;
  onSelectCamera: (camera: Camera) => void;
  isLoading: boolean;
  onRefresh: () => void;
  isMockData: boolean;
}

export function CameraSidebar({
  cameras,
  selectedCameraId,
  onSelectCamera,
  isLoading,
  onRefresh,
  isMockData,
}: CameraSidebarProps) {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | CameraState>("all");

  const filteredCameras = cameras.filter((cam) => {
    const matchesSearch =
      cam.name.toLowerCase().includes(search.toLowerCase()) ||
      cam.id.toLowerCase().includes(search.toLowerCase());

    const matchesStatus =
      statusFilter === "all" ? true : cam.state === statusFilter;

    return matchesSearch && matchesStatus;
  });

  return (
    <aside className="relative flex h-full w-[20%] min-w-[260px] max-w-[360px] shrink-0 flex-col border-r border-slate-800 bg-slate-950/95 z-20 shadow-xl backdrop-blur-md">
      {/* Brand / Header */}
      <div className="flex flex-col border-b border-slate-800 p-3.5 gap-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600/20 text-blue-400 border border-blue-500/30">
              <Cctv className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-white tracking-tight">
                Traffic Grid
              </h2>
              <p className="text-[10px] text-slate-400">
                Urban Surveillance Fleet
              </p>
            </div>
          </div>

          <Button
            variant="ghost"
            size="icon"
            onClick={onRefresh}
            disabled={isLoading}
            className="h-7 w-7 text-slate-400 hover:text-white"
            title="Refresh Cameras"
          >
            <RefreshCw
              className={`h-3.5 w-3.5 ${isLoading ? "animate-spin text-blue-400" : ""}`}
            />
          </Button>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-500" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search camera or ID..."
            className="h-8 pl-8 text-xs bg-slate-900 border-slate-800 text-slate-200 placeholder:text-slate-500"
          />
        </div>

        {/* Status Filters */}
        <div className="flex items-center gap-1 text-[11px]">
          {(["all", "online", "maintenance", "offline"] as const).map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`flex-1 rounded py-1 text-center font-medium capitalize transition-colors ${
                statusFilter === st
                  ? "bg-slate-800 text-blue-400 shadow-xs"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Cameras List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
        {filteredCameras.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-6 text-center text-xs text-slate-500">
            <Radio className="h-6 w-6 text-slate-600 mb-2" />
            <p className="font-semibold text-slate-400">No cameras found</p>
            <p className="text-[11px] text-slate-600">Try adjusting your search</p>
          </div>
        ) : (
          filteredCameras.map((camera) => {
            const isSelected = selectedCameraId === camera.id;
            return (
              <div
                key={camera.id}
                onClick={() => onSelectCamera(camera)}
                className={`group relative flex cursor-pointer flex-col rounded-xl border p-2.5 transition-all select-none ${
                  isSelected
                    ? "border-blue-500/80 bg-blue-950/25 shadow-lg shadow-blue-950/30 ring-1 ring-blue-500/40"
                    : "border-slate-800/80 bg-slate-900/40 hover:border-slate-700 hover:bg-slate-900/80"
                }`}
              >
                {/* Top Row: Name and Status Dot */}
                <div className="flex items-center justify-between gap-1">
                  <div className="flex items-center gap-2 truncate">
                    <span
                      className={`h-2.5 w-2.5 rounded-full shrink-0 shadow-sm ${
                        camera.current_light === "green"
                          ? "bg-emerald-400 shadow-emerald-400 animate-pulse"
                          : camera.current_light === "amber"
                          ? "bg-amber-400 shadow-amber-400"
                          : camera.current_light === "red"
                          ? "bg-rose-500 shadow-rose-500"
                          : camera.state === "online"
                          ? "bg-blue-400"
                          : "bg-slate-600"
                      }`}
                      title={camera.current_light ? `Traffic Light: ${camera.current_light}` : camera.state}
                    />
                    <h4
                      className={`text-xs font-semibold truncate ${
                        isSelected ? "text-white" : "text-slate-200 group-hover:text-white"
                      }`}
                    >
                      {camera.name}
                    </h4>
                  </div>
                  <ChevronRight
                    className={`h-3.5 w-3.5 shrink-0 transition-transform ${
                      isSelected
                        ? "text-blue-400 translate-x-0.5"
                        : "text-slate-600 group-hover:text-slate-400"
                    }`}
                  />
                </div>

                {/* Subtitle / ID */}
                <div className="mt-1 flex items-center justify-between text-[11px] text-slate-400">
                  <span className="font-mono text-[10px] text-slate-400">
                    ID: {camera.id.slice(0, 8)}...
                  </span>
                  <span className="text-[10px] text-slate-400">
                    {formatRelativeTime(camera.last_heartbeat)}
                  </span>
                </div>

                {/* Bottom Row Telemetry Micro-Badges */}
                <div className="mt-2 flex items-center justify-between pt-1.5 border-t border-slate-800/60 text-[10px] text-slate-400">
                  <div className="flex items-center gap-1">
                    <Battery className="h-3 w-3 text-slate-400" />
                    <span>
                      {camera.battery_level !== null && camera.battery_level !== undefined
                        ? `${Math.round(camera.battery_level)}%`
                        : "--"}
                    </span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Wifi className="h-3 w-3 text-slate-400" />
                    <span>
                      {camera.wifi_signal !== null && camera.wifi_signal !== undefined
                        ? `${camera.wifi_signal} dBm`
                        : "--"}
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    {camera.current_light && (
                      <span
                        className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider ${
                          camera.current_light === "green"
                            ? "bg-emerald-950/80 text-emerald-300 border border-emerald-800/60"
                            : camera.current_light === "amber"
                            ? "bg-amber-950/80 text-amber-300 border border-amber-800/60"
                            : "bg-rose-950/80 text-rose-300 border border-rose-800/60"
                        }`}
                      >
                        <span
                          className={`h-1.5 w-1.5 rounded-full ${
                            camera.current_light === "green"
                              ? "bg-emerald-400"
                              : camera.current_light === "amber"
                              ? "bg-amber-400"
                              : "bg-rose-400"
                          }`}
                        />
                        {camera.current_light}
                      </span>
                    )}
                    <Badge
                      variant={
                        camera.state === "online"
                          ? "success"
                          : camera.state === "maintenance"
                          ? "warning"
                          : "danger"
                      }
                      className="text-[9px] uppercase px-1.5 py-0 h-4"
                    >
                      {camera.state}
                    </Badge>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Footer Info */}
      <div className="border-t border-slate-800 bg-slate-900/60 p-2.5 text-center text-[10px] text-slate-500">
        <span>{filteredCameras.length} of {cameras.length} cameras visible</span>
        {isMockData && (
          <span className="block text-amber-500/80 font-medium mt-0.5">
            Fallback Demo Mode Active
          </span>
        )}
      </div>
    </aside>
  );
}
