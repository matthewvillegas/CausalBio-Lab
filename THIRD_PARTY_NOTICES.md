# Third-party notices

CausalBio Lab's original code and documentation use [Apache-2.0](LICENSE); the project copyright notice is in [NOTICE](NOTICE). That license does not relicense papers, database records, dependencies, or fonts. This inventory describes the material used here, not a legal certification of every possible redistribution or deployment.

## Fonts and interface assets

- **Newsreader**, the Newsreader Project Authors / Production Type: SIL Open Font License 1.1. The [full notice](apps/web/public/licenses/newsreader-OFL.txt) is retained from the [Google Fonts distribution](https://github.com/google/fonts/blob/main/ofl/newsreader/OFL.txt).
- **IBM Plex Sans and IBM Plex Mono**, IBM Corp.: SIL Open Font License 1.1. The [full notice](apps/web/public/licenses/ibm-plex-OFL.txt) is retained from [IBM Plex](https://github.com/IBM/plex/blob/master/LICENSE.txt).

Next.js downloads font files during the build and serves them with the application. No font binaries are checked into this repository. The retained notices are also served at `/licenses/newsreader-OFL.txt` and `/licenses/ibm-plex-OFL.txt` in a normal Next.js build. Preserve them when redistributing a build. The wordmark and interface are project assets; there is no third-party icon pack, stock illustration, or copied website template in the public source tree.

Screenshots are captures of this application. Their interface rendering is project documentation; visible source titles, metadata, and passages retain their original attribution and terms. A screenshot is not evidence that a source endorses the application or its interpretation.

## Numerical and adapter fixtures

| Material                                | Use and attribution                                                                                                                                                                                                                                                                                                                                                               |
| --------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Stan Bernoulli diagnostic columns       | Small numerical fixture for independent R-hat/ESS checks. BSD 3-Clause; source commit, digest, transformation and expectations appear in the [fixture provenance](packages/causalbio-core/tests/fixtures/README.md), with the [complete Stan license](packages/causalbio-core/tests/fixtures/STAN-LICENSE.md). No Stan implementation is vendored.                                |
| Europe PMC abstract fixture             | Dinç et al., _Medicina_ (2025), DOI [10.3390/medicina61112035](https://doi.org/10.3390/medicina61112035), copyright the authors, CC BY 4.0. Original abstract and selected response metadata are retained for offline contract tests; attribution and the permission source are in the [adapter fixture notes](packages/causalbio-core/tests/fixtures/source_adapters/README.md). |
| PubMed fixture                          | Small ESearch/ESummary citation-response examples from NCBI/NLM; source IDs are retained. They do not include full papers or abstract text. See [NCBI's policies](https://www.ncbi.nlm.nih.gov/home/about/policies/).                                                                                                                                                             |
| UniProt fixture and peptide annotations | UniProt Consortium, [CC BY 4.0](https://www.uniprot.org/help/license). The small adapter fixture and known-peptide registry retain accession/source links; registry annotations select and organize information rather than reproduce the database. See [UniProt citation guidance](https://www.uniprot.org/help/publications).                                                   |

Curated biological packs contain cited metadata and project curation/interpretation, with no verbatim `supporting_excerpt` text in the current two packs. Synthetic inference data are generated numerical examples, explicitly labeled as such. Local caches, session databases, response dumps, and generated reports are excluded from the public tree.

## Published tendon screenshots

The October 5, 2026 tendon-recovery screenshots display selected abstract passages from the following works. Each uses [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); passages are selected and formatted by CausalBio, and are not complete articles. Original sources are linked in the application and below. The license references were checked in the respective Europe PMC full-text XML permission elements during this release pass.

1. Guan L, Zhang W, Wang H, Zhang Y, Sun J, Lu J. “Effects of Mechanical Loading on the Structure and Function of the Achilles Tendon: From Homeostatic Adaptation to Pathological Degeneration.” _Journal of Functional Morphology and Kinesiology_ (2026). Copyright 2026 the authors. DOI [10.3390/jfmk11030273](https://doi.org/10.3390/jfmk11030273); [permission record](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC13397875/fullTextXML).
2. Tang Y, Alhaskawi A, Ruan B, Yuan Z. “Recent advances in tendon redox biology: the interplay of oxidative stress, calcium signaling, and antioxidant defence mechanisms.” _Frontiers in Pharmacology_ (2026). Copyright 2026 Tang, Alhaskawi, Ruan and Yuan. DOI [10.3389/fphar.2026.1752491](https://doi.org/10.3389/fphar.2026.1752491); [permission record](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC13083024/fullTextXML).
3. Wang I, Owens BD, Trivedi J. “From Degeneration to Regeneration: The Evolving Landscape of Cell-Based Tendon Repair.” _Cells_ (2026). Copyright 2026 the authors. DOI [10.3390/cells15161483](https://doi.org/10.3390/cells15161483); [permission record](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC13510503/fullTextXML).

Live retrieval can return different material later. Check the rights of newly selected passages before replacing public demo assets. Retrieval through [Europe PMC](https://europepmc.org/help) or [PubMed](https://www.ncbi.nlm.nih.gov/home/about/policies/) does not make all article text freely redistributable. Do not bundle full articles or unreviewed response caches.

## Additional demo-video source material

The October 8, 2026 walkthrough also displays a selected abstract passage from Love RJ, Sheridan J, Funk C, Young JL, “Management of Musculoskeletal Injuries with an Inflammatory Damage-Associated Molecular Pattern (DAMP) Etiology,” _Pain and Therapy_ 15, 1249–1279 (2026), DOI [10.1007/s40122-026-00880-5](https://doi.org/10.1007/s40122-026-00880-5). Copyright © His Majesty the King in Right of Canada, as represented by the Minister of National Defence 2026.

This passage is licensed under [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/), as stated by the [publisher](https://link.springer.com/article/10.1007/s40122-026-00880-5#rightslink) and the [Europe PMC permission record](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC13624240/fullTextXML), checked October 8, 2026. CausalBio selected and reformatted the passage for this noncommercial project demonstration. Its noncommercial restriction remains in effect; the project's Apache-2.0 license does not grant commercial reuse rights to that passage. Preserve this attribution and license notice when sharing the recording, and assess any different intended use under the source terms.

The recording also shows the title of Zhu S et al., “Antifibrotic hydrogel strategies for scarless tissue regeneration: mechanisms, design, and application,” _Bioactive Materials_, DOI [10.1016/j.bioactmat.2026.09.019](https://doi.org/10.1016/j.bioactmat.2026.09.019). The source's [permission record](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC13599580/fullTextXML) states CC BY-NC-ND 4.0; the reviewed frame shows citation metadata, not an adapted article passage. Neither source endorses CausalBio's interpretation.

## Software dependencies

Dependencies are installed from the declared manifests, rather than copied into the source tree. The release audit inspected installed direct-runtime package metadata:

| Packages                                                                           | Declared license family                                                     |
| ---------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| Next.js, React, React DOM, Cytoscape.js, Recharts; concurrently development runner | MIT                                                                         |
| FastAPI, Pydantic, pydantic-settings, SQLAlchemy                                   | MIT                                                                         |
| HTTPX, NetworkX, Uvicorn; SciPy's principal project license                        | BSD 3-Clause                                                                |
| NumPy                                                                              | BSD 3-Clause, with additional bundled-component notices in its distribution |

Authoritative versions are in [pyproject.toml](pyproject.toml), [the web manifest](apps/web/package.json), [the root manifest](package.json), and [pnpm-lock.yaml](pnpm-lock.yaml). Installed distributions retain their complete license files, including transitive and compiled-library notices. This table is not a substitute for those files. Preserve relevant dependency licenses when distributing wheels, containers, or built bundles; this pass validates a public source repository, not every downstream packaging format.
