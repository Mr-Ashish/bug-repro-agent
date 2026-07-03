import { defineConfig, devices } from "@playwright/test";
import "dotenv/config";

export default defineConfig({
  testDir: "./reproductions",
  testMatch: "**/repro.spec.ts",

  timeout: 60_000,
  expect: { timeout: 10_000 },

  fullyParallel: false,
  retries: 0,
  workers: 1,

  reporter: [
    ["list"],
    ["html", { outputFolder: "test-results/report", open: "never" }],
  ],

  outputDir: "test-results/artifacts",

  use: {
    baseURL: process.env.PLANE_URL || "http://localhost:3000",
    video: "on",
    screenshot: "on",
    trace: "on",
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
    ...devices["Desktop Chrome"],
  },

  projects: [
    {
      name: "repro-replay",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});