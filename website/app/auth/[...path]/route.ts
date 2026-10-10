import { NextRequest, NextResponse } from "next/server";
import { proxyFetch } from "@/lib/server-api";

async function handleProxy(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;
  const subPath = "/" + path.join("/");
  const targetPath = `/auth${subPath}`;

  const headers: Record<string, string> = {};
  req.headers.forEach((value, key) => {
    if (key.toLowerCase() !== "host") {
      headers[key] = value;
    }
  });

  const cookie = req.headers.get("cookie");
  if (cookie) {
    headers["cookie"] = cookie;
  }

  const authHeader = req.headers.get("authorization");
  if (authHeader) {
    headers["authorization"] = authHeader;
  }

  let body: string | undefined = undefined;
  if (req.method !== "GET" && req.method !== "HEAD") {
    try {
      body = await req.text();
    } catch {
      // no body
    }
  }

  try {
    const apiRes = await proxyFetch(targetPath, {
      method: req.method,
      headers: {
        ...headers,
        "content-type": req.headers.get("content-type") || "application/json",
      },
      body,
    });

    const responseData = await apiRes.text();
    const res = new NextResponse(responseData, {
      status: apiRes.status,
      headers: {
        "content-type": apiRes.headers.get("content-type") || "application/json",
      },
    });

    // Forward Set-Cookie if returned by API
    const setCookie = apiRes.headers.get("set-cookie");
    if (setCookie) {
      res.headers.set("set-cookie", setCookie);
    }

    return res;
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : "Proxy error";
    return NextResponse.json({ detail: msg }, { status: 502 });
  }
}

export async function GET(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  return handleProxy(req, ctx);
}

export async function POST(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  return handleProxy(req, ctx);
}
