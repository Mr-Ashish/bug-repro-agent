# Architecture — Bug Reproduction Agent

## System Layers

```
┌─────────────────────────────────────────────────────────────────┐
│  HUMAN                                                          │
│  "Reproduce issue #9329"                                        │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  GROK (Meta-Agent)                                              │
│                                                                 │
│  Reads: .claude/skills/repro-agent/SKILL.md                     │
│  Knows: drive.py CLI flags, exit codes, artifact paths          │
│  Does:  orchestrate scripts, interpret results, retry/chain     │
│                                                                 │
│  Runs:  python scripts/drive.py --issue 9329                    │
│  Then:  python scripts/post_comment.py --issue 9329             │
└──────────────────────────┬──────────────────────────────────────┘
                           │ subprocess
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  drive.py (Driver Script)                                       │
│                                                                 │
│  1. Auto-discover Chrome CDP (port 9222)                        │
│  2. Preflight: Chrome ✓  Plane ✓  gh ✓                          │
│  3. gh issue view → fetch title + body                          │
│  4. Template + issue body + creds → task prompt                 │
│  5. Create browser-use Agent(task, llm, browser)                │
│  6. agent.run(max_steps=50) with timeout                        │
│  7. Save artifacts to reproductions/<N>/                        │
│  8. Parse VERDICT line → exit code                              │
└──────────────────────────┬──────────────────────────────────────┘
                           │ in-process
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  browser-use Agent (Claude Sonnet 4 via OpenRouter)             │
│                                                                 │
│  Receives: natural language task with bug report + Plane creds  │
│  Does:     login → navigate → execute repro steps → observe     │
│  Emits:    VERDICT: REPRODUCED | <summary>                     │
│                                                                 │
│  This is the ONLY layer that reasons about the bug.             │
└──────────────────────────┬──────────────────────────────────────┘
                           │ CDP WebSocket
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Chrome → Plane (localhost:3000)                                │
│  Docker: Next.js + Django + Postgres + Redis + MinIO            │
└─────────────────────────────────────────────────────────────────┘
```

---

## UML Sequence Diagram

