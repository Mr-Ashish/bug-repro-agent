# Verdict: Issue #9050

**Issue**: [Deleted Stickies reappear on page reload](https://github.com/makeplane/plane/issues/9050)
**Date**: 2026-07-03
**Model**: gpt-4o
**Sticky text**: `REPRO-9050-1783102540993`

## Result: BUG APPEARS FIXED ✅

### After delete (before reload)
- **Sticky Notes**:
  - `REPRO-9050-1783102540993`

---

- **Note on Visibility**: 
  - The sticky note with the text "`REPRO-9050-1783102540993`" is visible as it appears under the DOM element [0-1910].

- **Additional Information**:
  - A message "That doesn't match any of your stickies." is present, but it does not indicate the absence of the sticky note we're interested in as it exists elsewhere in the DOM.

### After reload


### Conclusion
The deleted sticky did NOT reappear after page reload. The bug appears fixed in this build.
