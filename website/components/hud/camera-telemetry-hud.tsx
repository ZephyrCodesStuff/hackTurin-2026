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
} from "lucide-react";
import { Cctv } from "lucide-react";
import { Camera } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatRelativeTime, isSignalized } from "@/lib/utils";

interface CameraTelemetryHudProps {
  selectedCamera: Camera | null;
  allCameras: Camera[];
  isMockData: boolean;
}

export function CameraTelemetryHud({
  selectedCamera,
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

  // The HUD only appears when a camera is selected; there is no idle overview panel.
  if (!selectedCamera) return null;

  return (
    <div className="absolute top-4 right-4 z-20 w-80 sm:w-88 rounded-2xl border border-[#e7e5e0] bg-white/95 p-4 shadow-[0_1px_2px_rgba(0,0,0,0.06)] backdrop-blur-sm transition-all">
      {/* Selected Camera HUD View */}
      <div className="space-y-3.5">
          {/* Header */}
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span
                  className={`flex h-2 w-2 rounded-full ${
                    selectedCamera.state === "online"
                      ? "bg-[#4f9d69]"
                      : selectedCamera.state === "maintenance"
                      ? "bg-[#c08a2d]"
                      : "bg-[#c25450]"
                  }`}
                />
                <h4 className="text-xs font-semibold text-[#6b675f]">
                  Telemetry monitor
                </h4>
              </div>
              <h3 className="font-semibold text-[#1f1915] text-sm sm:text-base leading-tight">
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
              className="capitalize text-[11px] font-semibold"
            >
              {selectedCamera.state}
            </Badge>
          </div>

          {/* UUID Copy Bar */}
          <div className="flex items-center justify-between rounded-lg border border-[#e7e5e0] bg-[#f5f4ef] px-2.5 py-1.5 text-xs text-[#6b675f]">
            <span className="font-mono text-[11px] text-[#1f1915] truncate max-w-[210px]">
              {selectedCamera.id}
            </span>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 text-[#6b675f] hover:text-[#1f1915]"
              onClick={() => handleCopyId(selectedCamera.id)}
              title="Copy UUID"
            >
              {copied ? (
                <Check className="h-3.5 w-3.5 text-[#4f9d69]" />
              ) : (
                <Copy className="h-3.5 w-3.5" />
              )}
            </Button>
          </div>

          {/* Active Traffic Signal HUD (signalized cameras only). */}
          {isSignalized(selectedCamera) ? (
            <div className="flex items-center justify-between rounded-xl border border-[#e7e5e0] bg-[#fdfbfa] p-3">
              <div className="space-y-0.5">
                <span className="text-[10px] font-semibold text-[#6b675f]">
                  Active traffic signal
                </span>
                <div className="flex items-center gap-2">
                  <span
                    className={`text-sm font-semibold capitalize ${
                      selectedCamera.current_light === "green"
                        ? "text-[#4f9d69]"
                        : selectedCamera.current_light === "amber"
                        ? "text-[#c08a2d]"
                        : selectedCamera.current_light === "red"
                        ? "text-[#c25450]"
                        : "text-[#6b675f]"
                    }`}
                  >
                    {selectedCamera.current_light || "Syncing"}
                  </span>
                  {selectedCamera.current_light_timestamp && (
                    <span className="text-[10px] text-[#8a857c]">
                      ({formatRelativeTime(selectedCamera.current_light_timestamp)})
                    </span>
                  )}
                </div>
              </div>

              {/* 3-Lamp Illuminated Signal Head */}
              <div className="flex items-center gap-1.5 rounded-lg border border-[#e7e5e0] bg-[#f5f4ef] px-2.5 py-1.5">
                <span
                  className={`h-3 w-3 rounded-full transition-all ${
                    selectedCamera.current_light === "red"
                      ? "bg-[#d1584f] scale-110"
                      : "bg-[#d1584f]/20"
                  }`}
                  title="Red Light"
                />
                <span
                  className={`h-3 w-3 rounded-full transition-all ${
                    selectedCamera.current_light === "amber"
                      ? "bg-[#d99a2b] scale-110"
                      : "bg-[#d99a2b]/20"
                  }`}
                  title="Amber Light"
                />
                <span
                  className={`h-3 w-3 rounded-full transition-all ${
                    selectedCamera.current_light === "green"
                      ? "bg-[#4f9d69] scale-110"
                      : "bg-[#4f9d69]/20"
                  }`}
                  title="Green Light"
                />
              </div>
            </div>
          ) : (
            /* Neutral panel for unsignalized-crossing cameras. */
            <div className="flex items-center justify-between rounded-xl border border-[#e7e5e0] bg-[#fdfbfa] p-3">
              <div className="space-y-0.5">
                <span className="text-[10px] font-semibold text-[#6b675f]">
                  Monitoring mode
                </span>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-[#6b675f]">
                    Unsignalized crossing
                  </span>
                </div>
                <span className="text-[10px] text-[#8a857c]">
                  No traffic signal at this location
                </span>
              </div>
              <div className="flex items-center justify-center rounded-lg border border-[#e7e5e0] bg-[#f5f4ef] px-2.5 py-1.5 text-[#8a857c]">
                <Cctv className="h-5 w-5" />
              </div>
            </div>
          )}

          {/* Heartbeat Status Cards */}
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="rounded-lg border border-[#e7e5e0] bg-[#fdfbfa] p-2.5">
              <div className="flex items-center gap-1.5 text-[#6b675f] mb-1">
                <Activity className="h-3.5 w-3.5 text-[#20808d]" />
                <span className="text-[11px]">Heartbeat</span>
              </div>
              <p className="font-semibold text-[#1f1915]">
                {formatRelativeTime(selectedCamera.last_heartbeat)}
              </p>
            </div>
            <div className="rounded-lg border border-[#e7e5e0] bg-[#fdfbfa] p-2.5">
              <div className="flex items-center gap-1.5 text-[#6b675f] mb-1">
                <Clock className="h-3.5 w-3.5 text-[#20808d]" />
                <span className="text-[11px]">Last event</span>
              </div>
              <p className="font-semibold text-[#1f1915]">
                {formatRelativeTime(selectedCamera.last_event_timestamp)}
              </p>
            </div>
          </div>

          {/* Hardware Telemetry Specs */}
          <div className="space-y-2 rounded-xl border border-[#e7e5e0] bg-[#fdfbfa] p-3">
            {/* Battery */}
            <div>
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="flex items-center gap-1.5 text-[#6b675f]">
                  {selectedCamera.battery_level !== null &&
                  selectedCamera.battery_level > 20 ? (
                    <Battery className="h-3.5 w-3.5 text-[#4f9d69]" />
                  ) : (
                    <BatteryWarning className="h-3.5 w-3.5 text-[#c25450]" />
                  )}
                  Battery level
                </span>
                <span className="font-mono font-semibold text-[#1f1915]">
                  {selectedCamera.battery_level !== null &&
                  selectedCamera.battery_level !== undefined
                    ? `${selectedCamera.battery_level.toFixed(1)}%`
                    : "N/A"}
                </span>
              </div>
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-[#e7e5e0]">
                <div
                  className={`h-full transition-all ${
                    (selectedCamera.battery_level ?? 0) > 50
                      ? "bg-[#4f9d69]"
                      : (selectedCamera.battery_level ?? 0) > 20
                      ? "bg-[#c08a2d]"
                      : "bg-[#c25450]"
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
            <div className="flex items-center justify-between pt-1 border-t border-[#e7e5e0] text-xs">
              <div className="flex items-center gap-1.5 text-[#6b675f]">
                <Wifi className="h-3.5 w-3.5 text-[#20808d]" />
                <span>Wi-Fi signal</span>
              </div>
              <div className="flex items-center gap-1.5 font-mono text-[#1f1915]">
                <div className="flex items-end gap-0.5 h-3">
                  {[1, 2, 3, 4].map((bar) => (
                    <div
                      key={bar}
                      className={`w-1 rounded-xs ${
                        bar <= getWifiBars(selectedCamera.wifi_signal)
                          ? "bg-[#20808d]"
                          : "bg-[#e7e5e0]"
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
            <div className="flex items-center justify-between pt-1 border-t border-[#e7e5e0] text-xs">
              <div className="flex items-center gap-1.5 text-[#6b675f]">
                <Cpu className="h-3.5 w-3.5 text-[#20808d]" />
                <span>Firmware</span>
              </div>
              <span className="font-mono text-[#1f1915]">
                {selectedCamera.firmware_version || "v1.0.0"}
              </span>
            </div>

            {/* Location */}
            <div className="flex items-center justify-between pt-1 border-t border-[#e7e5e0] text-xs">
              <div className="flex items-center gap-1.5 text-[#6b675f]">
                <Compass className="h-3.5 w-3.5 text-[#20808d]" />
                <span>Coordinates</span>
              </div>
              <span className="font-mono text-[11px] text-[#1f1915]">
                {Array.isArray(selectedCamera.location)
                  ? `${selectedCamera.location[0].toFixed(3)}, ${selectedCamera.location[1].toFixed(3)}`
                  : "GPS Syncing"}
              </span>
            </div>
          </div>
      </div>
    </div>
  );
}
