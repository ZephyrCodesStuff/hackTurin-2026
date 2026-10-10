"use client";

import React, { useState, useEffect } from "react";
import { X, Download, AlertTriangle, ExternalLink, Loader2, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { getPhotoUrl } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";

interface CrashPhotoModalProps {
  isOpen: boolean;
  onClose: () => void;
  photoId: string;
  timestamp: number;
  cameraName: string;
}

export function CrashPhotoModal({
  isOpen,
  onClose,
  photoId,
  timestamp,
  cameraName,
}: CrashPhotoModalProps) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [fileSize, setFileSize] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const rawPhotoUrl = getPhotoUrl(photoId);

  useEffect(() => {
    if (!isOpen || !photoId) return;

    let isMounted = true;
    let createdUrl: string | null = null;

    async function loadPhoto() {
      try {
        const response = await fetch(rawPhotoUrl);
        if (!response.ok) {
          throw new Error(`API returned HTTP ${response.status}`);
        }

        const blob = await response.blob();
        if (!isMounted) return;

        setFileSize(blob.size);
        // Force valid image MIME type so browser image decoder handles octet-stream seamlessly
        const safeBlob = new Blob([blob], {
          type: blob.type.startsWith("image/") ? blob.type : "image/png",
        });

        createdUrl = URL.createObjectURL(safeBlob);
        setBlobUrl(createdUrl);
      } catch (err: unknown) {
        if (!isMounted) return;
        const msg = err instanceof Error ? err.message : "Failed to load image";
        setError(msg);
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }

    loadPhoto();

    return () => {
      isMounted = false;
      if (createdUrl) {
        URL.revokeObjectURL(createdUrl);
      }
    };
  }, [isOpen, photoId, rawPhotoUrl]);

  if (!isOpen) return null;

  const isSmallSeedImage = fileSize !== null && fileSize < 500;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm animate-in fade-in-0 duration-200"
      onClick={onClose}
    >
      <div
        className="relative flex max-h-[90vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl border border-rose-500/30 bg-slate-950 shadow-2xl shadow-rose-950/40"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 bg-slate-900/80 px-5 py-3">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-rose-500/20 text-rose-400">
              <AlertTriangle className="h-4 w-4" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">
                Incident Photo Snapshot
              </h3>
              <p className="text-xs text-slate-400">
                {cameraName} • Captured at {formatDateTime(timestamp)}
              </p>
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="h-8 w-8 text-slate-400 hover:text-white"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Image Display Area */}
        <div className="relative flex min-h-[340px] max-h-[65vh] items-center justify-center bg-slate-900/40 p-6 overflow-hidden">
          {isLoading ? (
            <div className="flex flex-col items-center gap-2 text-sm text-slate-400">
              <Loader2 className="h-8 w-8 animate-spin text-rose-500" />
              <span>Fetching photo bytes from API...</span>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center text-center p-6 text-sm text-slate-400">
              <AlertTriangle className="h-8 w-8 text-amber-500 mb-2" />
              <p className="font-semibold text-slate-300">Photo Unavailable</p>
              <p className="text-xs text-slate-500 mt-1">{error}</p>
              <p className="text-[11px] font-mono text-slate-600 mt-2">
                URL: {rawPhotoUrl}
              </p>
            </div>
          ) : blobUrl ? (
            <div className="flex flex-col items-center gap-3">
              {isSmallSeedImage ? (
                /* Scaled preview card for demo seed images */
                <div className="flex flex-col items-center rounded-xl border border-slate-800 bg-slate-900/90 p-6 text-center shadow-lg">
                  <div className="flex h-24 w-24 items-center justify-center rounded-lg border border-slate-700 bg-slate-800/80 p-2 shadow-inner">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={blobUrl}
                      alt="Crash incident capture"
                      className="h-16 w-16 object-contain image-rendering-pixelated"
                      style={{ imageRendering: "pixelated" }}
                    />
                  </div>
                  <div className="mt-3 flex items-center gap-1.5 text-xs text-emerald-400 font-medium">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    <span>Raw Photo Loaded from API</span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Payload: {fileSize} bytes (Standard demo frame snapshot)
                  </p>
                </div>
              ) : (
                /* Full resolution capture */
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={blobUrl}
                  alt="Crash incident capture"
                  className="max-h-[58vh] w-auto max-w-full rounded-lg object-contain shadow-md"
                />
              )}
            </div>
          ) : null}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-slate-800 bg-slate-900/60 px-5 py-3 text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[11px] text-slate-500 truncate max-w-[240px]">
              UUID: {photoId}
            </span>
            {fileSize !== null && (
              <span className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-[10px] text-slate-400">
                {fileSize < 1024
                  ? `${fileSize} B`
                  : `${(fileSize / 1024).toFixed(1)} KB`}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <a
              href={rawPhotoUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-200 transition-colors hover:bg-slate-700"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              Open Original
            </a>
            {blobUrl && (
              <a
                href={blobUrl}
                download={`crash-${photoId}.png`}
                className="inline-flex items-center gap-1.5 rounded-md bg-blue-600 px-3 py-1.5 text-xs text-white transition-colors hover:bg-blue-500"
              >
                <Download className="h-3.5 w-3.5" />
                Download
              </a>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
