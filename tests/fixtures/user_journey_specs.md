## TARGET AND GOAL

Target: the intentionally incomplete synthetic notes CLI at
`tests/fixtures/journey_notes.py`, not Espansr's application code. Its requirement
in the module docstring is to print unread titles in input order without
changing the input. This is an illustrative local authoring exercise, not an
installed product or an independent model evaluation.

Actor: a person finding unread notes. Final goal: given valid note records,
return exactly the unread titles in their input order and preserve every input
record. Completion requires observed CLI output plus an input-preservation check.

Exact SYNTHETIC input:

```json
[{"title": "Moon", "read": false}, {"title": "Sea", "read": true}, {"title": "Forest", "read": false}]
```

## JOURNEY AND REQUIREMENTS

| Step / requirement | Expected | Observed | Evidence | Status |
| --- | --- | --- | --- | --- |
| Invoke the supported local CLI with valid JSON | Receive a JSON list | A JSON list is printed with exit 0 | Regression test invokes the fixture as a subprocess | PASS |
| Find only unread notes | `["Moon", "Forest"]` | `["Moon", "Sea", "Forest"]` | Actual fixture stdout checked in the regression | FAIL |
| Preserve ordering | Moon before Forest | Moon before Forest | Actual output order and list traversal | PASS |
| Preserve input records | Original JSON unchanged | The fixture only parses its argument; the test's input remains unchanged | Source trace and input assertion | PASS |
| Human acceptance of this experience | Actual user judgment | No human observation collected | No acceptance is inferred from these checks | UNVERIFIED |

## BACKEND MAP

The existing path is `sys.argv[1]` JSON text -> `json.loads` -> `titles(notes)`
-> a list comprehension -> `json.dumps` -> stdout. The module owns this complete
local path. It contains no persistent store, background job, service, account or
network integration. The comprehension extracts every title and never checks
the `read` field, explaining the failed requirement. See `journey_notes.py`'s
`titles` and `__main__` block. This is current backend evidence, not a proposed
service design.

## FINAL-STATE SPECIFICATIONS

The synthetic fixture has no native spec format or runner. The self-contained
specification below is ready for a separate implementation request. No fixture
or application change is made by authoring this specification.

### Unread-title filtering

- Problem and basis: the fixture's stated unread-only requirement fails because
  `titles` extracts all titles, including the already-read Sea note.
- Final behavior: for valid records, include a title exactly when its `read`
  flag is false. Preserve relative input order and every input record.
- Backend owner: refine `titles(notes)` in `journey_notes.py`; keep JSON argument
  parsing, JSON list output and stdout delivery in the existing CLI path. Add no
  service, persistence or new command interface.
- Scope: unread selection only. Preserve title spelling and duplicates, input
  order, current CLI argument shape and successful output format. Invalid JSON
  and missing-record-field handling retain their current behavior; this spec
  creates no new recovery policy for inputs outside the stated valid-record
  boundary.
- Dependencies: none beyond the fixture's existing Python standard library.
- Acceptance: the exact mixed sample prints `["Moon", "Forest"]` with exit 0;
  all-read input and an empty list each print `[]`; two unread records with the
  same title both remain in their original order; compare the input records
  before and after the function call to establish that they were not modified.
- Evidence method: run the actual local CLI for output cases and a direct
  input-preservation check. These checks are specified for the future repair;
  this authoring exercise does not mark them as passed.

Coverage: unread-only output maps to this one refinement spec. Input order and
preservation map to existing evidence and the spec's preservation checks. Human
acceptance remains UNVERIFIED and does not authorize implementation or delivery.
No unresolved product choice blocks the spec. This exercise authors a goal,
backend explanation and specification; it does not build or install the filter.
