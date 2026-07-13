# docs-manifest — the user-facing docs registry (owned, internal)

The artifact **lives at [`docs/manifest.json`](../../docs/manifest.json)** — hand-written,
beside what it describes (owned surfaces keep their home). It registers every user-facing
doc: roots, a small repo-owned surface→glob map, and one node per doc — diagrams included
(a node's path is the `.dot` source; the same-basename render is the same unit).

- **Schema (commons-owned):** `../locveil-commons/process/user-docs/manifest.schema.json`;
  prose convention: `../locveil-commons/process/user-docs.md` §4.
- **Coherence test (layer 2):** `backend/tests/test_docs_manifest.py` — node↔tree bijection
  under the roots, floor classes stay populated, covers reference declared surfaces,
  docs-verdict node-ids in the DONE ledger exist; schema validation when the commons
  sibling is present.
- **Versioning:** `docs-manifest-v1` tracks the manifest SCHEMA generation — bumped only
  on a schema reshape, never for node additions/removals (those are ordinary edits riding
  their causing task, guarded by the coherence test).
