# Design and code audit

This audit records the production interface before and after the October 2026 product-design pass. It evaluates visible decisions and maintainability, not whether code or design was authored by a person or a model. Scientific routing, provenance, safety rules, numerical models, and saved evidence are outside the redesign's replacement scope.

## Inspection record

The existing production application ran at `http://127.0.0.1:3000`, with the research API at port 8000. Browser captures used **1440 × 1000**, **1024 × 768**, and **390 × 844** viewports. Curated results, simulation, uncertainty demonstration, and generated reports came from the running application, without substituting responses.

- `artifacts/design-before/baseline.json` (local-only): 39 captures covering curated interpretation, overview, mechanisms, focused pathway, connection evidence, full graph, simulation, Bayesian demonstration, report controls, Library, saved investigations, About, and the generated HTML report. These were visually inspected at all three sizes. No page exceptions or document-level horizontal overflow were recorded.
- `artifacts/design-before/root-captures.json` (local-only): 27 captures covering landing, live interpretation, summary, pathway, evidence, safety alternative, clarification, loading, and an attempted network-error capture. **The initial `network-error-*.png` files show the pending interpretation state, so they are not accepted as error-state verification.** The error needs a state-based wait and recapture.
- Capture scripts and images remain in the ignored `artifacts/design-before/` directory. These paths describe local review evidence and are not included in the public repository.

## Visual findings and priorities

| Area                         | Observed problem                                                                                                                                                                                                       | Design response                                                                                                                      |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Landing                      | The oversized two-line title, large prompt panel, three depth choices, and starter buttons dominate the first screen. Examples begin below the desktop fold.                                                           | Start a compact research workspace with useful curated links. Use a normal research default and place expansion after results.       |
| Typography                   | One system-sans stack carries titles and prose; bold controls compete with headings. Small uppercase monospace labels repeat the meaning of nearby headings.                                                           | Introduce an editorial serif for major titles and a restrained sans for interface text. Keep mono for actual technical content.      |
| Shared surfaces              | `.surface` uses an 18px radius and shadow; `.surface-flat` uses 14px. Cards, controls, badges, and inset panels repeat these rounded boundaries.                                                                       | Use rules and spacing for document sections. Reserve modest containers for interactive boundaries and overlays.                      |
| Curated result               | The first mechanism cards begin around the bottom of the 1000px desktop capture. Three equal cards impose the same emphasis on differing amounts of content.                                                           | Shorten repeated introductions and present numbered mechanisms as readable entries. Preserve context and ranking qualifications.     |
| Live result                  | The summary repeats a preliminary-source label, source link, and disclosure around every extract. Prose can span over 100 characters per line.                                                                         | Set a reading measure and consolidate repetitive labels without turning exact extracts into unsupported synthesis.                   |
| Citations                    | Curated overview links repeatedly say “Source 1” for different local citation lists. Evidence uses several badges before a paper title.                                                                                | Use consistent numbered references and compact, keyboard-accessible previews. Preserve the full record and why it is cited.          |
| Focused pathway              | A structural panel contains a figure panel containing wide rounded node panels. Mobile padding compounds.                                                                                                              | Treat the path as a figure with a caption, thin relationships, clear labels, and its textual alternative.                            |
| Evidence                     | A 390px connection view leaves roughly 230px for prose because of nested panel padding. Long titles and qualifiers become difficult to scan.                                                                           | Remove redundant wrappers and use a source heading, passage, and metadata list. Keep conflicting results visible.                    |
| Full graph                   | Filters consume roughly 330px above the desktop canvas. Large saturated shapes and overlapping relationship labels compete. On mobile, a desktop-sized graph remains partly outside the visible canvas after resizing. | Use a dedicated workbench, quieter graph styling, and deliberate responsive canvas handling. Retain filters and inspection controls. |
| Library and saved work       | Every saved question is a separate rounded rectangle. Repeated questions saved on the same day are visually indistinguishable.                                                                                         | Use an ordinary list with useful date/context metadata. Do not silently merge distinct saved evidence snapshots.                     |
| Simulation and Bayesian demo | Explanations, controls, charts, and tables sit in repeated containers. The posterior table scrolls internally on mobile, so its later columns are initially out of view.                                               | Keep functional groupings, simplify the presentation, and make horizontal table access evident and keyboard usable.                  |
| Reports and About            | A separate card wraps each report section and each About step. Report download controls get an oversized green success panel.                                                                                          | Typeset the report as a document; use a plain ordered explanation and quiet ready state. Preserve report content and export formats. |
| Loading and guidance         | Loading has large empty space and implementation-oriented prose. Scientific boundaries are repeated in global and local copy.                                                                                          | Present the actual question and truthful research stages quietly. Keep the relevant limitation where it affects a decision.          |