```mermaid
sequenceDiagram
    actor Human
    participant Grok as Grok<br/>(Meta-Agent)
    participant Drive as drive.py<br/>(Driver)
    participant GH as gh CLI
    participant Agent as browser-use Agent<br/>(Claude Sonnet 4)
    participant Chrome as Chrome<br/>(CDP)
    participant Plane as Plane<br/>(localhost:3000)
    participant Post as post_comment.py<br/>(Reporter)

    Note over Human,Grok: Layer 1 — Human → Meta-Agent
    Human->>Grok: /repro #9329
    Grok->>Grok: Read SKILL.md<br/>→ knows CLI flags, exit codes

    Note over Grok,Drive: Layer 2 — Meta-Agent → Driver
    Grok->>Drive: python scripts/drive.py --issue 9329

    Note over Drive,Plane: Preflight Checks
    Drive->>Chrome: TCP connect to CDP port 9222
    Chrome-->>Drive: ✓ reachable
    Drive->>Plane: HTTP GET localhost:3000
    Plane-->>Drive: ✓ responding
    Drive->>GH: gh auth status
    GH-->>Drive: ✓ authenticated

    Note over Drive,GH: Issue Fetch
    Drive->>GH: gh issue view 9329 --repo makeplane/plane<br/>--json title,body,url,number
    GH-->>Drive: {title, body, url, number}

    Note over Drive: Prompt Build
    Drive->>Drive: TASK_TEMPLATE + issue body<br/>+ Plane creds + nav map<br/>→ task prompt string
    Drive->>Drive: Save issue.json + task-prompt.txt

    Note over Drive,Chrome: Agent Lifecycle
    Drive->>Chrome: GET /json/version → webSocketDebuggerUrl
    Chrome-->>Drive: ws://localhost:9222/devtools/browser/...
    Drive->>Agent: Agent(task=prompt, llm=openrouter,<br/>browser=cdp, vision=True)

    Note over Agent,Plane: Layer 3 — Browser Automation (up to 50 steps)
    rect rgb(240, 248, 255)
        Agent->>Chrome: Navigate to Plane login
        Chrome->>Plane: GET /
        Plane-->>Chrome: Login page
        Chrome-->>Agent: Screenshot + DOM

        Agent->>Chrome: Type email + password
        Chrome->>Plane: POST login
        Plane-->>Chrome: Dashboard
        Chrome-->>Agent: Screenshot + DOM

        Agent->>Chrome: Navigate to project → issues
        Chrome->>Plane: GET /plane-dev/projects/.../issues
        Plane-->>Chrome: Work items list
        Chrome-->>Agent: Screenshot + DOM

        Agent->>Chrome: Execute reproduction steps<br/>(create issue, type long title, etc.)
        Chrome->>Plane: Various interactions
        Plane-->>Chrome: Bug behavior observed
        Chrome-->>Agent: Screenshot + DOM

        Agent->>Agent: Reason about observed<br/>vs expected behavior
    end

    Agent-->>Drive: "VERDICT: REPRODUCED | 256-char title<br/>shows generic error"<br/>+ AgentHistoryList

    Note over Drive: Artifact Saving
    Drive->>Drive: Save action-log.json (per-step)
    Drive->>Drive: Save evidence-*.png (screenshots)
    Drive->>Drive: Save agent-run.gif
    Drive->>Drive: Save verdict.md (stats + verdict)
    Drive->>Drive: Save traces/full-trace.json
    Drive->>Drive: Parse VERDICT regex → exit code 0

    Drive-->>Grok: exit code 0 (REPRODUCED)

    Note over Grok,Post: Reporting Phase
    Grok->>Post: python scripts/post_comment.py --issue 9329
    Post->>Post: Read verdict.md → status, stats
    Post->>Post: Read action-log.json → step table
    Post->>Post: Mask passwords everywhere
    Post->>Post: Build Markdown comment
    Post->>Post: Save github-comment.md
    Post->>GH: gh issue comment 9329<br/>--repo makeplane/plane<br/>--body-file github-comment.md
    GH-->>Post: ✓ Comment posted

    Post-->>Grok: exit code 0

    Note over Grok,Human: Result
    Grok-->>Human: Bug REPRODUCED ✅<br/>Artifacts: reproductions/9329/<br/>Comment posted to GitHub
```

---

## What Each Layer Owns

| Concern | Grok | drive.py | browser-use Agent | post_comment.py |
|---------|:-----:|:--------:|:-----------------:|:---------------:|
| User interface | ✅ | | | |
| Skill knowledge | ✅ | | | |
| Script orchestration | ✅ | | | |
| Exit code interpretation | ✅ | | | |
| Retry decisions | ✅ | | | |
| CDP auto-discovery | | ✅ | | |
| Preflight checks | | ✅ | | |
| Issue fetching (gh) | | ✅ | | |
| Prompt engineering | | ✅ | | |
| Agent lifecycle | | ✅ | | |
| Artifact saving | | ✅ | | |
| Verdict parsing | | ✅ | | |
| Crash recovery | | ✅ | | |
| Bug reasoning | | | ✅ | |
| Browser navigation | | | ✅ | |
| Screenshot capture | | | ✅ | |
| Verdict emission | | | ✅ | |
| Artifact reading | | | | ✅ |
| Comment generation | | | | ✅ |
| Password masking | | | | ✅ |
| GitHub posting | | | | ✅ |

---

## Key Insight

**Grok never touches the bug.** It's a pure orchestrator:
- Reads SKILL.md to know what's possible
- Translates human intent into script invocations
- Interprets exit codes to understand outcomes
- Chains scripts (drive → post_comment)
- Can adjust parameters (--timeout, --dry-run) based on context

**drive.py never reasons about the bug.** It's infrastructure:
- Fetches the issue, builds the prompt, manages the agent lifecycle
- Saves everything to disk even on crash
- Parses the structured verdict line mechanically

**The browser-use Agent is the only intelligence** that reads the bug report,
figures out what steps to take, drives the browser, observes the behavior,
and decides whether the bug was reproduced.