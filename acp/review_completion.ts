type ReviewPhase = "SUBMITTED" | "COMPLETED";

/** The same verified-delivery boundary is used before and after evaluation. */
export async function processReviewPhase(input: {
  phase: ReviewPhase;
  apiDeliverable: string | null;
  recoverDelivery: () => Promise<string>;
  verifyDelivery: (deliverable: unknown) => void;
  complete: () => Promise<void>;
}): Promise<{ phase: ReviewPhase; deliverable: unknown }> {
  const serialized = input.apiDeliverable ?? await input.recoverDelivery();
  const deliverable: unknown = JSON.parse(serialized);
  input.verifyDelivery(deliverable);
  if (input.phase === "SUBMITTED") await input.complete();
  return { phase: input.phase, deliverable };
}
