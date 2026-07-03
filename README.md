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
4. **Drives** the browser via [browser-use](https://github.com/browser-use/browser-use) (Python agent on Playwright) to execute the steps
5. **Verifies** the bug reproduced (agent result analysis)
6. **Emits** a deterministic Playwright test + evidence artifacts

Then replay forever without the agent:

```bash
npx playwright test reproductions/9329/repro.spec.ts
```

## Architecture

```
Brain:  Claude Code (Grok skill + /loop) — plans, reasons, judges
Hands:  browser-use (Python, in-process) — Claude Sonnet 4 via OpenRouter → Playwright
Target: Plane (local docker-compose) — the app under test
```

**Phase 1 (Author):** Python `drive.py` runs browser-use agent. Expensive, once.
**Phase 2 (Replay):** Emitted Playwright `repro.spec.ts` runs. Cheap, N times.

See [HLD.md](./HLD.md) for the full locked architecture.

## Output (artifact bundle)

```
reproductions/9329/
├── repro-plan.json          # structured reproduction plan
├── action-log.json          # every agent step (thought, actions, result)
├── repro.spec.ts            # deterministic Playwright test
├── traces/
│   └── full-trace.json      # complete browser-use agent history
├── conversation.json        # full LLM conversation log
├── evidence-*.png           # screenshots at each step
├── agent-run.gif            # animated GIF of browser session
└── verdict.md               # agent's judgment + confidence
```

## Demo bugs

| # | Bug | Class |
|---|-----|-------|
| [9329](https://github.com/makeplane/plane/issues/9329) | 255+ char title shows generic error | form-validation |
| [9050](https://github.com/makeplane/plane/issues/9050) | Deleted stickies reappear on reload | state-persistence |
| [9124](https://github.com/makeplane/plane/issues/9124) | Sub-task expand requires 3 clicks | ui-interaction |

## Prerequisites

- [Plane](https://github.com/makeplane/plane) running locally via `docker-compose-local.yml` on `:3000`
- Chrome with `--remote-debugging-port=9222`
- Python 3.11+
- Node.js 20+ (for Playwright replay)
- OpenRouter API key
- `gh` CLI authenticated

## Setup

```bash
# Python (browser-use agent)
pip install browser-use python-dotenv

# Node.js (Playwright replay)
npm install

# Config
cp .env.example .env  # add your OPENROUTER_API_KEY + CDP_URL
```

## Run the drive script

```bash
# Reproduce issue #9329
python scripts/drive.py --issue 9329

# Or via npm:
npm run drive:9329

# Other issues:
npm run drive:9050
npm run drive:9124
```

Artifacts go to `reproductions/9329/`. Inspect the agent trace:
```bash
cat reproductions/9329/action-log.json | python -m json.tool
```

## Replay (no agent, no LLM)

```bash
npx playwright test reproductions/9329/repro.spec.ts
```

## Run as a skill (from Grok)

```
/repro https://github.com/makeplane/plane/issues/9329
```

## Known issues

See [ISSUES.md](./ISSUES.md) for every problem encountered during development, root causes, and fixes.

## License

MIT