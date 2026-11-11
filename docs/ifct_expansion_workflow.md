# IFCT expansion staging workflow

`data/foods_final.csv` remains the production database. New IFCT candidates must enter through `data/foods_expansion_staging.csv` and must not be merged until source and permission review are complete.

## Required evidence for a verified row

- Exact IFCT food code and food identity from the source.
- Table 1 protein value in g/100 g edible portion.
- Table 8 phenylalanine value in g/100 g protein.
- Exact printed page references for both tables.
- A reproducible conversion to `phe_mg_per_100g`.
- Review of food state and duplicate identity.

The staging validator rejects nutrient values and source references on rows not marked `VERIFIED`. It does not promote rows to production.

## Current leafy-vegetable batch

The seven candidate rows currently carry `SOURCE_REVIEW_REQUIRED` and `PERMISSION_REVIEW_REQUIRED`. Their names and candidate codes were carried forward from the prior project discussion only; the IFCT 2017 source is not present in this workspace, so they are not validated.

## Permission gate

Before incorporating a substantial Table 1/Table 8 extract into the electronic application, obtain and retain written permission from the National Institute of Nutrition (NIN), Hyderabad, or confirm an applicable licence/permission route. Until that evidence is recorded, keep the rows in staging and out of `foods_final.csv`.
