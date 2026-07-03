# Verdict: Issue #9050

**Issue**: [Deleted Stickies reappear on page reload](https://github.com/makeplane/plane/issues/9050)
**Date**: 2026-07-03
**Model**: gpt-4o
**Sticky text**: `REPRO-9050-1783102540993`

## Result: NOT REPRODUCED

The issue reports that deleting a sticky, then reloading the page, causes the deleted sticky to reappear. We attempted to reproduce this.

### What we observed

| Step | What happened |
|------|---------------|
| Created sticky | `REPRO-9050-1783102540993` appeared on stickies page |
| Deleted sticky | Used three-dot menu → Delete → Confirm |
| After delete (before reload) | Sticky still visible in DOM (possible stale render) |
| After page reload | Sticky **did not reappear** — extract returned empty |

### Conclusion

The bug as described in #9050 could **not be reproduced** on this build. The deleted sticky did not reappear after page reload.