Clipping inside the graph or a scrollable table is distinct from page overflow. The absence of document overflow does not prove that the visible graph or table is useful at 390px.

## Performance baseline

This is **one local Chromium sample**, with a fresh browser context, an already running production server, no CPU/network throttling, and no claim to a field benchmark.

| Measurement                                    | Before redesign |
| ---------------------------------------------- | --------------: |
| First contentful paint                         |           336ms |
| Document load event                            |         309.5ms |
| Observed landing cumulative layout shift       |               0 |
| Landing JavaScript resources                   |               5 |
| Encoded landing JavaScript bytes               |         145,791 |
| JavaScript resources before opening full graph |               5 |
| JavaScript resources after opening full graph  |               7 |
| Additional encoded graph JavaScript bytes      |         140,797 |
| Loaded font faces / font requests              |           0 / 0 |

The graph's existing dynamic import works: its two extra chunks arrive only after opening the advanced graph. Preserve this boundary. The baseline font declaration names Inter but downloads no font; actual rendering relies on installed/system fallbacks. Compare fonts, encoded resources, layout shift, and responsive graph behavior after the redesign rather than assuming an improvement from a new font stack.

## Code and test review

Keep the existing boundaries that have a reason: the shared API request helper, typed scientific models, lazy graph/lab imports, `ChartFrame` visibility measurement, and report caching across tab remounts. Their purposes are observable in the browser or protected by behavior tests.

The small number of production comments reviewed explain invariants: weakest-edge confidence is not clinical certainty; hidden charts must not discard scientific runs; a report request must survive tab remounts; malformed API responses should not expose raw content. These should remain. Removing comments indiscriminately would erase useful constraints.

Existing report tests exercise retained downloads, an in-flight request surviving remount, retry after failure, and switching investigations. Their mocked network boundary is appropriate for those UI behaviors; the production browser workflow additionally generates and reads a real report. Neither layer alone establishes report scientific validity.

The independent static/API/test audit found:

| Finding                                               | Evidence and action                                                                                                                                                                                                                                      |
| ----------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| No unused TypeScript locals or parameters at baseline | `tsc --noEmit --incremental false --noUnusedLocals --noUnusedParameters` passed. Major components all have callers; there is no justification for deleting a screen wholesale.                                                                           |
| Dead and overridden CSS                               | Search found no use of `.tab-list`, `.tab-button`, `.chain*`, or `.metric-bar`. Earlier page-shell background/pseudo rules are overridden; `--shadow` is consumed only by an overridden declaration. Remove these after checking the final selector set. |
| Constant presentation props                           | Graph, simulation, Bayesian, and peptide labs receive constant `advanced=true`; `ResultsView`'s optional `advanced` prop is never supplied. These can be simplified without removing advanced functionality.                                             |
| Obsolete API wrapper                                  | `interpretQuestion` has no production caller; only its own API test invokes it. The active workflow calls `interpretResearch`. Remove the obsolete wrapper and test the actual request contract.                                                         |
| Malformed API errors bypass the fallback              | The previous error branch cast arbitrary parsed JSON to `ProblemDetail`. Null, wrong types, or mismatched status could reach the UI. Validate this boundary and retain safe error text for invalid payloads.                                             |
| A graph-bound test does not reach the bound           | The prior bounded-graph test uses only three nodes, so it cannot detect a broken 12-node limit. Use a larger fixture and verify both bounded selection and preservation of a longer selected path.                                                       |
| Repeated date formatting                              | Saved work and source records format dates independently. A small shared formatter can make timezone and invalid-date behavior explicit; avoid a larger formatting abstraction.                                                                          |

