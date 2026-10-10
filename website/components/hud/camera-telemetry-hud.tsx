"use client";

import React, { useState } from "react";
import {
  Activity,
  Battery,
  BatteryWarning,
  Wifi,
  Cpu,
  Clock,
  Compass,
  Copy,
  Check,
  Layers,
} from "lucide-react";
import { Camera } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatRelativeTime } from "@/lib/utils";

interface CameraTelemetryHudProps {
  selectedCamera: Camera | null;
  allCameras: Camera[];
  isMockData: boolean;
}

export function CameraTelemetryHud({
  selectedCamera,
  allCameras,
  isMockData,
}: CameraTelemetryHudProps) {
  const [copied, setCopied] = useState(false);

  const handleCopyId = (id: string) => {
    navigator.clipboard.writeText(id);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getWifiBars = (rssi: number | null | undefined) => {
    if (rssi === null || rssi === undefined) return 0;
    if (rssi >= -60) return 4;
    if (rssi >= -70) return 3;
    if (rssi >= -80) return 2;
    return 1;
  };

  const onlineCount = allCameras.filter((c) => c.state === "online").length;
  const maintenanceCount = allCameras.filter((c) => c.state === "maintenance").length;
  const offlineCount = allCameras.filter((c) => c.state === "offline").length;

  return (
    <div className="absolute top-4 right-4 z-20 w-80 sm:w-88 rounded-2xl border border-slate-700/60 bg-slate-950/85 p-4 shadow-2xl backdrop-blur-xl transition-all">
      {selectedCamera ? (
        /* Selected Camera HUD View */
        <div className="space-y-3.5">
          {/* Header */}
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="flex h-2 w-2 rounded-full bg-blue-500 animate-ping" />
                <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Telemetry Monitor
                </h4>
              </div>
              <h3 className="font-bold text-white text-sm sm:text-base leading-tight">
                {selectedCamera.name}
              </h3>
            </div>
            <Badge
              variant={
                selectedCamera.state === "online"
                  ? "success"
                  : selectedCamera.state === "maintenance"
                  ? "warning"
                  : "danger"
              }
              className="uppercase tracking-wider text-[11px] font-bold"
            >
              {selectedCamera.state}
            </Badge>
          </div>

          {/* UUID Copy Bar */}
          <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900/60 px-2.5 py-1.5 text-xs text-slate-400">
            <span className="font-mono text-[11px] text-slate-300 truncate max-w-[210px]">
              {selectedCamera.id}
            </span>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 text-slate-400 hover:text-white"
              onClick={() => handleCopyId(selectedCamera.id)}
              title="Copy UUID"
            >
              {copied ? (
                <Check className="h-3.5 w-3.5 text-emerald-400" />
              ) : (
                <Copy className="h-3.5 w-3.5" />
              )}
            </Button>
          </div>

          {/* Active Traffic Signal HUD */}
          <div className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-900/80 p-3">
            <div className="space-y-0.5">
              <span className="text-[10px] uppercase font-semibold text-slate-400">
                Active Traffic Signal
              </span>
              <div className="flex items-center gap-2">
                <span
                  className={`text-sm font-bold uppercase tracking-wider ${
                    selectedCamera.current_light === "green"
                      ? "text-emerald-400"
                      : selectedCamera.current_light === "amber"
                      ? "text-amber-400"
                      : selectedCamera.current_light === "red"
                      ? "text-rose-400"
                      : "text-slate-400"
                  }`}
                >
                  {selectedCamera.current_light || "Syncing"}
                </span>
                {selectedCamera.current_light_timestamp && (
                  <span className="text-[10px] text-slate-500">
                    ({formatRelativeTime(selectedCamera.current_light_timestamp)})
                  </span>
                )}
              </div>
            </div>

            {/* 3-Lamp Illuminated Signal Head */}
            <div className="flex items-center gap-1.5 rounded-lg border border-slate-800 bg-black/60 px-2.5 py-1.5">
              <span
                className={`h-3 w-3 rounded-full transition-all ${
                  selectedCamera.current_light === "red"
                    ? "bg-rose-500 shadow-md shadow-rose-500 scale-110"
                    : "bg-rose-950/60 opacity-30"
                }`}
                title="Red Light"
              />
              <span
                className={`h-3 w-3 rounded-full transition-all ${
                  selectedCamera.current_light === "amber"
                    ? "bg-amber-400 shadow-md shadow-amber-400 scale-110"
                    : "bg-amber-950/60 opacity-30"
                }`}
                title="Amber Light"
              />
              <span
                className={`h-3 w-3 rounded-full transition-all ${
                  selectedCamera.current_light === "green"
                    ? "bg-emerald-400 shadow-md shadow-emerald-400 scale-110"
                    : "bg-emerald-950/60 opacity-30"
                }`}
                title="Green Light"
              />
            </div>
          </div>

          {/* Heartbeat Status Cards */}
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="rounded-lg border border-slate-800/80 bg-slate-900/40 p-2.5">
              <div className="flex items-center gap-1.5 text-slate-400 mb-1">
                <Activity className="h-3.5 w-3.5 text-blue-400" />
                <span className="text-[11px]">Heartbeat</span>
              </div>
              <p className="font-semibold text-slate-200">
                {formatRelativeTime(selectedCamera.last_heartbeat)}
              </p>
            </div>
            <div className="rounded-lg border border-slate-800/80 bg-slate-900/40 p-2.5">
              <div className="flex items-center gap-1.5 text-slate-400 mb-1">
                <Clock className="h-3.5 w-3.5 text-cyan-400" />
                <span className="text-[11px]">Last Event</span>
              </div>
              <p className="font-semibold text-slate-200">
                {formatRelativeTime(selectedCamera.last_event_timestamp)}
              </p>
            </div>
          </div>

          {/* Hardware Telemetry Specs */}
          <div className="space-y-2 rounded-xl border border-slate-800 bg-slate-900/60 p-3">
            {/* Battery */}
            <div>
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="flex items-center gap-1.5 text-slate-400">
                  {selectedCamera.battery_level !== null &&
                  selectedCamera.battery_level > 20 ? (
                    <Battery className="h-3.5 w-3.5 text-emerald-400" />
                  ) : (
                    <BatteryWarning className="h-3.5 w-3.5 text-rose-400" />
                  )}
                  Battery Level
                </span>
                <span className="font-mono font-semibold text-slate-200">
                  {selectedCamera.battery_level !== null &&
                  selectedCamera.battery_level !== undefined
                    ? `${selectedCamera.battery_level.toFixed(1)}%`
                    : "N/A"}
                </span>
              </div>
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
                <div
                  className={`h-full transition-all ${
                    (selectedCamera.battery_level ?? 0) > 50
                      ? "bg-emerald-500"
                      : (selectedCamera.battery_level ?? 0) > 20
                      ? "bg-amber-500"
                      : "bg-rose-500"
                  }`}
                  style={{
                    width: `${Math.min(
                      100,
                      Math.max(0, selectedCamera.battery_level ?? 0)
                    )}%`,
                  }}
                />
              </div>
            </div>

            {/* Wifi & Firmware */}
            <div className="flex items-center justify-between pt-1 border-t border-slate-800/60 text-xs">
              <div className="flex items-center gap-1.5 text-slate-400">
                <Wifi className="h-3.5 w-3.5 text-blue-400" />
                <span>Wi-Fi Signal</span>
              </div>
              <div className="flex items-center gap-1.5 font-mono text-slate-200">
                <div className="flex items-end gap-0.5 h-3">
                  {[1, 2, 3, 4].map((bar) => (
                    <div
                      key={bar}
                      className={`w-1 rounded-xs ${
                        bar <= getWifiBars(selectedCamera.wifi_signal)
                          ? "bg-blue-400"
                          : "bg-slate-700"
                      }`}
                      style={{ height: `${bar * 25}%` }}
                    />
                  ))}
                </div>
                <span>
                  {selectedCamera.wifi_signal !== null &&
                  selectedCamera.wifi_signal !== undefined
                    ? `${selectedCamera.wifi_signal} dBm`
                    : "N/A"}
                </span>
              </div>
            </div>

            {/* Firmware */}
            <div className="flex items-center justify-between pt-1 border-t border-slate-800/60 text-xs">
              <div className="flex items-center gap-1.5 text-slate-400">
                <Cpu className="h-3.5 w-3.5 text-indigo-400" />
                <span>Firmware</span>
              </div>
              <span className="font-mono text-slate-300">
                {selectedCamera.firmware_version || "v1.0.0"}
              </span>
            </div>

            {/* Location */}
            <div className="flex items-center justify-between pt-1 border-t border-slate-800/60 text-xs">
              <div className="flex items-center gap-1.5 text-slate-400">
                <Compass className="h-3.5 w-3.5 text-amber-400" />
                <span>Coordinates</span>
              </div>
              <span className="font-mono text-[11px] text-slate-300">
                {Array.isArray(selectedCamera.location)
                  ? `${selectedCamera.location[0].toFixed(3)}, ${selectedCamera.location[1].toFixed(3)}`
                  : "GPS Syncing"}
              </span>
            </div>
          </div>
        </div>
      ) : (
        /* Global Overview when no camera is actively selected */
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Layers className="h-4 w-4 text-blue-400" />
              <h4 className="font-semibold text-white text-sm">
                Traffic Fleet Overview
              </h4>
            </div>
            {isMockData ? (
              <Badge variant="warning" className="text-[10px]">
                Mock Seed Data
              </Badge>
            ) : (
              <Badge variant="success" className="text-[10px]">
                API Connected
              </Badge>
            )}
          </div>

          <p className="text-xs text-slate-400 leading-relaxed">
            Select any camera marker on the map or from the left sidebar to
            inspect real-time heartbeat telemetry, Wi-Fi RSSI diagnostics, and
            event records.
          </p>

          <div className="grid grid-cols-3 gap-2 text-center text-xs">
            <div className="rounded-lg border border-slate-800/80 bg-slate-900/60 p-2">
              <div className="text-lg font-bold text-emerald-400">
                {onlineCount}
              </div>
              <div className="text-[10px] uppercase font-semibold text-slate-400">
                Online
              </div>
            </div>
            <div className="rounded-lg border border-slate-800/80 bg-slate-900/60 p-2">
              <div className="text-lg font-bold text-amber-400">
                {maintenanceCount}
              </div>
              <div className="text-[10px] uppercase font-semibold text-slate-400">
                Service
              </div>
            </div>
            <div className="rounded-lg border border-slate-800/80 bg-slate-900/60 p-2">
              <div className="text-lg font-bold text-rose-400">
                {offlineCount}
              </div>
              <div className="text-[10px] uppercase font-semibold text-slate-400">
                Offline
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
