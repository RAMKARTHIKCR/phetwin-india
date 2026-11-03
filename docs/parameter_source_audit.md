# Parameter source audit

This is a reference audit for the illustrative model. It does not establish
clinical validity and does not replace review by a metabolic physician,
biochemist, or dietitian.

## Findings

| Parameter or concept | Audit finding | Action |
| --- | --- | --- |
| `target_low_umol_l = 120` | 120 µmol/L is described as a commonly used lower target in the European PKU guideline, with age- and context-specific interpretation. | Retain as an illustrative target; do not present it as universal. |
| `target_high_umol_l = 360` | 360 µmol/L is supported for some age groups and contexts, but target ranges vary by age and pregnancy status. | Retain only as a demo value; the model needs age/context fields before clinical use. |
| Dietary Phe tolerance | Guidelines define tolerance as the intake that maintains blood Phe in an intended range, and emphasize individual determination and monitoring. | Keep `activity_from_tolerance()` as a calibration helper, not a prescription tool. |
| `phe_mg_per_g_protein = 50` | The 50 mg Phe per gram protein exchange convention appears in PKU dietary guidance, but food composition and exchange systems vary. | Keep the value flagged as an assumption in the food workflow. |
| `vd_l_per_kg`, `km_mg_per_l`, `endogenous_input_mg_per_h` | No source was identified that justifies the current demo values for this specific one-compartment model and unit system. | Do not replace the placeholders. |
| `k_alt_l_per_h`, `ka_per_h`, `bioavailability` | These are model-structure assumptions; a source would need to match the chosen compartment, route, and units. | Keep illustrative and test sensitivity only. |

## References

- [GeneReviews: Phenylalanine Hydroxylase Deficiency](https://www.ncbi.nlm.nih.gov/books/NBK1504/)
- [The complete European guidelines for phenylketonuria](https://pmc.ncbi.nlm.nih.gov/articles/PMC5639803/)
- [PKU dietary handbook to accompany PKU guidelines](https://pmc.ncbi.nlm.nih.gov/articles/PMC7329487/)
- [A model of human phenylalanine metabolism in normal subjects and PKU patients](https://pmc.ncbi.nlm.nih.gov/articles/PMC15912/)

The model must not claim that these references validate the current parameter
set. They provide clinical or conceptual context only; parameter replacement
requires a separate unit- and population-specific validation exercise.
