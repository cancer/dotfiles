import type { UserProfile } from "./types.js";

export function renderProfile(profile: UserProfile): string {
  return profile.displayName + " (" + profile.id + ")";
}
