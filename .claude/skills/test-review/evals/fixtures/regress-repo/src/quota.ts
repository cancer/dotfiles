export type Grant = { userId: string; seats: number };

// 仕様: 上限を超える申請、および席数が 0 以下の申請は拒否し、拒否は null で表す
// （呼び出し側は null を「拒否」として扱い、理由は別の監査ログから引く）。
export function grantSeats(userId: string, seats: number, limit: number): Grant | null {
  if (seats <= 0) return null;
  if (seats > limit) return null;
  return { userId, seats };
}

export function label(kind: "trial" | "paid"): string {
  return kind === "trial" ? "Trial plan" : "Paid plan";
}
