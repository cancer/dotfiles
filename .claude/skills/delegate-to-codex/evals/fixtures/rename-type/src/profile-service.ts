import type { UserProfile, UserProfileUpdate } from "./types.js";

export class ProfileService {
  private cache = new Map<string, UserProfile>();

  get(id: string): UserProfile | undefined {
    return this.cache.get(id);
  }

  update(id: string, patch: UserProfileUpdate): UserProfile {
    const current = this.cache.get(id);
    if (!current) throw new Error("no such profile: " + id);
    const next: UserProfile = { ...current, ...patch };
    this.cache.set(id, next);
    return next;
  }
}
