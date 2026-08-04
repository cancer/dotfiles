import { describe, expect, it } from "vitest";
import { grantSeats, label } from "./quota";

describe("grantSeats", () => {
  it("rejects a request for zero seats", () => {
    expect(grantSeats("u-1", 0, 50)).toBeNull();
  });

  it("rejects a request for a negative number of seats", () => {
    expect(grantSeats("u-1", -1, 50)).toBeNull();
  });

  it("rejects a request above the limit", () => {
    expect(grantSeats("u-1", 51, 50)).toBeNull();
  });

  it("rejects a request far above the limit", () => {
    expect(grantSeats("u-1", 500, 50)).toBeNull();
  });

  it("grants seats at the limit", () => {
    expect(grantSeats("u-1", 50, 50)).toEqual({ userId: "u-1", seats: 50 });
  });
});

describe("label", () => {
  it("returns the trial label for the trial plan", () => {
    const displayed = label("trial");
    expect(displayed).toBe("Trial plan");
    expect(displayed.startsWith("Trial")).toBe(true);
  });

  it("returns the paid label for the paid plan", () => {
    const displayed = label("paid");
    expect(displayed).toBe("Paid plan");
    expect(displayed.startsWith("Paid")).toBe(true);
  });
});
