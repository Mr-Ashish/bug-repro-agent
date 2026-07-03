# Bug Reproduction Agent — Design Principle

> **Full architecture:** [HLD.md](./HLD.md)

## Core Insight

Split every reproduction into **"agent-authored" vs "deterministic-runtime."**

- **Phase 1 (Author):** Claude Code reasons about the bug, drives the browser via browser-use (Python agent on Playwright), and compiles everything into deterministic artifacts. Expensive, once per bug.
- **Phase 2 (Replay):** The emitted Playwright script runs without the agent. `npx playwright test`. Cheap, N times.

Reproduce once with intelligence, replay forever with determinism.
