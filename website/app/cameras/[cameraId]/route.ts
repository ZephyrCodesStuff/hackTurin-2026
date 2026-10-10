import { NextRequest, NextResponse } from "next/server";
import { proxyFetch } from "@/lib/server-api";

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ cameraId: string }> }
) {
  const token = request.cookies.get("auth_token")?.value;
  const authHeader = request.headers.get("authorization");
  if (!token && !authHeader) {
    return NextResponse.json(
      { error: "Authentication required to edit camera" },
      { status: 401 }
    );
  }

  const { cameraId } = await params;
  let body: string;
  try {
    body = await request.text();
  } catch {
    body = "{}";
  }

  const headers: Record<string, string> = {
    "content-type": "application/json",
  };
  if (token) {
    headers["cookie"] = `auth_token=${token}`;
    headers["authorization"] = `Bearer ${token}`;
  }
  if (authHeader) {
    headers["authorization"] = authHeader;
  }

  try {
    const res = await proxyFetch(`/cameras/${cameraId}`, {
      method: "PATCH",
      headers,
      body,
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : "Failed to update camera";
    return NextResponse.json({ error: msg }, { status: 502 });
  }
}
