# Capability Graph and Process Layer

espansr's prompt notes are independent **capabilities**: jobs you can invoke
directly with a colon trigger, exactly as before. The optional process layer
adds discovery, relationships, context transport, and output validation around
them — without a required sequence, a current step, a router, or any automatic
execution.

Everything in this layer is optional. If you never touch it, espansr behaves
exactly as it always has.

## Concepts

- **Capability** — an independently invocable job represented by a template or
  system command (e.g. `research-report` → `:research`). Never a numbered step.
- **Artifact type** — what a capability consumes (`accepts`) or produces
  (`produces`): `rough-intent`, `goal-contract`, `research-question`,
  `evidence-report`, `gap-review`, `human-litmus`, `implementation-handoff`,
  `implemented-feature`, `visual-artifact`, `interactive-html`,
  `verification-report`, `feedback-directives`, `context-packet`.
- **Workflow** — an optional directed graph of useful relationships among
  capabilities. It may branch, merge, cycle, and have many entry points. It
  never owns your state, never blocks direct invocation, and never runs
  anything.
- **Handoff packet** — an explicit, user-saved Markdown artifact carrying
  selected context (objective, evidence, decisions, assumptions, unknowns,
  requested outcome) into a fresh model window.
- **Output contract** — optional machine-checkable structure a capability's
  generated output must contain, validated with `espansr check-output`.

## Stable capability identity

Workflow manifests reference capabilities by `capability_id`, never by
trigger, so renaming a trigger never breaks workflow membership. The
derived-ID policy for templates without an explicit `capability_id` is
deterministic:

1. An explicit `capability_id` in the template JSON wins.
2. A template loaded from disk falls back to its file stem
   (`verify.json` → `verify`).
3. An unsaved template falls back to the slug of its name.

Capability IDs must stay unique. `espansr validate` warns about duplicates,
and importing a template whose explicit ID is already owned by another
template conservatively clears the incoming ID.

## Bundled capabilities

| Capability ID | Trigger | Produces |
|---------------|---------|----------|
| `goal-refinement` | `:goal` | `goal-contract` |
| `research-report` | `:research` | `evidence-report` |
| `gap-review` | `:gaps` | `gap-review` |
| `visual-workflow` | `:visual` | `visual-artifact` |
| `html-help-doc` | `:html-help-doc` | `interactive-html` |
| `audit-packet` | `:audit` | `interactive-html` |
| `experience-audit` | `:ui-ux-audit` | `interactive-html` |
| `spec-discovery` | `:cb-transcript-feature` | `implementation-handoff` |
| `human-litmus` | `:litmus` | `human-litmus` |
| `feature-handoff` | `:feature` | `implementation-handoff` |
| `verification` | `:verify` | `verification-report` |
| `adversarial-review` | `:adversary-review` | `feedback-directives` |
| `feedback-apply` | `:feedback` | `verification-report` |
| `troubleshooting` | `:troubleshoot` | `verification-report` |
| `context-reset` | `:context` | `context-packet` |
| `reality-max` | `:reality-max` | `evidence-report` |
| `reality-min` | `:reality-min` | `evidence-report` |

`:verify` accepts a `verification-report` as well as implemented work and
handoffs, so re-verifying after `:feedback` is a direct edge. The other
bundled notes carry no capability metadata and stay directly invocable.

## Workflow manifests

Bundled topology lives in exactly one place: JSON manifests under
`templates/_meta/workflows/`. Bundled prompts keep `next_triggers` empty and
never route the user to another trigger — at runtime the catalog derives
neighboring capabilities from the manifests and shows them in `:coms`, and
nothing is ever written back into template files.

```json
{
  "workflow_schema": 1,
  "id": "evidence-research-cycle",
  "name": "Evidence Research, Challenge, and Presentation",
  "entry_points": ["research-report", "gap-review"],
  "nodes": [{"capability": "research-report", "role": "evidence"}],
  "edges": [
    {
      "source": "research-report",
      "target": "gap-review",
      "label": "Challenge the findings independently.",
      "artifact": "evidence-report"
    }
  ]
}
```

Validation (`espansr workflows validate`) allows multiple entry points,
branches, merges, and cycles — acyclicity is never required. It rejects
duplicate workflow IDs, duplicate node identities, dangling capability
references, edges with missing endpoints, entry points that are not nodes,
unknown schema versions, and any manifest that declares current-step state or
claims to execute actions.

Two workflows ship bundled:

- **`evidence-research-cycle`** — research (`:research`), independent
  challenge (`:gaps`), visualization (`:visual`), interactive HTML
  presentation (`:html-help-doc`), and context transfer (`:context`). Start
  anywhere; a gap review can loop back to research, and a diagram from
  `:visual` can be embedded by `:html-help-doc`
  (`visual-workflow → html-help-doc`).
- **`feature-delivery-cycle`** — goal refinement (`:goal`), research,
  challenge, human litmus (`:litmus`), implementation handoff (`:feature`),
  verification (`:verify`), adversarial review (`:adversary-review`), bounded
  feedback (`:feedback`), and context transfer. Every node is an entry point;
  `:feature` never requires a predecessor. A refined goal can go straight to
  human checks (`goal-refinement → human-litmus`), and a compiled handoff can
  have its checklist audited before the build
  (`feature-handoff → human-litmus`) as well as feed verification and
  adversarial review after a separate implementation run.

User manifests can be added under the live template store's
`_meta/workflows/` directory. That directory is local-only (`_meta/` is
gitignored by remote template sync).

### Diagrams

Both bundled workflows render as interactive diagrams inside espansr:

