export type UserProfile = {
  id: string;
  displayName: string;
  avatarUrl: string | null;
};

export type UserProfileUpdate = Partial<Omit<UserProfile, "id">>;
