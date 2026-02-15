import { NextResponse } from "next/server";

type NotifyLeadBody = {
  runId?: string;
  email?: string;
  company?: string;
};

const TARGET_EMAIL = "hirsch.hans92@gmail.com";

export async function POST(req: Request) {
  try {
    const { runId, email, company }: NotifyLeadBody = await req.json();

    if (!runId || !email) {
      return NextResponse.json({ ok: false, message: "runId und email sind erforderlich." }, { status: 400 });
    }

    const apiKey = process.env.RESEND_API_KEY;
    if (!apiKey) {
      console.info("[notify-lead] disabled: RESEND_API_KEY missing", {
        runId,
        email,
        company,
      });
      return NextResponse.json({ ok: true, disabled: true });
    }

    const timestamp = new Date().toISOString();
    const text = [
      "Neuer zVT Navigator Lead",
      `run_id: ${runId}`,
      `email: ${email}`,
      `company: ${company || "-"}`,
      `timestamp: ${timestamp}`,
    ].join("\n");

    const resendRes = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        from: process.env.RESEND_FROM_EMAIL ?? "zVT Navigator <onboarding@resend.dev>",
        to: [TARGET_EMAIL],
        subject: "Neuer zVT Navigator Lead",
        text,
      }),
    });

    if (!resendRes.ok) {
      const detail = await resendRes.text();
      console.error("[notify-lead] resend failed", { status: resendRes.status, detail, runId });
      return NextResponse.json({ ok: true, warning: "notify_failed" });
    }

    return NextResponse.json({ ok: true });
  } catch (error) {
    console.error("[notify-lead] unexpected error", error);
    return NextResponse.json({ ok: true, warning: "notify_exception" });
  }
}