- **`:coms` → Processes view** — the graph is drawn on the popup. Click a
  node to see its trigger, what it accepts and produces, its use/avoid
  guidance, and every optional next step with its full label. The buttons
  under the diagram act on the selected node: copy its prompt, put the
  prompt in the scratchpad, or jump to its card in All Commands. Selecting a
  row in the Quick Reference table switches between workflows.
- **`:aopen` → Workflows panel** — the editor gains a "Show Workflows"
  toolbar button (`Ctrl+Shift+W`). Clicking a node selects that template in
  the browser and loads it in the editor; Enter or double-click also focuses
  the editor. The panel's visibility is remembered in `config.json`
  (`ui.show_workflows`).

Diagrams are drawn from the manifests, so they stay in sync with the
topology by construction. Two optional, presentation-only keys shape them:
`x`/`y` on a node (scene coordinates; when every node has them the manifest's
own layout is used, otherwise espansr computes a deterministic layered layout)
and `short` on an edge (the two-or-three-word label drawn on the arrow — the
full `label` still appears in the detail panel and as a tooltip). Loop edges
(A→B and B→A) draw in the accent color, and a node whose edges reach every
other node — like `context-reset` — draws once as a dashed "feeds any node"
source instead of one arrow per target. Keyboard: Tab / Shift+Tab move
between nodes, Enter activates the selection. Nothing in a diagram runs a
prompt; nodes only select.

## Discovery in `:coms`

The popup keeps the full alphabetical reference, previews, system entries,
scratchpad, escape behavior, and theming — and adds:

- a fuzzy search field ("challenge finished research" surfaces `:gaps`
  without knowing the trigger);
- "I currently have" / "I need to produce" artifact selectors;
- views: **All Commands** (default — the complete catalog is always one
  selection away), **Recommended**, **Processes** (the workflow graphs),
  **Recent**, and **Favorites**;
- per-command `use_when` / `avoid_when` guidance, workflow membership, and
  optional-next hints;
- direct actions: copy the trigger, copy the full prompt, place the full
  prompt in the scratchpad ("Prompt to scratchpad"), open the template in the
  full editor, star a favorite, and preview a handoff packet.

Ranking is local and deterministic — capability metadata, artifact
compatibility, workflow proximity, favorites, and recency. No model, no
network. Identical inputs always produce identical rankings. Selecting a
recommendation or a workflow edge only changes what is displayed or copies
text; it never runs a prompt, shell command, installer, sync, or network
action.

Favorites and recents are stored in the local `config.json` under
`discovery`; they are convenience state, never workflow position.

## Handoff packets

A packet is Markdown with YAML front matter — human-readable, versioned, and
safe to paste into any model window:

```markdown
---
espansr_packet: 1
title: Auth research handoff
artifact_type: evidence-report
workflow: evidence-research-cycle
created_from: research-report
requested_outcome: gap-review
---

# Objective
...

# Confirmed facts and evidence
...
```

The `:context` note (`context-reset`) writes its output in exactly these seven
`# ` sections — Objective, Confirmed facts and evidence, Decisions,
Assumptions, Material unknowns, Evidence references, Candidate capabilities —
with `(none)` under any section that has nothing to report and no front matter
of its own; the packet tooling adds the front-matter header when the note is
saved as a packet.

Rules the implementation guarantees:

- Preview never persists; only the explicit **Save packet** action writes a
  file, into `<config>/packets/` — outside the git-synced template store.
- Deleting requires an explicit action and touches only that one packet.
- No transcript, clipboard, or scratchpad capture by default; the "Create
  packet from scratchpad" button is an explicit selection.
- No secret fields, no current-step field. Newer user direction and current
  project evidence always outrank packet content.
- Unknown future front-matter keys survive round-trips (forward
  compatibility). Loading a packet never mutates templates or workflows.

Use `espansr packet list|show|validate|delete` from the CLI.

## Output contracts

A template may declare an `output_contract`: required sections, required
literal or regex markers with occurrence bounds, and forbidden markers.
`espansr check-output --template :feature <path>` validates a saved model
output, reports **every** unmet obligation, and exits nonzero on failure.
Structural conformance never claims semantic quality — a boilerplate section
can pass structurally and still fail human review.

The bundled `:feature` contract checks one final-artifact reply — the reply
that follows your approval of the pre-write packet — and never the
approval-round packet itself (the note says so beside the packet). It
requires the `FINAL IMPLEMENTATION META-PROMPT` and `REALITY SUMMARY`
sections; at least one `If this was built correctly:` litmus entry with a
`Model verdict:` and a `Human verdict:` field; the `ALL_GATES_GREEN` and
`BUDGET_EXHAUSTED` terminal states — and it fails any output whose human
verdicts were prefilled instead of left blank. The `INPUT COVERAGE`,
`CLARIFICATION STATUS`, `ARCHITECTURE OUTCOME`, `BEHAVIOR OUTCOME`, and
`PRESERVATION SET` blocks still belong to the packet the note prints; they are
not contract obligations.

## The `:litmus` capability

`:litmus` (capability ID `human-litmus`) creates, audits, or revises one
consolidated plain-language human-verification checklist for whatever
material you supply — rough intent, a goal contract, a report, a review, a
handoff, or an existing checklist. Entries describe what a person would do
and observe (visual and non-visual, operator and maintainer and downstream
included), never files or classes; model verdicts are preserved for later
implementation evidence and human verdicts always stay blank. It is fully
standalone: no workflow, no packet, and no `:feature` run is ever required.

## What this layer never does

- No required linear sequence, universal workflow, or global current step.
- No numbered process commands, model router, or automatic prompt chain.
- No hosted service or model API for normal discovery.
- No mandatory manifest or packet for using any command.
- No transcript, clipboard, or silent scratchpad persistence.
- No workflow metadata in generated Espanso YAML.
