# Source adapter fixtures

These responses are used only for deterministic offline adapter contract tests. A successful schema or provenance test does not validate a biological claim.

## Europe PMC

`europepmc_core.json` preserves a selected response from the Europe PMC core search endpoint, with one result, its original abstract, and metadata. The query and response envelope are retained in the file. Retrieved October 2, 2026 UTC; the record's current identifier contract and license were rechecked October 3, 2026 UTC.

- Dinç M, Soydemir ÖC, Bayrak HÇ, Karasu R, Aykaç B, Topcu ME. “Avocado-Soybean Unsaponifiables Enhance Tendon Healing via Anti-Inflammatory and Antioxidant Mechanisms in a Rat Achilles Injury Model.” _Medicina_ 61(11), 2035 (2025).
- [DOI: 10.3390/medicina61112035](https://doi.org/10.3390/medicina61112035)
- [PMID 41303871](https://pubmed.ncbi.nlm.nih.gov/41303871/); [PMC12654124](https://pmc.ncbi.nlm.nih.gov/articles/PMC12654124/)
- Copyright 2025 the authors. [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/).
- License verified from the `permissions` element in [Europe PMC full-text XML](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12654124/fullTextXML). The fixture contains citation metadata and the abstract; full text is not bundled.

This is a rat study. Its abstract is preserved as source material, including the authors' interpretation; it is not an endorsed treatment claim. The adapter does not infer structured species, human relevance, or evidence grade from this text. Runtime extraction separately suppresses operational dosage sentences from displayed claims.

## PubMed and UniProt

The other fixtures exercise the earlier citation/protein adapter contracts: PubMed ESearch/ESummary and UniProtKB search. They retain their source identifiers and are not biological reference datasets. Source responses and annotations remain subject to the original service's terms, independently of the repository's code license.
