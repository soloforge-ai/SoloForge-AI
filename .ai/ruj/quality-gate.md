# Ruj Quality Gate

Main records every gate against the final revision. A checklist alone is not proof.

## Specification
- [ ] Objective, scope and exclusions recorded.
- [ ] Testable acceptance criteria and risk-based checks recorded.
- [ ] Required context inspected; unknowns recorded.

## Build
- [ ] Implementation and changed-file purposes documented.
- [ ] No unrelated modifications or exposed secrets.
- [ ] Appropriate verification evidence recorded.

## QA — จ่ารุจ
- [ ] Execution mode and checked revision recorded.
- [ ] Every critical criterion verified with evidence.
- [ ] Relevant negative cases, error paths and regressions checked.
- [ ] No unresolved BLOCKER/HIGH; lower findings have dispositions.
- [ ] Unrun live checks clearly limit the completion scope.

## Review — ยามรุจ
- [ ] QA passed for this revision.
- [ ] Architecture, product workflow, costs and maintenance reviewed.
- [ ] No required review fixes outstanding.

## Main closure
- [ ] Any fixes passed affected QA and final-revision review.
- [ ] Required gates passed; evidence linked in task record.
- [ ] DONE scope distinguished from merge/deployment/live readiness.
- [ ] Pilot ledger updated without fabricated values.

FAIL → REWORK. Missing evidence/access → BLOCKED.
SELF_REVIEW must remain labeled as such; never count it as independent-agent QA.