The initial API/presentation corrections passed **19 focused tests in two files** (38.55s). Existing lab/report tests protect stale settings, no duplicate requests, cache retention, retries, missing models, and warning semantics; these expectations remain. Mocked universal-research browser tests are UI contracts, not proof of live provider retrieval. The separate production/live workflows remain necessary.

Dead-code deletion requires both static and search evidence. Network error handling belongs at request/parsing boundaries; retaining a safe fallback is different from hiding a failure. No scientific assertions or expectations will be weakened to accommodate the visual changes.

## Implementation and acceptance order

1. Make the landing → loading → live summary → mechanisms → pathway → citation sequence coherent, then review production captures at all three sizes.
2. Propagate its typography, rules, spacing, references, and controls to curated results, Library, guidance, reports, and labs. Keep the full graph a separate workbench.
3. Reinspect each screen for unnecessary containers, narrow prose, excessive color, weak wrapping, and unclear controls. Record remaining weaknesses rather than approving by screenshot existence.
4. Verify visible focus, citation keyboard behavior, semantic headings, graph text alternatives, reduced motion, contrast, mobile controls, and error/retry states.
5. Run `pnpm verify`, `pnpm graph:validate`, and production capture workflows. Compare the measured performance sample, and document actual implementation decisions in `frontend-design.md`.

## Implemented design and code decisions

The landing workspace places the question beside useful investigation links and recent work. Standard research is the default; scope controls remain under Research options, with an expanded search available after results. Newsreader titles, IBM Plex Sans interface text, warm paper surfaces, restrained semantic color, and 4–6px corners replace the previous repeated cards. See [frontend design](frontend-design.md) for the rationale.

Both result types now lead with a readable brief and numbered mechanisms. Curated and provisional claims retain their distinct scientific status. Inline numbered references open a shared native source drawer; reference numbers stay consistent throughout each result. Figures keep their explicit causal or source-link meaning. The full graph remains optional, with filters, canvas, inspector, and a keyboard-accessible text version. Library, saved work, safety guidance, error states, reports, and numerical tools use the same hierarchy.

No scientific screen was deleted. Removed UI consists of prompt chips, the large pre-submit depth selector, redundant structural card wrappers, and decorative styles. Verified dead CSS, the unused `interpretQuestion` client wrapper, constant `advanced` props, an unused example description field, and duplicate dialog-test setup were removed. Domain types, API parsing boundaries, scientific comments, chart measurement, lazy imports, and report caching were retained because they protect real behavior. A shared UTC formatter replaces duplicate date formatting; saved snapshots include time.

The test audit replaced an obsolete-client-only contract check with the active research request contract and exercised the graph's node limit with a fixture large enough to exceed it. API tests now reject malformed problem responses. Citation tests protect numbering, provenance, and focus restoration. Scientific assertions and numerical expectations were not relaxed. Browser selectors changed only where deliberately edited labels changed.

## Screenshot-driven refinement

Review of the first production redesign led to a second pass:

- Moved detached curated citations into the finding paragraphs and separated evidence metadata clearly.
- Restored citation focus when React unmounts a closed native dialog. The browser check allows Tab to reach browser chrome; whenever the page itself has focus, it must stay inside the dialog, never on the inert background.
- Reduced the mobile full-map canvas to 380px and added an explicit zoom/text-view cue. Added a named, keyboard-focusable scroll region and mobile cue for Bayesian interval columns.
- Removed empty pathway controls and unavailable report links from results without evidence; evidence gaps remain visible, including in Quick mode.
- Added save times to distinguish repeated questions and shortened the safety introduction without changing its restrictions.
- Removed a duplicate report rule and simplified report headings. A real browser console error exposed unsupported `frame-ancestors` in a meta CSP: the meta directive was removed while both report routes retain HTTP frame protection. New reports use readable UTC creation times and preserve exact ISO provenance.

Existing saved report documents are immutable and keep their original presentation. Fresh reports were required to review the new styles and CSP. The initially invalid baseline error capture was replaced by a capture that waits for the specific failure heading; controlled loading, error, partial, and empty states are labeled as fixtures rather than live-provider observations.

## Final production checks — October 5, 2026

