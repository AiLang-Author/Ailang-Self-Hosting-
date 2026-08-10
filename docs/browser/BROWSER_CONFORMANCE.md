# Browser JS Conformance — Scoreboard

> **Canonical doc:** [`Docs/Browser/JS_ENGINE_MASTER.md`](./Docs/Browser/JS_ENGINE_MASTER.md)  
> Scores, roadmap, browser readiness, and resume checklist live there.

**Updated:** 2026-08-05 · **Tip:** M128e7e1 (`9f4e6c52`)

| Track | Score | Artifact |
|-------|------:|----------|
| **Full test262** | **34,218 / 49,723 (~69%)** | [`results/test262_full_m128e7e1_SUMMARY.md`](./results/test262_full_m128e7e1_SUMMARY.md) |
| **Language** G2 primary | **~95.9%** pass/(pass+fail) | [`results/test262_lang_m128e7bt_SUMMARY.md`](./results/test262_lang_m128e7bt_SUMMARY.md) |
| **Desert** (AB/DV/TA/TAC) | **2,090 / 2,931 (71.6%)** | [`results/test262_desert_e7e1_SUMMARY.md`](./results/test262_desert_e7e1_SUMMARY.md) |
| Built-ins overall | ~47% | full e7e1 dump |

**Hard goal (long horizon):** high full-suite compliance + usable browser shell.  
**Near-term:** B-core polish; Temporal / full 95% deferred (see master doc).

```bash
python3 tools/test262_runner.py --full -j 8 --timeout 12
```
