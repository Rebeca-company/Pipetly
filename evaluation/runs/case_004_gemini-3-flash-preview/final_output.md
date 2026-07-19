# Pipetly — Extracted Protocols

**Search intent:** Knockin of the AAVS1 locus in HEK293T cells using Cpf1 and a targeting construct.

**Generated:** 2026-07-18T00:18:35

---

## Rank 1 — Protocol
**Source:** Multiplex Genome Editing of Human Pluripotent Stem Cells Using Cpf1.

**DOI:** [10.21769/bioprotoc.5108](https://doi.org/10.21769/bioprotoc.5108)

**Relevance score:** 95.0/100

### Protocol Steps

1. **Transfection of HEK293T Cells**
    1. Prepare HEK293T cells in one well of a 12-well plate.
    2. Transfect the cells with 0.8 μg of AAVS1-CAGGS-tdTomato targeting vector and 0.4 μg of AsCpf1-AAVS1 plasmid using Lipofectamine 2000 transfection reagent.

2. **Cell Sorting and Initial Selection**
    1. Incubate the cells for 3 days post-transfection.
    2. Sort GFP and tdTomato (tdT) double-positive cells using a FACSAria.
    3. Plate the sorted cells onto a 10 cm culture plate at a density of approximately 2,000 cells per plate.
    4. Apply selection pressure using 2 μg/mL puromycin.
    5. Maintain selection until visible colonies are formed.

3. **Colony Expansion**
    1. Identify individual tdT-expressing colonies.
    2. Mechanically passage individual colonies into separate wells of a 12-well plate.
    3. Expand the clones for downstream analysis.

4. **Genotyping and Validation**
    1. Extract genomic DNA from the expanded clones.
    2. Prepare a PCR reaction using 0.5 μg of genomic DNA and REDTaq PCR Reaction Mix with the following primers:
        *   Primer 495: 5′- TCTCTCTCCTGAGTCCGGACC-3′
        *   Primer 489: 5′-ACTGAGCTCTCAGGCACCGGGCTTGCGG-3′
    3. Perform PCR amplification using the following thermal cycling conditions:
        *   Initial denaturation: 95 °C for 5 min.
        *   35 cycles of: 95 °C for 30 s, 57 °C for 30 s, and 72 °C for 1 min 40 s.
        *   Final extension: 72 °C for 5 min.
    4. Resolve the resulting PCR products on a 1% agarose gel.
    5. Excise DNA bands of the expected size from the gel.
    6. Extract the DNA using a gel purification kit (Omega Bio-tek).
    7. Perform Sanger sequencing on the purified DNA using primer 495 to confirm correct knockin.

### Inherited References


These are references cited by this protocol that were resolved.
- None

---

## Rank 2 — Protocol
**Source:** Multiplex genome editing of human pluripotent stem cells using Cpf1

**DOI:** [10.1101/2022.04.13.488123](https://doi.org/10.1101/2022.04.13.488123)

**Relevance score:** 95.0/100

### Protocol Steps

1. **Vector Preparation**
    1. Digest the bicistronic AsCpf1 backbone vector (containing CMV-driven AsCpf1-T2A-GFP and U6-driven crRNA cassette) using BbsI restriction enzyme.
    2. Anneal a pair of oligonucleotides corresponding to the AAVS1 target site.
    3. Ligate the annealed oligonucleotides into the BbsI-digested backbone vector to generate the AAVS1-specific AsCpf1 plasmid.

2. **Cell Culture and Transfection**
    1. Maintain HEK293T cells in DMEM high glucose medium supplemented with 10% FBS, 1X L-glutamine, 1X MEM-NEAA, and 1X penicillin/streptomycin.
    2. Seed cells into 12-well plates and grow until they reach 60-80% confluence.
    3. Transfect each well with 0.4 µg of the AAVS1-specific AsCpf1 plasmid and 0.8 µg of the AAVS1-CAGGS-tdTomato targeting vector using Fugene 6 transfection reagent according to the manufacturer’s guidelines.

3. **Enrichment and Selection**
    1. Dissociate cells with trypsin 3 days post-transfection.
    2. Sort GFP and tdTomato double-positive cells using a FACSAria flow cytometer.
    3. Plate the sorted cells at a low density of 2000 cells per 10 cm culture plate.
    4. Apply selection pressure using 2 µg/ml puromycin.
    5. Maintain selection until distinct colonies form.

4. **Clone Expansion and Genomic DNA Extraction**
    1. Mechanically passage individual colonies into separate wells of a 12-well plate.
    2. Expand the clones under standard culture conditions.
    3. Purify genomic DNA from expanded clones using the DNeasy Blood & Tissue Kit.

5. **Genotyping and Validation**
    1. Prepare a PCR reaction using 0.5 µg of genomic DNA, primers 495 and 489, and Red Taq polymerase.
    2. Perform PCR amplification using the following thermal cycling conditions:
        1. Initial denaturation: 95 °C for 5 min.
        2. 35 cycles of:
            1. Denaturation: 95 °C for 30 sec.
            2. Annealing: 57 °C for 30 sec.
            3. Extension: 72 °C for 1 min 40 sec.
        3. Final extension: 72 °C for 5 min.

## Rank 3 — Protocol
**Source:** Human T Cells Expressing a CD19 CAR-T Receptor Provide Insights into Mechanisms of Human CD19-Positive β Cell Destruction

**DOI:** [10.1016/j.xcrm.2020.100097](https://doi.org/10.1016/j.xcrm.2020.100097)

**Relevance score:** 65.0/100

### Protocol Steps

1. **Plasmid Construction**
    1. Generate the `AAVS1-AsCpf1` targeting construct (#66) by PCR amplifying the *As-Cpf1* sequence from the `pcDNA3.1-hAsCpf1` template using primers `5′-TAACCGGTCCACCATGGCCCCAAAGAAGAAGCGGAAG-3′` and `5′-GCCTTAATTAATCAGGCATAGTCGGGGACATCATATGGGTATG-3′`.
    2. Clone the resulting PCR product into the `AgeI` and `PacI` sites of the `AAVS1-tdTomato` targeting construct to create a multicistronic plasmid containing `CAGGS:As-Cpf1-2A-GFP` and `U6:sgRNA` cassettes.
    3. Generate the `AAVS1-PDL1` donor construct by PCR amplifying the human *PDL1* coding sequence using primers `5′-TAACCGGTCCAACCATGAGGATATTTGCTGTCTTTATATTC-3′` and `5′-GCCTTAATTAATTACGTCTCCTCCAAATGTGTATCA-3′`.
    4. Clone the *PDL1* PCR product into the `AgeI` and `PacI` sites of the `AAVS1-tdTomato` targeting construct.

2. **Cell Preparation and Electroporation**
    1. Supplement the cell culture medium with 10 μM Rho kinase (ROCK) inhibitor Y-27632 one day prior to electroporation.
    2. Dissociate approximately 10 million cells into a single-cell suspension using Accutase.
    3. Filter the cell suspension through a 40 μm cell strainer.
    4. Wash the filtered cells with medium containing 10 μM Y-27632.
    5. Centrifuge the cells and resuspend the pellet in 800 μl of PBS.
    6. Mix the resuspended cells with 100 μg of `CAGGS-AsCpf1-U6-INS-sgRNA` and 40 μg of the donor construct (`AAVS1-PDL1`).
    7. Transfer the mixture into a 0.4-cm cuvette and incubate on ice for 5 minutes.
    8. Electroporate using a Gene Pulser Xcell System with a single pulse at 250 V and 500 μF.
    9. Incubate the cuvette on ice for 5 minutes immediately following the pulse.

3. **Post-Electroporation Recovery and Selection**
    1. Plate the electroporated cells onto two 6-well plates containing DR4 MEF feeder cells.
    2. Initiate selection 3–4 days post-electroporation by adding medium containing 0.5 μg/mL Puromycin.
    3. Manually pick individual colonies and passage them onto MEF-coated 12-well plates.
    4. Expand the colonies and verify correct integration at the AAVS1 locus via PCR genotyping and Southern blotting.
    5. Confirm transgene expression through PDL1 cell surface staining.

### Inherited References


These are references cited by this protocol that were resolved.
- None

---
