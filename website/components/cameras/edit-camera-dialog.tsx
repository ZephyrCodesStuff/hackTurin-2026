"use client";

import React, { useState, useEffect } from "react";
import {
  X,
  Cctv,
  Save,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Wrench,
  PowerOff,
  Compass,
} from "lucide-react";
import { Camera, CameraState } from "@/lib/types";
import { updateCamera } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface EditCameraDialogProps {
  isOpen: boolean;
  onClose: () => void;
  camera: Camera | null;
  onCameraUpdated: (camera: Camera) => void;
}

export function EditCameraDialog({
  isOpen,
  onClose,
  camera,
  onCameraUpdated,
}: EditCameraDialogProps) {
  const [name, setName] = useState("");
  const [latitude, setLatitude] = useState("");
  const [longitude, setLongitude] = useState("");
  const [state, setState] = useState<CameraState>("online");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Sync initial camera values when dialog opens or camera changes
  useEffect(() => {
    if (camera) {
      setName(camera.name || "");
      if (Array.isArray(camera.location)) {
        setLatitude(camera.location[0]?.toString() || "");
        setLongitude(camera.location[1]?.toString() || "");
      } else {
        setLatitude(camera.latitude?.toString() || "");
        setLongitude(camera.longitude?.toString() || "");
      }
      setState(camera.state || "online");
      setError(null);
    }
  }, [camera, isOpen]);

  // Handle escape key
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !camera) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError("Camera name cannot be empty");
      return;
    }

    const latNum = parseFloat(latitude.trim());
    const lonNum = parseFloat(longitude.trim());

    if (isNaN(latNum) || isNaN(lonNum)) {
      setError("Please provide valid numbers for Latitude and Longitude");
      return;
    }

    if (latNum < -90 || latNum > 90) {
      setError("Latitude must be between -90 and 90 degrees");
      return;
    }

    if (lonNum < -180 || lonNum > 180) {
      setError("Longitude must be between -180 and 180 degrees");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const { camera: updatedCamera } = await updateCamera(camera.id, {
        name: name.trim(),
        latitude: latNum,
        longitude: lonNum,
        state,
      });

      onCameraUpdated(updatedCamera);
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to update camera";
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-[#1f1915]/50 p-4 sm:p-6 backdrop-blur-xs animate-in fade-in-0 duration-200"
      onClick={onClose}
    >
      <div
        className="relative flex max-h-[90vh] w-full max-w-lg flex-col overflow-hidden rounded-2xl border border-[#e7e5e0] bg-[#faf9f5] shadow-2xl animate-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[#e7e5e0] bg-white px-5 py-3.5">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#20808d]/10 text-[#20808d] border border-[#20808d]/20">
              <Cctv className="h-4 w-4" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-[#1f1915]">
                Edit Camera Settings
              </h3>
              <p className="font-mono text-[11px] text-[#8a857c]">
                ID: {camera.id.slice(0, 8)}... ({camera.camera_type?.replace("_", " ") || "Camera"})
              </p>
            </div>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={onClose}
            disabled={isSubmitting}
            className="h-8 w-8 text-[#6b675f] hover:text-[#1f1915] rounded-md"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Scrollable Form Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {error && (
            <div className="flex items-center gap-2 rounded-lg border border-[#c25450]/30 bg-[#c25450]/10 p-3 text-xs text-[#a8423e]">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form id="edit-camera-form" onSubmit={handleSubmit} className="space-y-4">
            {/* 1. Name */}
            <div>
              <label className="mb-1 block text-xs font-semibold text-[#1f1915]">
                Camera Name / Location
              </label>
              <Input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Piazza Castello / Via Po"
                disabled={isSubmitting}
                className="h-9 text-xs bg-white border-[#e7e5e0]"
              />
            </div>

            {/* 2. Coordinates */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs font-semibold text-[#1f1915] flex items-center gap-1">
                  <Compass className="h-3.5 w-3.5 text-[#20808d]" />
                  Coordinates (Floats)
                </label>
                <span className="text-[10px] text-[#8a857c]">
                  Decimal degrees
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <span className="block text-[10px] text-[#6b675f] mb-0.5">Latitude</span>
                  <Input
                    type="number"
                    step="any"
                    value={latitude}
                    onChange={(e) => setLatitude(e.target.value)}
                    placeholder="45.0710"
                    disabled={isSubmitting}
                    className="h-9 font-mono text-xs bg-white border-[#e7e5e0]"
                  />
                </div>
                <div>
                  <span className="block text-[10px] text-[#6b675f] mb-0.5">Longitude</span>
                  <Input
                    type="number"
                    step="any"
                    value={longitude}
                    onChange={(e) => setLongitude(e.target.value)}
                    placeholder="7.6865"
                    disabled={isSubmitting}
                    className="h-9 font-mono text-xs bg-white border-[#e7e5e0]"
                  />
                </div>
              </div>
            </div>

            {/* 3. State */}
            <div>
              <label className="mb-1.5 block text-xs font-semibold text-[#1f1915]">
                Operational State
              </label>
              <div className="grid grid-cols-3 gap-2">
                {/* Online */}
                <button
                  type="button"
                  onClick={() => setState("online")}
                  className={`flex flex-col items-center justify-center p-2.5 rounded-lg border text-center transition-all cursor-pointer ${
                    state === "online"
                      ? "border-[#4f9d69] bg-[#4f9d69]/10 shadow-xs font-medium"
                      : "border-[#e7e5e0] bg-white hover:bg-[#f5f4ef]"
                  }`}
                >
                  <CheckCircle2
                    className={`h-4 w-4 mb-1 ${
                      state === "online" ? "text-[#4f9d69]" : "text-[#8a857c]"
                    }`}
                  />
                  <span className="text-[11px] capitalize text-[#1f1915]">Online</span>
                </button>

                {/* Maintenance */}
                <button
                  type="button"
                  onClick={() => setState("maintenance")}
                  className={`flex flex-col items-center justify-center p-2.5 rounded-lg border text-center transition-all cursor-pointer ${
                    state === "maintenance"
                      ? "border-[#c08a2d] bg-[#c08a2d]/10 shadow-xs font-medium"
                      : "border-[#e7e5e0] bg-white hover:bg-[#f5f4ef]"
                  }`}
                >
                  <Wrench
                    className={`h-4 w-4 mb-1 ${
                      state === "maintenance" ? "text-[#c08a2d]" : "text-[#8a857c]"
                    }`}
                  />
                  <span className="text-[11px] capitalize text-[#1f1915]">Maintenance</span>
                </button>

                {/* Offline */}
                <button
                  type="button"
                  onClick={() => setState("offline")}
                  className={`flex flex-col items-center justify-center p-2.5 rounded-lg border text-center transition-all cursor-pointer ${
                    state === "offline"
                      ? "border-[#c25450] bg-[#c25450]/10 shadow-xs font-medium"
                      : "border-[#e7e5e0] bg-white hover:bg-[#f5f4ef]"
                  }`}
                >
                  <PowerOff
                    className={`h-4 w-4 mb-1 ${
                      state === "offline" ? "text-[#c25450]" : "text-[#8a857c]"
                    }`}
                  />
                  <span className="text-[11px] capitalize text-[#1f1915]">Offline</span>
                </button>
              </div>
            </div>
          </form>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 border-t border-[#e7e5e0] bg-white px-5 py-3">
          <Button
            type="button"
            variant="ghost"
            onClick={onClose}
            disabled={isSubmitting}
            className="h-8 px-3 text-xs text-[#6b675f]"
          >
            Cancel
          </Button>
          <Button
            type="submit"
            form="edit-camera-form"
            disabled={isSubmitting}
            className="h-8 px-4 bg-[#20808d] hover:bg-[#016a71] text-white text-xs font-medium gap-1.5 shadow-xs"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="h-3 w-3 animate-spin" />
                <span>Saving...</span>
              </>
            ) : (
              <>
                <Save className="h-3 w-3" />
                <span>Save Changes</span>
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
