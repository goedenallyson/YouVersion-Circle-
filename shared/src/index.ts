// Framework-agnostic YouVersion Circle API contract, shared by the web app and
// the mobile app so behavior + response shapes never drift. No React/DOM/native deps.
export * from "./types";
export { seed } from "./seed";
export { createMockApi, todayIso, addDaysIso, APPROVED_EMOJI, SIGNAL_TAXONOMY, engagementPairForDay, EMOTION_WORDS } from "./mock";
export type { EngagementPair } from "./mock";
export { createLiveApi, backendHealthy } from "./live";
