import { NextRequest, NextResponse } from "next/server";
import { proxyFetch } from "@/lib/server-api";

export async function GET(req: NextRequest) {
  const token = req.cookies.get("auth_token")?.value;
  const authHeader = req.headers.get("authorization");
  if (!token && !authHeader) {
    return NextResponse.json(
      { error: "Authentication required to access cameras" },
      { status: 401 }
    );
  }

  try {
    const res = await proxyFetch("/cameras");
    if (!res.ok) {
      return NextResponse.json(
        { error: `API responded with status ${res.status}` },
        { status: res.status }
      );
    }
    const data = await res.json();
    return NextResponse.json(data);
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : "Failed to fetch cameras";
    return NextResponse.json({ error: msg }, { status: 502 });
  }
}