The final `pnpm verify` completed with exit code 0 after the screenshot-driven fixes: **384 Python tests**, **54 Vitest tests**, **9 production Chromium workflows**, and **11/11 offline evaluations** passed. Ruff format/lint, strict mypy, Prettier, ESLint, TypeScript, and the production webpack build passed. Browser tests used `CAUSALBIO_E2E_PRODUCTION=1` and `CI=1` with fresh servers; all nine passed on the first attempt in 33.3s. `pnpm graph:validate` passed both curated packs. Logs: `artifacts/design-verify-final.log` (local-only) and `artifacts/design-graphs.log` (local-only). The existing Starlette test-client deprecation warning remains; coverage was not remeasured during this pass.

The [final capture record](assets/design/review-record.json), completed October 5 at 22:35 UTC, records **99 images across 33 states at 1440×1000, 1024×768, and 390×844**. It includes light/dark results and graphs, both research paths, evidence drawers, reports, numerical tools, saved work, guidance, and explicitly labeled loading/failure/empty fixtures. The complete image matrix stays local; the public repository retains this manifest and selected documentation screenshots. All captures stayed within the document width. There were no unexpected console errors, warnings, or page exceptions; the intentionally injected 503 is recorded separately. The real tendon and BDNF workflows retain source availability and retrieval timestamps, including cache use.

Keyboard checks passed for Enter-to-open citations, native modal focus behavior, Escape and focus restoration, graph relationship inspection, and saved-session reopening. Explicit safe-alternative selection was verified before retrieval. Reduced-motion emulation disabled smooth scrolling and reduced transitions. **123 rendered text samples across five light/dark screen states had no contrast failures**; the lowest sampled ratio was 5.23:1. This sampling is narrower than a complete accessibility audit.

| Local production sample                        |        Before |         After |
| ---------------------------------------------- | ------------: | ------------: |
| First contentful paint                         |         336ms |         252ms |
| Document load event                            |       309.5ms |         302ms |
| Landing cumulative layout shift                |             0 |       0.01707 |
| Encoded landing JavaScript                     | 145,791 bytes | 146,433 bytes |
| Landing font requests / encoded bytes          |         0 / 0 |    2 / 98,392 |
| JavaScript resources before → after full graph |         5 → 7 |         5 → 7 |
| Additional encoded graph JavaScript            | 140,797 bytes | 140,600 bytes |
| Graph action to visible canvas                 |  Not measured |         481ms |

These are single unthrottled local samples, not evidence of a speed improvement. The identity fonts add 98,392 encoded bytes; the landing JavaScript adds 642 bytes and layout shift increases slightly. Newsreader and Plex Sans loaded from the build; Plex Mono remained unloaded on landing. Graph loading stays deferred. Measurements and resource entries are reproducible from the capture script and manifest.

Run production review from `apps/web`, with the API and production web server running:

```powershell
node scripts/capture-design-review.mjs
node scripts/capture-docs-screenshots.mjs
node scripts/capture-live-research.mjs
```

## Remaining design and verification limits

- Dense full maps still have overlapping relationship labels. At mobile scale the fitted overview is not readable without zooming or using the text version and inspector. A smaller canvas and an honest cue improve access; they do not solve graph layout generally.
- Exact source extracts can make the mobile research brief long. They retain qualifiers and provenance rather than presenting a newly invented biological synthesis. Fuller editorial summarization would require separate scientific validation.
- Existing immutable report snapshots retain their previous styles. Only newly generated reports receive this pass's presentation changes.
- Keyboard and visual browser review uses Chromium. This is not a full screen-reader audit, a cross-browser certification, or an observed novice usability study. Solid-background text contrast samples do not cover every component, canvas label, or WCAG criterion.
- Resource sizes, font requests, layout shift, and graph opening were sampled locally. No field telemetry, throttled benchmark series, exhaustive unused-JavaScript analysis, or React Profiler trace was collected. The new font assets have a measurable cost; a changed local paint time alone would not establish a speed improvement.

Code inspection confirms that citation opening, search typing, and inspector selection do not recreate Cytoscape. Theme updates change its existing styles, and cleanup disconnects observers and destroys the instance. Filters or a different selected pathway do rebuild the graph and reset its viewport; resizing also refits it. This remains a limitation for larger maps, without a measured regression in the small curated packs. Visited analysis panels stay mounted to preserve completed runs; chart data is memoized from completed results, and numerical requests run only on explicit actions.
