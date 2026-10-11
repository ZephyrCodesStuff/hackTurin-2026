"use client";

import React, { useState, useEffect } from "react";
import {
  X,
  Siren,
  ShieldAlert,
  Loader2,
  AlertTriangle,
  Clock,
} from "lucide-react";
import { toast } from "sonner";
import {
  CrashEvent,
  EmergencyUnit,
  EMERGENCY_UNIT_CONFIG,
} from "@/lib/types";
import { dispatchEmsUnits } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { formatDateTime, formatRelativeTime } from "@/lib/utils";

interface DispatchEmsDialogProps {
  isOpen: boolean;
  onClose: () => void;
  crashEvent: CrashEvent | null;
  cameraName: string;
  onDispatched: (updatedCrash: CrashEvent) => void;
}

export function DispatchEmsDialog({
  isOpen,
  onClose,
  crashEvent,
  cameraName,
  onDispatched,
}: DispatchEmsDialogProps) {
  // Preselect 118 (Emergenza Sanitaria) and Polizia Locale by default
  const [selectedUnits, setSelectedUnits] = useState<EmergencyUnit[]>([
    EmergencyUnit.EMERGENZA_SANITARIA,
    EmergencyUnit.POLIZIA_LOCALE,
  ]);
  const [confirmationInput, setConfirmationInput] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset inputs when opened
  useEffect(() => {
    if (isOpen) {
      setSelectedUnits([
        EmergencyUnit.EMERGENZA_SANITARIA,
        EmergencyUnit.POLIZIA_LOCALE,
      ]);
      setConfirmationInput("");
      setError(null);
    }
  }, [isOpen]);

  // Handle escape key
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !crashEvent) return null;

  const isConfirmed = confirmationInput.trim().toUpperCase() === "CONFIRM";
  const canSubmit = isConfirmed && selectedUnits.length > 0 && !isSubmitting;

  const handleToggleUnit = (unit: EmergencyUnit) => {
    setSelectedUnits((prev) =>
      prev.includes(unit) ? prev.filter((u) => u !== unit) : [...prev, unit]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;

    setIsSubmitting(true);
    setError(null);

    try {
      const identifier = crashEvent.id || crashEvent.photo_id;
      const { crash } = await dispatchEmsUnits(identifier, selectedUnits);

      toast.success("Emergency Units Dispatched", {
        description: `Dispatched ${selectedUnits.length} unit(s) to ${cameraName}. Incident is now marked in progress.`,
        duration: 5000,
      });

      onDispatched(crash);
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to dispatch units";
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const allUnits = [
    EmergencyUnit.EMERGENZA_SANITARIA,
    EmergencyUnit.POLIZIA_LOCALE,
    EmergencyUnit.VIGILI_DEL_FUOCO,
    EmergencyUnit.CARABINIERI,
    EmergencyUnit.POLIZIA_DI_STATO,
    EmergencyUnit.SOCCORSO_STRADALE,
    EmergencyUnit.PROTEZIONE_CIVILE,
  ];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-[#1f1915]/50 p-4 sm:p-6 backdrop-blur-xs animate-in fade-in-0 duration-200"
      onClick={onClose}
    >
      <div
        className="relative flex max-h-[92vh] w-full max-w-lg flex-col overflow-hidden rounded-2xl border border-[#e7e5e0] bg-[#faf9f5] shadow-2xl animate-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[#e7e5e0] bg-white px-5 py-3.5">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#c25450]/15 text-[#c25450] border border-[#c25450]/30">
              <Siren className="h-4 w-4 animate-pulse" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-[#1f1915] flex items-center gap-2">
                Authorize Emergency Dispatch
                <Badge variant="outline" className="text-[10px] bg-red-50 text-red-700 border-red-200">
                  Torino 112 / EMS
                </Badge>
              </h3>
              <p className="text-xs text-[#8a857c]">
                {cameraName} • Incident logged {formatRelativeTime(crashEvent.timestamp)}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-[#8a857c] hover:bg-[#e7e5e0]/60 hover:text-[#1f1915] transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="flex flex-1 flex-col overflow-y-auto">
          <div className="space-y-4 p-5">
            {/* Incident Summary Card */}
            <div className="rounded-xl border border-[#c25450]/20 bg-[#fdf5f5] p-3 text-xs text-[#1f1915]">
              <div className="flex items-start justify-between">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-1.5 font-semibold text-[#a8423e]">
                    <ShieldAlert className="h-3.5 w-3.5" />
                    Crash Incident Confirmed
                  </div>
                  <p className="text-[11px] text-[#6b675f]">
                    Location: <span className="font-medium text-[#1f1915]">{cameraName}</span>
                  </p>
                </div>
                <span className="font-mono text-[11px] text-[#8a857c] flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  {formatDateTime(crashEvent.timestamp)}
                </span>
              </div>
            </div>

            {/* Emergency Units Checklist */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-[#1f1915]">
                  Select Response Units to Dispatch ({selectedUnits.length} selected):
                </label>
                <div className="flex gap-2 text-[11px]">
                  <button
                    type="button"
                    onClick={() => setSelectedUnits(allUnits)}
                    className="text-[#20808d] hover:underline"
                  >
                    Select All
                  </button>
                  <span className="text-stone-300">|</span>
                  <button
                    type="button"
                    onClick={() => setSelectedUnits([])}
                    className="text-[#6b675f] hover:underline"
                  >
                    Clear
                  </button>
                </div>
              </div>

              <div className="max-h-56 space-y-1.5 overflow-y-auto rounded-xl border border-[#e7e5e0] bg-white p-2">
                {allUnits.map((unit) => {
                  const info = EMERGENCY_UNIT_CONFIG[unit];
                  const isChecked = selectedUnits.includes(unit);
                  return (
                    <label
                      key={unit}
                      className={`flex cursor-pointer items-start gap-2.5 rounded-lg border p-2 transition-colors ${
                        isChecked
                          ? "border-[#20808d]/40 bg-[#20808d]/5"
                          : "border-transparent bg-transparent hover:bg-stone-50"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => handleToggleUnit(unit)}
                        className="mt-0.5 h-4 w-4 rounded border-[#d4d1ca] text-[#20808d] focus:ring-[#20808d]"
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1.5">
                          <span className="rounded bg-stone-100 px-1.5 py-0.2 text-[10px] font-mono font-bold text-stone-700">
                            {info.code}
                          </span>
                          <span className="text-xs font-semibold text-[#1f1915]">
                            {info.name}
                          </span>
                        </div>
                        <p className="text-[11px] text-[#6b675f] mt-0.5 leading-snug">
                          {info.description}
                        </p>
                      </div>
                    </label>
                  );
                })}
              </div>
            </div>

            {/* Authorization Confirmation Field */}
            <div className="space-y-1.5 rounded-xl border border-[#e7e5e0] bg-[#f5f4ef] p-3.5">
              <label
                htmlFor="confirm-dispatch-input"
                className="text-xs font-semibold text-[#1f1915] flex items-center justify-between"
              >
                <span>Authorization Safeguard</span>
                <span className="text-[11px] font-normal text-[#8a857c]">
                  Type <strong className="font-mono text-[#c25450]">CONFIRM</strong> to unlock
                </span>
              </label>
              <Input
                id="confirm-dispatch-input"
                type="text"
                placeholder="Type CONFIRM"
                value={confirmationInput}
                onChange={(e) => setConfirmationInput(e.target.value)}
                autoComplete="off"
                className="font-mono tracking-wider bg-white"
              />
              <p className="text-[10px] text-[#8a857c]">
                Dispatching emergency response alerts city dispatcher systems and records this incident as In Progress.
              </p>
            </div>

            {/* Error Message */}
            {error && (
              <div className="flex items-center gap-2 rounded-lg bg-red-50 p-2.5 text-xs text-red-700 border border-red-200">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between border-t border-[#e7e5e0] bg-white px-5 py-3">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancel
            </Button>

            <Button
              type="submit"
              size="sm"
              disabled={!canSubmit}
              className={`gap-1.5 transition-all ${
                canSubmit
                  ? "bg-[#c25450] hover:bg-[#a8423e] text-white shadow-sm"
                  : "bg-stone-200 text-stone-400 cursor-not-allowed"
              }`}
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  Dispatching...
                </>
              ) : (
                <>
                  <Siren className="h-3.5 w-3.5" />
                  Authorize Dispatch ({selectedUnits.length})
                </>
              )}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
