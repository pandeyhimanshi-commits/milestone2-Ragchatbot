import { NextResponse } from "next/server";

const BACKEND_CHAT_URL = process.env.BACKEND_CHAT_URL || "http://127.0.0.1:8080/chat";

export async function POST(request: Request) {
  try {
    const payload = await request.json();
    const upstream = await fetch(BACKEND_CHAT_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      cache: "no-store",
    });

    const text = await upstream.text();
    return new NextResponse(text, {
      status: upstream.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch (err) {
    return NextResponse.json(
      { error: `Failed to call backend chat API: ${String(err)}` },
      { status: 500 },
    );
  }
}
