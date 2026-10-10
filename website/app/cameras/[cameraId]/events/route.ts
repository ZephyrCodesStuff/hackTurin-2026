import { NextRequest, NextResponse } from "next/server";
import { proxyFetch } from "@/lib/server-api";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ cameraId: string }> }
) {
  const { cameraId } = await params;
  try {
    const res = await proxyFetch(`/cameras/${cameraId}/events`);
    if (!res.ok) {
      return NextResponse.json(
        { error: `API responded with status ${res.status}` },
        { status: res.status }
      );
    }
    const data = await res.json();
    return NextResponse.json(data);
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : "Failed to fetch camera events";
    return NextResponse.json({ error: msg }, { status: 502 });
  }
}
