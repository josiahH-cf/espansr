# Versioned capability catalog

`espansr catalog` lets a person or a connected client find useful reusable
definitions and see whether the installed copies match their source:

```powershell
python -m espansr catalog --intent research
python -m espansr catalog --json
python -m espansr catalog --capability gap-review --input evidence-report
```

Run `python -m espansr` from the selected checkout to inspect that candidate.
`--source templates` selects its canonical definitions explicitly;
`--installed PATH` selects a projection for comparison. These commands read
files, without pulling a remote, publishing, restarting Espanso or launching
work. A successful command means source validation passed; look at `status`
and `current.publication` for publication truth. An empty or missing installed
root remains unavailable. A private candidate is not an installed release.

The bundled population is 65 templates and four workflows at introduction.
All 65 are prompt-only; the four graphs are declarative. Explicit capability
IDs remain distinct from file identities. Missing IDs and incomplete intent,
input or output metadata are visible as `capability_metadata` and
`metadata_gaps`; no executor is inferred from prompt content. Existing local
templates and system triggers remain available in `:coms`; installed-only
private definitions are counted without exporting their names or content.

## Definition and execution contracts

The JSON interface is `espansr-capability-catalog-v1`, schema 1, additive to
`espansr-adapter-v1`. `entries` holds stable `template:<file stem>` and
`workflow:<declared id>` identities, relative source paths, description,
declared intent, inputs/outputs, variable names/types and output contract.
Every entry includes canonical byte and semantic hashes, source Git revision
(null if unqualified/unknown), installed byte and semantic hashes, validation,
and execution classification. JSON whitespace/key order differences compare
equal; different prose, metadata and values do not. Exact byte hashes remain
available for accepted work. Variable defaults, private operation values, local
paths and account/session details are not exported by default. A canonical
public template can explicitly opt in with `publish_definition: true`; its
exact source JSON bytes are then included as base64 `definition_bytes` in the
same atomic generation. The Meta-Prompt Generator uses this for connected
inline drafting. Consumers verify both byte and semantic digests before use.
Installed-only definitions never opt themselves into publication. A template
marked `local_only: true`, in the source or in its installed copy, is treated
like an installed-only private definition even when it also sets
`publish_definition`: it has no entry, metadata or bytes and is only counted in
`unmanaged_installed_templates`. A workflow built on a local-only capability
is omitted with it instead of failing qualification. A retained publication
that still describes a template now marked local only is withdrawn (removed)
as soon as espansr saves a template as local only (the editor, an import, a
restore). After a hand edit, the withdrawal happens the first time espansr
reads or publishes the catalog: `espansr catalog`, the `:coms` popup, or a
sync. No read
returns it, filtered or otherwise; `espansr catalog` reports `withdrawn`, and
warns when the file could not be removed so connected tools could still read
it. Publication resumes with the next complete build. A new selection from a
catalog held from before the change is refused when the definition it would
read is local only. A copy a connected tool already read, and a job frozen
before the change, are not recalled or rewritten. Derived
`effective_capability_id`, replacement labels and deprecation are metadata,
never new executor or dispatch aliases.

### Local-only templates for consumers

The qualified publication lists only templates that may be shared, so a
consumer that exposes exactly its entries never shows a private one. A consumer
that reads the live template folder itself has to apply espansr's rule to every
file before reading or exposing anything from it. A file may be shared only
when its bytes decode as UTF-8 (a byte-order mark allowed), or as UTF-16 when
they start with a UTF-16 byte-order mark, and parse as a JSON object whose
top-level `local_only` is absent or appears once with the value `false`.
Anything else is not shareable: `true`, any other value, a repeated
`local_only` key, something other than an object, bytes that do not decode
(never retry them as Latin-1), an unreadable file, or a file that does not
parse (whether or not it spells `"local_only": true`). A parser that keeps only
the last value of a repeated key, as plain `json.loads` does, cannot see the
repetition; read the object's key/value pairs (`object_pairs_hook` in Python).
The rule is `local_only_state_bytes` in `espansr/core/templates.py`, mirrored
without imports in `scripts/deliver.py`; a test keeps the two identical.

- Apply it on every refresh, so marking a template takes effect at the next
  read. Already-frozen jobs are history and keep their bytes.
- Keep a file that is not shareable out of new listing, selection and
  admission. That includes a file that was public until it became unreadable,
  unparsable or not an object while the last publication still lists it. Such
  a file is not a withdrawal: leave the publication and frozen history as they
  are, and list the template again once its file reads as shareable.
- After a hand edit, the publication can still describe the template until
  espansr next reads or publishes the catalog, so a consumer that reads the
  publication applies the rule to each entry's live file as well.
