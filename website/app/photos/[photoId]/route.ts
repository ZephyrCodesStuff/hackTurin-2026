import { NextRequest, NextResponse } from "next/server";
import { proxyFetch } from "@/lib/server-api";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ photoId: string }> }
) {
  const { photoId } = await params;
  try {
    const res = await proxyFetch(`/photos/${photoId}`);
    if (!res.ok) {
      return new NextResponse(null, { status: res.status });
    }
    const contentType = res.headers.get("content-type") || "image/png";
    const buffer = await res.arrayBuffer();
    return new NextResponse(buffer, {
      status: 200,
      headers: {
        "Content-Type": contentType,
        "Cache-Control": "public, max-age=86400",
      },
    });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : "Failed to fetch photo";
    return NextResponse.json({ error: msg }, { status: 502 });
  }
}
