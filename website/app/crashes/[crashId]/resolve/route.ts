import { NextRequest, NextResponse } from "next/server";
import { proxyFetch } from "@/lib/server-api";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ crashId: string }> }
) {
  const token = request.cookies.get("auth_token")?.value;
  const authHeader = request.headers.get("authorization");

  const { crashId } = await params;
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
    const res = await proxyFetch(`/crashes/${crashId}/resolve`, {
      method: "POST",
      headers,
      body,
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : "Failed to resolve crash event";
    return NextResponse.json({ error: msg }, { status: 502 });
  }
}
