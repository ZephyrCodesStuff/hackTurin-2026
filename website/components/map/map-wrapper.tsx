"use client";

import dynamic from "next/dynamic";
import { Loader2 } from "lucide-react";
import { Camera } from "@/lib/types";

const CameraMap = dynamic(() => import("./camera-map"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center bg-[#faf9f5] text-[#6b675f]">
      <div className="flex flex-col items-center gap-2">
        <Loader2 className="h-8 w-8 animate-spin text-[#20808d]" />
        <span className="text-sm font-medium">Initializing OpenStreetMap...</span>
      </div>
    </div>
  ),
});

interface MapWrapperProps {
  cameras: Camera[];
  selectedCameraId: string | null;
  onSelectCamera: (camera: Camera) => void;
}

export function MapWrapper(props: MapWrapperProps) {
  return <CameraMap {...props} />;
}
