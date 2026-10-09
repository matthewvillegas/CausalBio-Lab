# GitHub publishing checklist

The current work prepares a public repository and a first release. It does not create an account, push code, run hosted CI, publish a release, host a video, or establish personal contribution. Review the [public-release audit](public-release-audit.md) before following these steps.

## Repository metadata

**Suggested name:** `CausalBio-Lab`

**Description:**

> Computational biology workbench for source-linked mechanism maps, pathway simulations, and reproducible research.

**Topics:** `computational-biology`, `bioinformatics`, `scientific-computing`, `causal-graphs`, `networkx`, `fastapi`, `nextjs`, `petri-nets`, `bayesian-inference`, `reproducible-research`.

The Bayesian topic refers to the explicit synthetic demonstration. Do not describe arbitrary literature research as Bayesian inference or causal discovery.

**Social preview:** upload the prepared `docs/assets/social-preview.png` (1280 × 640). It shows the wordmark, a concise research-workbench subtitle, and a three-entity excerpt from the curated memory pathway, with its evidence limitation. This is a presentation graphic, not an application screenshot. Confirm the final file and labels before upload.

**Website field:** use the real hosted demo or personal case-study URL only after it exists. Leave it blank until then. Do not use a local development URL as a public demo.

## Owner steps

1. **Create or confirm the repository.** Choose the intended account and visibility. If publishing this existing tree into an empty GitHub repository, avoid generating a competing README/license remotely. Confirm the remote destination before adding it locally.
2. **Review the public tree.** Run `pnpm public:check`, `pnpm docs:check`, `git status --short`, and `git diff --check`. Review filenames, ignored artifacts, images, notices, and generated documentation. Automated scans do not replace inspection.
3. **Review “My contribution.”** Confirm each personal claim in the README and case study. Replace owner-review text with accurate wording or leave the drafts explicitly marked; never publish uncertain authorship as fact.
4. **Review coding-assistant disclosure.** Describe the actual roles of direction, implementation, debugging, testing, and review. Do not claim sole authorship of every algorithm or formal mastery unsupported by your experience.
5. **Commit and push the reviewed source.** Use the truthful initial-import plan below. Verify the destination and final staged diff before pushing. Do not manufacture a development timeline.
6. **Confirm hosted CI.** Open the Actions run and inspect its results on the actual commit. Fix failures; only then describe that commit as passing hosted CI. No passing status badge is included in advance.
7. **Add the description.** Paste the suggested description or an equally accurate short version into the repository's About field.
8. **Add topics.** Select only the implemented subjects listed above. Avoid machine-learning or diagnostic labels.
9. **Add the social preview.** Upload the reviewed 1280 × 640 image in repository settings and check its crop.
10. **Create the first release.** After steps 1–9 and successful CI, publish `v1.0.0 — Public Research MVP` from the tested commit, using [CHANGELOG.md](../CHANGELOG.md). The tag and release date must be real. The prepared source version alone does not prove a release occurred.
11. **Review and host the demo.** Review the local recording, or record a new walkthrough using the [60-second script](demo-script.md), then upload it and add its real hosted URL to the README. Retain the script link in the docs index. Label sped-up or cached retrieval honestly.
12. **Pin the repository.** Select it in your own GitHub profile's pinned repositories after checking the card description and README.
13. **Link the case study.** Add the real GitHub and demo URLs to your personal portfolio and [case-study draft](portfolio-case-study.md). Do not modify unrelated project claims to match this project's methods.
14. **Review application wording.** Keep application and resume wording consistent with your actual contribution, current form limits, and the methods you can explain. Recheck counts against the release's validation record.

## Truthful commit and release plan

The inspected starting repository had no commits or remotes. A single initial import of the reviewed implementation is more truthful than dividing it into fabricated historical milestones. Suggested initial message:

```text
Prepare CausalBio Lab public research MVP
```

After review, these are owner-run commands, not actions already performed. Replace `OWNER` and the repository name with the intended destination. If a remote or commits now exist, inspect them first and adapt instead of overwriting history.

```powershell
git status --short
git add --all
git diff --cached --check
git diff --cached --stat
git diff --cached
git commit -m "Prepare CausalBio Lab public research MVP"
git branch -m main
git remote add origin https://github.com/OWNER/CausalBio-Lab.git
git push -u origin main
```

After remote CI passes, the GitHub **Releases → Draft a new release** form can create tag `v1.0.0` on that tested commit. Use the title **v1.0.0 — Public Research MVP** and the prepared changelog entry, including its limitations. Remove “unreleased” wording only when publication actually happens. Do not backdate the tag or release.

Future commits should represent new work performed at that time, such as `Improve study-context extraction fixtures` or `Refine dense graph labels`. Those are examples of scope and naming, not a claim that such changes have already occurred. No destructive history rewrite is needed.
