# Frontend design

CausalBio is a research notebook with interactive analysis. Its identity comes from the way it presents a question, its evidence, and its unresolved assumptions. The scientific engines and evidence contracts remain separate from this presentation pass.

## Typography

Newsreader gives investigation titles and major headings the rhythm of a research publication. IBM Plex Sans carries prose, navigation, controls, and tables. IBM Plex Mono is reserved for raw data and technical identifiers; section labels use the interface font. The scale is defined in `globals.css`: display 40–56px, page titles 32–42px, sections 25–30px, and body text 16px. Small supporting text is at least 13px.

Only upright Newsreader 400/600, Plex Sans 400/500/600, and Plex Mono 400 are requested. `next/font` serves the build's font assets locally with system fallbacks; the mono face is not preloaded. No separate font binaries are checked in. See the [Next font documentation](https://nextjs.org/docs/app/api-reference/components/font), [Newsreader license](https://github.com/productiontype/Newsreader), and [IBM Plex license](https://github.com/IBM/plex).

## Layout and hierarchy

The home workspace gives the question most of the available width. The adjacent list earns its space with curated examples and saved research. It becomes a single column on smaller screens. Search scope is available under Research options; standard research is the default, and results offer an expanded search.

Results read in this order: question, research summary, numbered mechanisms, focused figure, evidence and limitations, optional analysis, and report. Mechanism rows use rules and alignment instead of equal-size cards. Reading columns are bounded by character width; the graph and numerical tools can use the wider workspace. Supporting and conflicting evidence retain their own language and limitations.

## Color and shape

Warm paper and near-black ink support long reading. Deep green marks actions and citations, amber flags uncertainty, and oxide marks failures or conflicting evidence. Dark mode uses warm charcoal and muted surfaces. Graph categories retain distinguishable colors and explicit textual labels. Color alone never defines a scientific relationship.

Inputs and buttons have 4px corners; necessary structural panels use 6px. Prose and reference sections generally have no surrounding panel. There are no decorative shadows, gradients, hover lifts, or background motion.

## Evidence and figures

Numbered citations open a source drawer containing the relevant passage or curated evidence note, metadata, context, identifiers, and provenance. Missing metadata stays unknown. The native dialog makes the background inert; while the document has focus, keyboard focus stays within the drawer. Browser chrome remains reachable through native Tab behavior. Closing the drawer returns focus to the citation. A reference number identifies one record throughout a result.

A provisional source-link figure is labeled as a connection to source material, not a discovered causal mechanism. Curated pathways retain their causal-status and polarity labels. The full evidence map is an optional workbench with filters, a canvas, an inspector, and a textual alternative. Numerical tools remain lazy-loaded and retain their submitted-input snapshots and explicit model assumptions.

## Responsive behavior and accessibility

Reading order survives the move to one column. Long identifiers wrap, tables scroll within their own region, and the graph resizes to its canvas. The mobile graph uses a 380px canvas and points to zoom and the text version; the posterior table has a keyboard-focusable region and a cue for hidden interval columns. Visible focus, input labels, disclosure state, native dialog behavior, and reduced-motion preferences are part of the implementation rather than decorative additions. Screenshot and keyboard checks are recorded in the design audit; they are not a claim of complete accessibility certification.

Standalone HTML reports use Georgia and system sans-serif fallbacks, avoiding network dependencies in an exported document. Their evidence content, immutable snapshots, and scientific caveats are unchanged by the report styles.

## Maintenance decisions

Keep domain models, network boundaries, lazy imports, chart measurement, and report caching because they protect real behavior. Remove dead CSS, the obsolete interpretation client, and constant presentation props. A small UTC date formatter replaces inconsistent formatting; saved investigations also display time to distinguish snapshots of the same question. Comments explain the remaining scientific, browser, accessibility, and caching constraints; they do not narrate JSX.
