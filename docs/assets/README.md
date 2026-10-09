# Publication assets

The README deliberately selects six 1440×1000 light-mode images from the October 5, 2026 production review. They show the implemented interface, not a design mockup. The full viewport/state matrix remains local; its [review record](design/review-record.json) is public.

| File                         | Purpose                                                        |
| ---------------------------- | -------------------------------------------------------------- |
| `landing.png`                | Question workspace and useful example investigations           |
| `live-tendon-overview.png`   | Provisional summary with source citations and cache context    |
| `citation-drawer.png`        | Exact passage, publication metadata, context, and provenance   |
| `focused-pathway.png`        | Selected curated pathway with scientific relationship labels   |
| `pathway-simulation.png`     | Educational model controls, trajectory and baseline comparison |
| `bayesian-demonstration.png` | Synthetic model estimates, uncertainty and diagnostic context  |

Other captured images remain ignored local review material. No application screenshot contains a personal browser profile, filesystem path, credential, or patient record. Source authors are publication metadata. See [third-party notices](../../THIRD_PARTY_NOTICES.md) for the selected CC BY passages, database terms, fonts, and asset ownership boundaries.

## Social preview

`social-preview.png` is a 1280×640 publication graphic generated from the actual memory pack's entity labels. Its short pathway explicitly notes animal evidence and indirect general-human applicability. It is not an additional scientific result.

With the production app running, execute from `apps/web`:

```powershell
node scripts/render-social-preview.mjs
```

## Recording

The reviewed [production walkthrough](demo-walkthrough.mp4) was recorded October 8, 2026: 71.92 seconds, 1440×1000, 25 fps, H.264, 5.30 MB, with no audio. Read the [caption transcript](../demo-transcript.md). The MP4 preserves the captured timing; no wait was shortened. The script completed with zero browser page errors. Seven representative frames were inspected, including the cached-source date and scientific warnings. The social preview was also rendered and visually inspected on October 8.

The video contains a selected CC BY-NC 4.0 paper passage. Its noncommercial restriction remains in force separately from the project's Apache license; see the [video source attribution](../../THIRD_PARTY_NOTICES.md#additional-demo-video-source-material) before redistribution.

The [demo script](../demo-script.md) describes narration and a suggested owner-recorded walkthrough. `apps/web/scripts/record-demo.mjs` additionally records the real browser flow with explanatory captions, cached evidence, normal timing, and no audio. It requires a previously reviewed cached tendon investigation in the local service; it does not inject fake source responses. Raw video and timing records go to ignored `artifacts/demo/` for inspection before publication.

Run it from `apps/web` while the API and production app are running:

```powershell
node scripts/record-demo.mjs
```

Review the output before hosting, including current source rights and visible content. Do not describe cached retrieval as a fresh search or a scripted walkthrough as a user study. No hosted demo URL is invented here.
