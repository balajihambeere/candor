"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { apiPost } from "./api";
import { createSessionToken, SESSION_COOKIE } from "./session";

export async function login(formData: FormData): Promise<void> {
  const username = String(formData.get("username") ?? "");
  const password = String(formData.get("password") ?? "");

  const expectedUsername = process.env.DASHBOARD_USERNAME ?? "";
  const expectedPassword = process.env.DASHBOARD_PASSWORD ?? "";

  if (!expectedUsername || username !== expectedUsername || password !== expectedPassword) {
    redirect("/login?error=Invalid+credentials");
  }

  const token = await createSessionToken(username);
  const store = await cookies();
  store.set(SESSION_COOKIE, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 12,
  });

  redirect("/review-queue");
}

export async function logout(): Promise<void> {
  const store = await cookies();
  store.delete(SESSION_COOKIE);
  redirect("/login");
}

export async function resolveReviewItem(
  itemId: string,
  decisionId: string,
  formData: FormData,
): Promise<void> {
  const assigned_to = String(formData.get("assigned_to") ?? "");
  const resolution_notes = String(formData.get("resolution_notes") ?? "");

  let errorMessage: string | null = null;
  try {
    await apiPost(`/v1/review-queue/${itemId}/resolve`, { assigned_to, resolution_notes });
  } catch (err) {
    errorMessage = (err as Error).message;
  }

  if (errorMessage) {
    redirect(`/decisions/${decisionId}?error=${encodeURIComponent(errorMessage)}`);
  }
  redirect(`/decisions/${decisionId}?message=${encodeURIComponent("Review item resolved")}`);
}

export async function discloseDecision(decisionId: string, formData: FormData): Promise<void> {
  const channel = String(formData.get("channel") ?? "");
  const disclosed_by = String(formData.get("disclosed_by") ?? "");
  const delay_owned = formData.get("delay_owned") === "on";
  const sentenceOverrideRaw = String(formData.get("sentence_override") ?? "").trim();
  const customerResponseRaw = String(formData.get("customer_response") ?? "").trim();

  let errorMessage: string | null = null;
  try {
    await apiPost(`/v1/decisions/${decisionId}/disclose`, {
      channel,
      disclosed_by,
      delay_owned,
      sentence_override: sentenceOverrideRaw || undefined,
      customer_response: customerResponseRaw || undefined,
    });
  } catch (err) {
    errorMessage = (err as Error).message;
  }

  if (errorMessage) {
    redirect(`/decisions/${decisionId}?error=${encodeURIComponent(errorMessage)}`);
  }
  redirect(`/decisions/${decisionId}?message=${encodeURIComponent("Disclosure logged")}`);
}

export async function reopenDecision(decisionId: string, formData: FormData): Promise<void> {
  const raw = String(formData.get("new_evidence_json") ?? "{}");

  let newEvidence: Record<string, unknown>;
  try {
    newEvidence = JSON.parse(raw);
  } catch {
    redirect(`/decisions/${decisionId}?error=${encodeURIComponent("Invalid JSON in new evidence")}`);
  }

  let newDecisionId: string | null = null;
  let errorMessage: string | null = null;
  try {
    const result = await apiPost<{ new_decision: { id: string } }>(
      `/v1/decisions/${decisionId}/reopen`,
      { new_evidence: newEvidence },
    );
    newDecisionId = result.new_decision.id;
  } catch (err) {
    errorMessage = (err as Error).message;
  }

  if (errorMessage || !newDecisionId) {
    redirect(`/decisions/${decisionId}?error=${encodeURIComponent(errorMessage ?? "reopen failed")}`);
  }
  redirect(`/decisions/${newDecisionId}?message=${encodeURIComponent("Reopened")}`);
}
