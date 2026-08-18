import { afterEach, expect, it, vi } from "vitest";

afterEach(() => vi.unstubAllEnvs());

async function loadConfig(ci: string) {
  vi.stubEnv("CI", ci);
  vi.resetModules();
  return (await import("../../playwright.config")).default;
}

it("reuses a local server but starts an isolated server in CI", async () => {
  const localConfig = await loadConfig("");
  expect(localConfig.webServer).toMatchObject({ reuseExistingServer: true });

  const ciConfig = await loadConfig("true");
  expect(ciConfig.webServer).toMatchObject({ reuseExistingServer: false });
});