- A consumer that keeps its last good generation after a failed refresh drops
  the templates excluded now.

espansr cannot apply the rule for a consumer. A consumer that listed every live
file, and checked only that the publication's members were present, would show
local-only templates in its discovery and let a new preparation read their
text.

A deliberately authored optional template field can identify a route:

```json
{"execution": {"kind": "instruction-skill", "id": "example-skill", "hosts": ["windows"], "clients": ["codex"]}}
```

Supported kinds also include `native-tool`, `browser-interaction` and `other`.
The declaration is metadata, never an executable command or authentication
claim. Its initial class is `declared-unobserved` and availability is unknown.
`select_entries` matches capability, host, client, available input kinds and
declared natural intent. It neither ranks tools nor creates a plan. An explicit
usable `selected` identity survives relevance filtering; incompatibility stays
visible. Only caller-owned current inventory evidence matching the exact
definition digest, route, host and client can report supported execution.
The CLI has no such inventory and makes no supported-execution claim. Inventory
is re-evaluated per read, never stored as a permanent availability receipt.

## Publication and failure

The existing publish/setup/install path qualifies the catalog after writing
trigger output. Bundled sync also projects source workflow files and preserves
overwritten raw topology under `_versions/wf/`. Backups use short digest names
for Windows path limits and compare existing bytes before reuse. No cleanup
or deletion of user workflow files is added.

`_meta/capabilities.json` is one atomic, deterministic descriptor/receipt envelope
in the installed templates root. It binds the complete canonical definition
digest, source revision when known, installed hashes, validation outcome and
adapter schema. `catalog_sha256` hashes the envelope without that field, using
sorted compact UTF-8 JSON. This hash detects corruption, not authorship or
authentication; trust remains with the existing source/install owner.

`publish_catalog` replaces that file only if every canonical definition is
valid and every installed projection is semantically equal. An invalid new
definition, partial install, duplicate identity, broken workflow reference or
drift leaves the last complete file untouched, unless that file still describes
a template now marked local only, which withdraws it. A write failure also
retains it. Sync says which happened: retained, withdrawn, or none published
until the build is complete.
Trigger publication remains usable for intentional local edits and prints a
catalog drift warning. Catalog qualification proves definition parity, without
claiming an Espanso process reload or actual client typing. Those have their
own owner checks.

`inspect_catalog` returns `current` and the last `published` envelope separately.
Consumers display drift/unavailability alongside old descriptors, without
silently calling the older publication current. `:coms` row data carries the
same `capability_descriptor` and a separate `publication_status`. Local-only
rows have no public descriptor. Unknown schemas or corrupt publications are
unavailable, never silently accepted as compatible.

## Accepted work and OA integration

`freeze_definition` returns a **private job payload** with the exact chosen
definition bytes, selected descriptor, source/catalog lineage, exact supplied
values and unchanged caller context binding. The existing profile/job owner
persists it alongside request/attempt/source identities. `restore_frozen` and
`render_frozen` use only that saved payload after restart or replay. New work
can choose newer definitions; old work does not reselect from the current catalog.
Changed bytes during selection are refused, without substituting another prompt.
Defaults are not automatically supplied for required values.

Espansr remains the editor and publication owner. OA must read the qualified
installed envelope through its existing Espansr source adapter and reuse the
same descriptor in Dot context, Console choices and skill discovery. Preserve
the existing adapter-v1 record/prepare fields while attaching the descriptor
and explicit drift state. OA's contextual profile/job serialization owns the
private frozen payload and its durable context binding. It must not edit
installed definitions or copy them into another planning store. Actual native
execution remains with the selected tool/workflow owner.

This repository supplies the producer, popup descriptor, source compatibility
probe and exact owner handoff. The probe compares all bundled definitions with
the adapter from the pinned OA dependency candidate, exercises prompt
preparation, and checks old frozen payloads after a compatible update.
`scripts/check_catalog_adapter.py --adapter-file PATH --expected-sha256 SHA`
requires that exact external source. OA deployment, cross-surface consumption
and actual installed/trigger/client checks remain with their assigned owners;
the private probe does not prove those effects happened. See
`receipts/ds07/owner-handoff.json` for their version-bound readbacks.

Public definitions still require public-source review: no actual private
values, account details, task content, passwords or credential-bearing URLs.
Credential-shaped strings and private source fields block qualification without
echoing values. This guard cannot classify arbitrary personal prose. Private
variables resolve only inside the authorized operation; they never enter a
public catalog or receipt. Permission modes, exact Stop, accounts and runtime
effect identity are untouched by this read/selection contract.
