import { describe, expect, it, beforeEach } from "vitest";

import { clearAccessToken, getAccessToken, saveAccessToken } from "../features/auth/authStorage";

describe("authStorage", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it("stores and reads token", () => {
    saveAccessToken("jwt-test");
    expect(getAccessToken()).toBe("jwt-test");
  });

  it("clears token", () => {
    saveAccessToken("jwt-test");
    clearAccessToken();
    expect(getAccessToken()).toBeNull();
  });
});
