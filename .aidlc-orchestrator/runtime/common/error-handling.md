# Error Handling and Recovery

## Principles
1. Identify error → assess impact → communicate → offer solutions → log in `audit.md`

## Severity Levels

| Level | Definition | Examples |
|-------|-----------|----------|
| **Critical** | Workflow cannot continue | Missing required files, invalid input, system errors |
| **High** | Stage cannot complete | Incomplete answers, contradictions, missing dependencies |
| **Medium** | Continue with workarounds | Optional artifacts missing, non-critical validation fails |
| **Low** | Non-blocking | Formatting issues, optional info missing |

## Stage Error Quick Reference

| Stage | Error | Action |
|-------|-------|--------|
| Workspace Detection | Cannot read workspace | Ask user verify path/perms; use provided info |
| Workspace Detection | Corrupted aidlc-state.md | Ask: start fresh or recover? |
| Requirements | Contradictory requirements | Follow-up questions; do NOT proceed until resolved |
| Requirements | Incomplete answers | Highlight gaps; provide examples; block progress |
| User Stories | Cannot map to stories | Return to Requirements for clarification |
| User Stories | Ambiguous planning answers | Targeted follow-ups; block until resolved |
| Application Design | Unclear arch decision | Follow-ups; block until clear |
| Design | Circular dependencies | Identify cycles; suggest refactor; revise boundaries |
| NFR | Incompatible tech stack | Show conflicts; ask user to choose; block |
| NFR | Requires human action | Mark HUMAN TASK; provide instructions; wait |
| Code Generation | Plan incomplete | Return to Design; fill gaps |
| Code Generation | Syntax errors | Fix and regenerate; verify compiles |
| Code Generation | Test generation fails | Create basic structure; mark for manual completion |

## Recovery Procedures

### Partial Stage Completion
1. Load stage plan → find last `[x]` → resume from next `[ ]` → verify prior steps

### Corrupted State File
1. Backup → ask user current stage → regenerate from existing artifacts → resume

### Missing Artifacts
1. Identify what's missing → check if regenerable → re-run that stage OR ask user → log gap

### User Wants Restart
1. Confirm (data loss) → archive existing → reset status → re-execute

### User Wants Skip
1. Confirm implications → log reason → mark SKIPPED → proceed (may break deps)

## Session Resumption Errors

| Situation | Action |
|-----------|--------|
| Stage marked complete but artifacts missing | Mark incomplete; re-execute |
| Artifacts exist but state shows incomplete | Verify artifacts; update state |
| Multiple stages marked "current" | Review artifacts; ask user; fix state |
| Loaded artifacts contradict | Present contradictions; ask user; reconcile |

**Resumption best practices**: Validate state matches artifacts; load incrementally; fail fast on critical gaps; offer options (regenerate/provide/restart); log recovery.

## Escalation: When to Suggest Starting Over
- Multiple stages have errors
- State file severely corrupted
- Requirements changed significantly
- Architectural decision must reverse

**Before restart**: Archive all work → document lessons → identify what to preserve → get user confirmation.

## Logging

Errors: `## Error - [Stage] | Timestamp | Severity | Description | Cause | Resolution | Impact`
Recovery: `## Recovery - [Stage] | Timestamp | Issue | Steps | Outcome | Files Affected`
