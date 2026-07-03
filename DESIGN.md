# Bug Reproduction Agent — Design Principles

> **Full architecture:** [HLD.md](./HLD.md)

## 1. The issue IS the plan

Don't hardcode reproduction steps. Fetch the issue body, inject it into a generic prompt, let the LLM figure out the steps. Works on any bug, not just pre-selected ones.

## 2. Structured verdict, not keyword matching

The agent ends with `VERDICT: REPRODUCED | <summary>`. Parse that line with a regex. Don't write per-issue keyword matchers — they break on every new bug.

## 3. One script does everything

`scripts/drive.py` fetches the issue, builds the prompt, runs the agent, parses the verdict, saves artifacts. No multi-phase orchestration pipeline needed.
