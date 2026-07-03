# repro-agent

Point a browser agent at a GitHub issue, watch it reproduce the bug — live.

Built for the **Browser-Use Hackathon** (July 4, 2026, Bengaluru).

## What it does

```
/repro https://github.com/makeplane/plane/issues/9329
```

1. **Reads** the GitHub issue, extracts steps to reproduce
2. **Plans** the reproduction — classifies bug type, structures steps
3. **Seeds** the app with required data state
4. **Drives** the browser via [Stagehand](https://github.com/browserbase/stagehand) to execute the steps
5. **Verifies** the bug reproduced (screenshot + vision judgment)
6. **Emits** a deterministic Playwright test + evidence artifacts

Then replay forever without the agent:

```bash
npx playwright test reproductions/9329/repro.spec.ts
```

## Architecture

```
Brain:  Claude Code (Grok skill + /loop) — plans, reasons, judges
Hands:  Stagehand server-v3 (Gemini Flash) — clicks, types, observes
Target: Plane (local docker-compose) — the app under test
```

**Phase 1 (Author):** Agent reproduces the bug. Expensive, once.
**Phase 2 (Replay):** Emitted Playwright script runs. Cheap, N times.

See [HLD.md](./HLD.md) for the full locked architecture.

## Output (artifact bundle)

```
reproductions/9329/
├── repro-plan.json          # structured reproduction plan
├── action-log.json          # every browser action taken
├── repro.spec.ts            # deterministic Playwright test
├── evidence/
│   ├── screenshot-before.png
│   ├── screenshot-after.png
│   ├── video.webm
│   └── console.log
└── verdict.md               # agent's judgment + confidence
```

## Demo bugs

| # | Bug | Class |
|---|-----|-------|
| [9329](https://github.com/makeplane/plane/issues/9329) | 255+ char title shows generic error | form-validation |
| [9050](https://github.com/makeplane/plane/issues/9050) | Deleted stickies reappear on reload | state-persistence |
| [9124](https://github.com/makeplane/plane/issues/9124) | Sub-task expand requires 3 clicks | ui-interaction |

## Prerequisites

- [Plane](https://github.com/makeplane/plane) running locally via `docker-compose-local.yml`
- [Stagehand server-v3](https://github.com/browserbase/stagehand) running on `localhost:3000`
- Node.js 20+
- `gh` CLI authenticated

## Setup

```bash
npm install
cp .env.example .env  # add your API keys
```

## Usage

From a Grok session in this repo:

```
/repro https://github.com/makeplane/plane/issues/9329
```

## License

MIT