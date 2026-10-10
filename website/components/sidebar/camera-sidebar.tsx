"use client";

import React, { useState } from "react";
import {
  Search,
  Cctv,
  Wifi,
  RefreshCw,
  ChevronRight,
  Radio,
  LogOut,
  User,
} from "lucide-react";
import { useAuth } from "@/components/auth/login-gate";
import { Camera, CameraState } from "@/lib/types";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatRelativeTime, isSignalized } from "@/lib/utils";

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
  const { user, logout } = useAuth();
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
    <aside className="relative flex h-full w-[20%] min-w-[260px] max-w-[360px] shrink-0 flex-col border-r border-[#e7e5e0] bg-[#faf9f5] z-20 shadow-sm">
      {/* Brand / Header */}
      <div className="flex flex-col border-b border-[#e7e5e0] p-3.5 gap-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#20808d]/10 text-[#20808d] border border-[#20808d]/20">
              <Cctv className="h-4 w-4" />
            </div>
            <div>
              <h2 className="font-serif text-base font-semibold text-[#1f1915] tracking-tight">
                Traffic Grid
              </h2>
              <p className="text-[10px] text-[#8a857c]">
                Urban Surveillance Fleet
              </p>
            </div>
          </div>

          <Button
            variant="ghost"
            size="icon"
            onClick={onRefresh}
            disabled={isLoading}
            className="h-7 w-7 text-[#6b675f] hover:text-[#1f1915]"
            title="Refresh Cameras"
          >
            <RefreshCw
              className={`h-3.5 w-3.5 ${isLoading ? "animate-spin text-[#20808d]" : ""}`}
            />
          </Button>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-[#8a857c]" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search camera or ID..."
            className="h-8 pl-8 text-xs"
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
                  ? "bg-[#20808d]/10 text-[#20808d]"
                  : "text-[#6b675f] hover:text-[#1f1915] hover:bg-[#f5f4ef]"
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
          <div className="flex flex-col items-center justify-center p-6 text-center text-xs text-[#8a857c]">
            <Radio className="h-6 w-6 text-[#b8b3aa] mb-2" />
            <p className="font-semibold text-[#6b675f]">No cameras found</p>
            <p className="text-[11px] text-[#8a857c]">Try adjusting your search</p>
          </div>
        ) : (
          filteredCameras.map((camera) => {
            const isSelected = selectedCameraId === camera.id;
            const signalized = isSignalized(camera);
            return (
              <div
                key={camera.id}
                onClick={() => onSelectCamera(camera)}
                className={`group relative flex cursor-pointer flex-col rounded-xl border p-2.5 transition-all select-none ${
                  isSelected
                    ? "border-[#20808d]/50 bg-[#20808d]/8 ring-1 ring-[#20808d]/30 shadow-sm"
                    : "border-[#e7e5e0] bg-[#fdfbfa] hover:border-[#d6d3cc] hover:bg-[#f5f4ef]"
                }`}
              >
                {/* Top Row: Name */}
                <div className="flex items-center justify-between gap-1">
                  <h4
                    className={`text-xs font-semibold truncate ${
                      isSelected ? "text-[#1f1915]" : "text-[#1f1915] group-hover:text-[#1f1915]"
                    }`}
                  >
                    {camera.name}
                  </h4>
                  <ChevronRight
                    className={`h-3.5 w-3.5 shrink-0 transition-transform ${
                      isSelected
                        ? "text-[#20808d] translate-x-0.5"
                        : "text-[#b8b3aa] group-hover:text-[#6b675f]"
                    }`}
                  />
                </div>

                {/* Subtitle / Coordinates & Heartbeat */}
                <div className="mt-1 flex items-center justify-between text-[11px] text-[#6b675f]">
                  <span className="font-mono text-[10px] text-[#8a857c]">
                    {Array.isArray(camera.location)
                      ? `${camera.location[0].toFixed(3)}, ${camera.location[1].toFixed(3)}`
                      : "GPS Syncing"}
                  </span>
                  <span className="text-[10px] text-[#8a857c]">
                    {formatRelativeTime(camera.last_heartbeat)}
                  </span>
                </div>

                {/* Bottom Row Telemetry Micro-Badges */}
                <div className="mt-2 flex items-center justify-between pt-1.5 border-t border-[#e7e5e0] text-[10px] text-[#6b675f]">
                  {/* Traffic light symbol (3-lamp horizontal) */}
                  {signalized ? (
                    <div
                      className="flex items-center gap-1 rounded border border-[#e7e5e0] bg-[#f5f4ef] px-1.5 py-0.5"
                      title={
                        camera.state === "online" && camera.current_light
                          ? `Traffic Light: ${camera.current_light}`
                          : "Traffic signal syncing"
                      }
                    >
                      <span
                        className={`h-2 w-2 rounded-full transition-all ${
                          camera.state === "online" && camera.current_light === "red"
                            ? "bg-[#d1584f]"
                            : "bg-[#d1584f]/20"
                        }`}
                      />
                      <span
                        className={`h-2 w-2 rounded-full transition-all ${
                          camera.state === "online" && camera.current_light === "amber"
                            ? "bg-[#d99a2b]"
                            : "bg-[#d99a2b]/20"
                        }`}
                      />
                      <span
                        className={`h-2 w-2 rounded-full transition-all ${
                          camera.state === "online" && camera.current_light === "green"
                            ? "bg-[#4f9d69]"
                            : "bg-[#4f9d69]/20"
                        }`}
                      />
                    </div>
                  ) : (
                    <div
                      className="flex items-center rounded border border-[#e7e5e0] bg-[#f5f4ef] px-1.5 py-0.5 text-[#8a857c]"
                      title="Unsignalized crossing"
                    >
                      <Cctv className="h-3 w-3" />
                    </div>
                  )}

                  <div className="flex items-center gap-1">
                    <Wifi className="h-3 w-3 text-[#8a857c]" />
                    <span>
                      {camera.wifi_signal !== null && camera.wifi_signal !== undefined
                        ? `${camera.wifi_signal} dBm`
                        : "--"}
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5">
                    <Badge
                      variant={
                        camera.state === "online"
                          ? "success"
                          : camera.state === "maintenance"
                          ? "warning"
                          : "danger"
                      }
                      className="text-[9px] capitalize px-1.5 py-0 h-4"
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

      {/* Footer Info & User Session */}
      <div className="border-t border-[#e7e5e0] bg-[#f5f4ef] p-2.5">
        <div className="flex items-center justify-between text-xs mb-1.5">
          <div className="flex items-center gap-1.5 min-w-0">
            <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse shrink-0" />
            <span className="font-mono text-[11px] text-[#1f1915] truncate font-semibold">
              {user?.username || "authenticated"}
            </span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={logout}
            title="Sign out of operations terminal"
            className="h-6 px-2 text-[10px] text-[#6b675f] hover:text-[#c25450] hover:bg-white"
          >
            <LogOut className="h-3 w-3 mr-1" />
            Logout
          </Button>
        </div>

        <div className="text-center text-[10px] text-[#8a857c]">
          <span>{filteredCameras.length} of {cameras.length} cameras visible</span>
          {isMockData && (
            <span className="block text-[#c08a2d] font-medium mt-0.5">
              Fallback Demo Mode Active
            </span>
          )}
        </div>
      </div>
    </aside>
  );
}
