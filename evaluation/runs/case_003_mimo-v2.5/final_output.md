# Pipetly — Extracted Protocols

**Search intent:** Inducing gene editing and regenerating transgene-free tomato plants using CRISPR-Cas9 and Agrobacterium.

**Generated:** 2026-07-14T23:36:26

---

## Rank 1 — Protocol
**Source:** Genome editing and regeneration pipeline for engineering disease resistance in tomato using CRISPR/Cas9.

**DOI:** [10.3389/fpls.2026.1754287](https://doi.org/10.3389/fpls.2026.1754287)

**Relevance score:** 93.0/100

### Protocol Steps

# Protocol: Inducing Gene Editing and Regenerating Transgene-Free Tomato Plants using CRISPR-Cas9 and Agrobacterium

## 1. gRNA Design and Vector Construction

1.1. **Design gRNAs** targeting the tomato susceptibility gene *MLO1*.
    - Identify gRNA sequences using the CRISPOR web tool based on PAM site, GC content, and specificity scores.
    - Evaluate potential off-target sites in silico using the tomato reference genome.
    - Example gRNA sequences to use:
        - gRNA1 Forward: `ATTGGGAGGTACCACGCAATGGTG`
        - gRNA1 Reverse: `AAACCACCATTGCGTGGTACCTCC`
        - gRNA2 Forward: `ATTGCCATGGTTAGCCTTATGGCT`
        - gRNA2 Reverse: `AAACAGCCATAAGGCTAACCATGG`

1.2. **Prepare hybridized oligonucleotides**.
    - Resuspend lyophilized forward and reverse oligonucleotides to 100 µM in sterile water, then dilute to 10 µM.
    - Mix 5 µL of each forward and reverse oligonucleotide (10 µM) with 40 µL of sterile water (5 µM hybridization solution).
    - Denature at 98 °C for 5 minutes, then cool to room temperature (RT).
    - Prepare a 1:100 dilution (50 fmol/µL) for cloning and store at −20°C.

1.3. **Perform Golden Gate cloning into shuttle vectors**.
    - Assemble gRNA1 into pDGE5 and gRNA2 into pDGE8.
    - Prepare a 10 µL cut-ligation reaction:
        - 4 µL dH₂O
        - 3 µL pDGE5 or pDGE8 (20 fmol ≈ 200 ng)
        - 1 µL hybridized oligonucleotides
        - 1 µL 10× ligation buffer
        - 0.5 µL BpiI (10U/µL)
        - 0.5 µL T4 DNA ligase (10U/µL)
    - Thermocycle: 37 °C for 2 min, 16 °C for 5 min (10–30 cycles), followed by 50 °C for 10 min, 80 °C for 10 min.
    - Purify reaction products using spin columns and store at 4 °C.

1.4. **Perform final vector assembly** into binary vector pDGE1.
    - Prepare a 20 µL reaction:
        - 11.5 µL dH₂O
        - 3.5 µL pDGE1 (200 ng)
        - 0.5 µL pDGE5-gRNA1 (20 fmol ≈ 220 ng)
        - 0.5 µL pDGE8-gRNA2 (20 fmol ≈ 220 ng)
        - 2 µL 10× ligation buffer
        - 1 µL BsaI (10U/µL)
        - 1 µL T4 DNA ligase (10U/µL)
    - Use the same thermocycling conditions as in step 1.3.
    - Purify reaction products using spin columns and store at 4 °C.

1.5. **Transform into *E. coli***.
    - Mix 15 µL of electrocompetent *E. coli* DH10b cells with 3 µL of purified ligation product.
    - Electroporate at 2.5 kV (cuvette gap: 0.1 cm).
    - Recover cells in 250 µL of SOC medium at 37°C for 1 hour with shaking.
    - Plate on LB agar containing spectinomycin.
    - Isolate plasmid DNA from single colonies using a miniprep kit.

## 2. *Agrobacterium*-mediated Transformation

2.1. **Introduce purified plasmids into *Agrobacterium***.
    - Electroporate electrocompetent *A. tumefaciens* GV3101 with purified plasmid DNA.
    - Recover cells in SOC medium at 28 °C for 1 hour.
    - Plate on LB agar containing spectinomycin, gentamicin, and rifampicin.
    - Cultivate colonies in selective LB broth and store as glycerol stocks.

## 3. Tomato Regeneration and Selection

3.1. **Prepare and germinate tomato seeds**.
    - Sterilize tomato (S. lycopersicum cv. "Ailsa Craig") seeds.
    - Germinate in vitro on full-strength MS medium with 0.7% agar for 10 days.

3.2. **Perform co-cultivation**.
    - Use cotyledon explants.
    - Co-cultivate with *Agrobacterium* suspension (OD₆₀₀ 0.3–0.5) supplemented with 100 µM acetosyringone (ACS) for 5–10 minutes.
    - Incubate on co-cultivation medium in the dark for 48 hours.

3.3. **Induce shoot regeneration**.
    - Transfer explants to shoot induction medium (TS1):
        - Full-strength MS supplemented with: zeatin (0.5 mg/L), IAA (0.1 mg/L), BAP (0.1 mg/L), kanamycin (10 mg/L), and timentin (200 mg/L).
    - Maintain cultures under a 16-h light/8-h dark photoperiod.
    - Expect shoots to emerge approximately 2 weeks after co-cultivation; maintain on TS1 for ~7 weeks.

3.4. **Induce rooting and acclimatization**.
    - Transfer regenerated shoots to half-strength MS rooting medium supplemented with IBA.
    - Acclimatize plantlets in soil under controlled growth chamber conditions (23 °C, long-day photoperiod).

## 4. Molecular Screening and Genome Editing Validation

4.1. **Extract genomic DNA** from regenerated plants.
    - Use a modified Shorty DNA extraction protocol.
    - Assess DNA quality using agarose gel electrophoresis.

4.2. **Perform PCR confirmation of CRISPR/Cas9 integration**.
    - Use kanamycin-specific primers:
        - Forward: `CTTCCCGCTTCAGTGACAAC`
        - Reverse: `TTGGGTGGAGAGGCTATTCG`
    - Prepare 25-µL PCR reaction per sample:
        - 12.5 µL Red Mix
        - 0.5 µL forward primer
        - 0.5 µL reverse primer
        - Nuclease-free dH₂O to volume
        - 1 µL template DNA
    - Use thermocycling conditions: 95°C for 1 min; 30 cycles of 95°C for 15 s, 60°C for 15 s, 72°C for 10 s; 72°C for 5 min.

4.3. **Detect targeted mutations** via PCR and Sanger sequencing.
    - Amplify genomic regions flanking gRNA target sites using:
        - Forward: `ATGATCAGTGGAGGCATGCT`
        - Reverse: `GGAGTTGGGTAAGGAGTTGGA`
    - Perform Sanger sequencing on amplified products.
    - Analyze sequence traces using DSDecodeM to determine indel patterns and mutation frequencies.
    - Further quantify indel frequencies using TIDE analysis to determine mutation efficiencies.

4.4. **Evaluate predicted protein consequences**.
    - Use the ExPASy Translate tool to translate edited alleles and identify frameshift mutations and premature stop codons.

## 5. Key Workflow Outcomes and Best Practices

5.1. **Expected timeline and outcomes**.
    - Shoot regeneration occurs within 2–3 weeks post-transformation.
    - Rooted plantlets are ready for acclimatization in 6–8 weeks.
    - Editing efficiencies typically range from 40% to 70%.
    - Homozygous or biallelic T₀ plants displaying frameshifts may be obtained.
    - Transgene-free edited lines can be obtained in subsequent generations by segregation.

5.2. **Adhere to best practices**.
    - Select gRNAs with high predicted efficiency and minimal off-target effects.
    - Maintain strict aseptic technique during tissue culture.
    - Include wild-type (WT) and empty vector controls at all stages.
    - Consider whole-genome sequencing for comprehensive off-target analysis if required.

5.3. **Troubleshooting guide**.
    - **gRNA cloning (low ligation efficiency)**: Verify enzyme activity; increase ligation time or temperature cycles.
    - **E. coli transformation (no colonies)**: Use freshly prepared competent cells; ensure correct electroporation parameters.
    - **Agrobacterium transformation (no growth)**: Confirm antibiotic stock concentrations; recheck plasmid integrity.
    - **Shoot regeneration (poor induction)**: Optimize Zeatin/IAA/BAP ratios; ensure 48 h dark co-cultivation.
    - **Shoot regeneration (high contamination)**: Use 70% ethanol and bleach sterilization for seeds; work in laminar flow cabinet.
    - **Low editing efficiency**: Redesign gRNA to target exonic conserved regions; verify Cas9 expression with RT-PCR.
    - **Chimerism in T₀ plants**: Screen T₁ generation for stable, vector-free lines.
    - **No root formation**: Adjust IBA concentration; use fresh media; check for latent *Agrobacterium*.

**Citations**: Materials and methods adapted or cited from [{O'Leary et al., 2024}](https://dog.org/), [{Concordet and Haeussler, 2018}](https://doi.org/), [{Ordon et al., 2017}](https://doi.org/), [{Stuttmann et al., 2021}](https://doi.org/), [{Edwards et al., 1991}](https://doi.org/), and [{Hsu et al., 2013}](https://doi.org/).

## Rank 2 — Protocol
**Source:** Optimization of Agrobacterium-mediated transformation of commercial heirloom tomato cultivars to develop novel traits via CRISPR/Cas9 genome editing.

**DOI:** [10.1007/s00425-026-05024-9](https://doi.org/10.1007/s00425-026-05024-9)

**Relevance score:** 85.0/100

### Protocol Steps

### Protocol: Inducing Gene Editing and Regenerating Transgene-Free Tomato Plants using CRISPR-Cas9 and Agrobacterium

**1. Plant Material and Growth Conditions**
1.1. Surface sterilize tomato seeds with 70% ethanol for 30 seconds, then with 2% sodium hypochlorite solution for 10 minutes.
1.2. Wash seeds 5–6 times with sterile distilled water.
1.3. Place seeds on half-strength Murashige and Skoog (½ MS) medium in sterile glass jars.
1.4. Germinate seeds in a growth chamber at 25°C, 50% humidity, under long-day conditions (16-h light/8-h dark) with white LED light (~200 µmol/m² s⁻¹).

**2. Guide RNA (gRNA) Design**
2.1. Select published gRNA sequences targeting the coding sequences of *Br* (Solyc01g066980) and *SP5G* (Solyc05g053850) [Soyk et al. 2017; Lee et al. 2022].
2.2. Confirm gRNA specificity by BLAST against the Heinz genome (SL4.0) in Solgenomics.
2.3. Synthesize gRNAs as primers from an external vendor.

**3. Vector Construction**
3.1. Assemble vectors using the MoClo Golden Gate cloning system.
3.1.1. Sub-clone the NPTII gene from pICSL7004 (Addgene #50334) into the Level 1 (L1) vector pICH47732 to create pTL0038.
3.1.2. Clone pTL0038 and pICH47742-35S:Cas9 (Addgene #49771) into the binary backbone pAGM4723 to create the Level 2 (L2) vector pTL0047.
3.1.3. For each gRNA, perform PCR with a primer containing the gRNA sequence using plasmid pICH86966::AtU6p::gRNA_PDS (Addgene #46966) as template.
3.1.4. Clone each gRNA PCR product into an L1 vector.
3.1.5. To assemble pTL0151, combine pTL0038, pICH47742-35S:Cas9, the gRNA L1 vectors, and the binary L2 vector pAGM4723.
3.1.6. To assemble pTL0153, combine pTL0038, an L1 vector containing the GRF4-GIF1 chimeric gene under the parsley UBIQUITIN promoter, pICH47742-35S:Cas9, and the *Br* and *SP5G* L1 gRNA vectors.
3.1.7. Confirm all vectors by enzyme restriction and whole-plasmid sequencing.

**4. Agrobacterium-Mediated Plant Transformation**
4.1. Introduce binary vectors into competent *Agrobacterium tumefaciens* strain GV3101 via freeze-thaw method.
4.2. Streak transformed Agrobacterium on LB plates with kanamycin (Kan), rifampicin (Rif), and gentamicin (Gent) (50 mg/L each). Incubate at 28°C for 36–48 hours.
4.3. Inoculate a single colony into 15 mL LB medium with 50 mg/L Kan. Grow at 28°C, 220 rpm for 16 hours.
4.4. Centrifuge culture, discard supernatant, and resuspend pellet in MS-0.2% medium (4.3 g/L MS salts, 2% sucrose, 100 mg/L myo-inositol, pH 5.8) to an OD₆₀₀ of 0.6.
4.5. **Plant Material Preparation:** Harvest cotyledons from 8-day-old seedlings. Cut cotyledons into 1 cm sections.
4.6. Place explants adaxial side down on 2Z preculture medium [4.3 g/L MS salts, 2% sucrose, 100 mg/L myo-inositol, pH 6.0, 5.2 g/L TC Gel; after autoclaving add 2 mL/L *trans*-zeatin stock] and incubate at 25°C for 24 hours.
4.7. Incubate explants with the Agrobacterium suspension for 5 minutes.
4.8. Remove explants to sterile paper towels, then place adaxial side down on fresh 2Z preculture medium.
4.9. Co-cultivate plates in the dark at 25°C for 48 hours.
4.10. Transfer explants adaxial side up to 2Z selection medium [same as 2Z preculture medium; after autoclaving add *trans*-zeatin, 3.5 mL/L timentin stock, and 200 mg/L Kan].
4.11. Culture under white LEDs (16-h light/8-h dark, 200 µmol/m² s⁻¹) at 25°C and 50% humidity. Transfer every 2 weeks to fresh 2Z selection medium until shoots appear.
4.12. When shoots are >2 cm and include a node, excise and transfer to plastic containers with selective rooting medium (4.3 g/L MS salts, 30 g/L sucrose, 1 mL/L modified Nitsch vitamins, pH 6.0, 8 g/L agar; after autoclaving add 3.5 mL/L timentin stock, 200 mg/L Kan, 0.5 mg/L IBA, and 0.5 g/L activated charcoal).

**5. Rooting Optimization**
5.1. Transfer excised shoots to rooting media containing 0.5 mg/L IBA and 0.5 g/L activated charcoal.
5.2. Place containers in a plant growth rack with ambient lighting (6–9 µmol/m² s⁻¹) at 22–25°C.
5.3. Monitor for root development, which should occur within 7 days.

**6. Molecular Characterization**
6.1. **DNA Extraction:** Collect cotyledon tips into 96-well plates with a steel bead.
6.2. Homogenize tissue using a Genogrinder.
6.3. Add 350 µL lysis buffer and 50 µL 10% SDS. Incubate at 65°C for 25 minutes.
6.4. Add 400 µL chloroform:isoamyl alcohol (24:1), vortex, and centrifuge at 4,000 rpm for 25 minutes.
6.5. Transfer 120 µL of upper phase to a new PCR plate, mix with an equal volume of isopropanol, and centrifuge at 4,000 rpm for 25 minutes.
6.6. Wash pellet with 70% ethanol, centrifuge at 4,000 rpm for 10 minutes, air-dry for 10–20 minutes.
6.7. Elute DNA in DNase-free water with 0.05 µL RNase (10 mg/mL) per 50 µL water. Incubate at 65°C for 30 minutes.
6.8. **Genotyping:** Use specific primers for *Br* and *SP5G* target regions. Perform PCR: 95°C for 3 min; 30 cycles of 95°C for 30 s, annealing for 30 s, 72°C for 30 s.
6.9. Analyze products by gel electrophoresis on 1% agarose gels.
6.10. Select plants showing edits and screen subsequent generations for absence of transgene to obtain transgene-free lines.

### Inherited References


These are references cited by this protocol that were resolved.
- **fast-track DNA extraction protocol**

  Extracted from: [10.4161/bbug.3.1.18223](https://doi.org/10.4161/bbug.3.1.18223)
- **fast-track DNA extraction protocol**

  Extracted from: [10.1101/pdb.prot4666](https://doi.org/10.1101/pdb.prot4666)
- **fast-track DNA extraction protocol**

  Extracted from: [10.1007/978-1-4939-8778-8_16](https://doi.org/10.1007/978-1-4939-8778-8_16)
- **fast-track DNA extraction protocol**

  Extracted from: [10.21769/p1516](https://doi.org/10.21769/p1516)

---

## Rank 3 — Protocol
**Source:** CRISPR/Cas9-Targeted Gene Editing of Allergenic Profilin-Encoding Lyc e1 in Tomato Fruit

**DOI:** [10.3390/plants14243837](https://doi.org/10.3390/plants14243837)

**Relevance score:** 85.0/100

### Protocol Steps

# Protocol: Inducing Gene Editing and Regenerating Transgene-Free Tomato Plants Using CRISPR-Cas9 and Agrobacterium

## 1. Plant Material and Seed Germination
1. Use tomato cv. ‘Micro-Tom’ seeds.
2. Surface-sterilize seeds:
   - Immerse in 70% (v/v) ethanol for 1 minute.
   - Transfer to sodium hypochlorite solution (1% v/v) for 30 minutes.
   - Rinse five times with sterile distilled water.
3. Inoculate sterilized seeds onto half-strength MS solid medium supplemented with 3% (w/v) sucrose and 0.8% (w/v) agar (pH 5.8).
4. Grow under controlled conditions:
   - Photoperiod: 16 h light / 8 h dark.
   - Temperature: 25 °C.
   - Relative humidity: 70–80%.
   - Light intensity: 98–117 μmol·m⁻²·s⁻¹ (cool-white fluorescent lamps).
5. Use one-week-old seedlings for protoplast isolation.

## 2. sgRNA Design and Synthesis
1. Identify conserved target region in *Lyc e1.01* and *Lyc e1.02* genes using CRISPRdirect tool (https://crispr.dbcls.jp/).
2. Generate sgRNA template by PCR amplification, incorporating a T7 promoter sequence.
3. Perform in vitro transcription using T7 RNA polymerase.
4. Treat transcription product with RNase-free DNase I at 37 °C for 15 minutes to remove residual DNA templates.
5. Purify RNA using RNeasy MinElute Cleanup Kit.
6. Assess concentration and integrity of purified sgRNA:
   - Use NanoDrop spectrophotometer.
   - Confirm by 2% agarose gel electrophoresis.

## 3. Protoplast Isolation and Transformation
1. Cut cotyledons from one-week-old tomato seedlings into strips (~2 mm).
2. Digest strips in enzyme solution containing:
   - 1.2% Viscozyme®
   - 0.6% PectinEX®
   - 0.6% Celluclast®
   - 0.4 M D-Mannitol
   - 8 mM calcium chloride
   - 0.5 mM MES solution (pH 5.7) [{DOI:10.1093/plphys/kiac022}](https://doi.org/10.1093/plphys/kiac022).
3. Incubate overnight at 25 °C in the dark [{DOI:10.1093/plphys/kiac022}](https://doi.org/10.1093/plphys/kiac022).
4. After digestion, dilute mixture in W5 solution (154 mM NaCl, 125 mM CaCl₂, 5 mM KCl, 2 mM MES, 5 mM glucose).
5. Filter through a 70-μm cell strainer.
6. Centrifuge at 360 × g for 3 minutes to collect protoplasts [{DOI:10.1093/plphys/kiac022}](https://doi.org/10.1093/plphys/kiac022).
7. Resuspend protoplasts in W5 solution and incubate on ice for 30 minutes.
8. Assemble ribonucleoprotein (RNP) complexes:
   - Incubate Cas9 protein with sgRNA at a molar ratio of 1:3.
9. Deliver RNP complexes into protoplasts via PEG–Ca²⁺–mediated transfection.
10. Monitor transformation efficiency using a GFP-expressing plasmid.
11. Observe green fluorescence under a fluorescence microscope 24 hours after transformation.

## 4. Vector Construction and Stable Transformation
1. Use CRISPR/Cas9 vector pKI1.1R (Addgene plasmid #85808) with RPS5A-driven Cas9 and AtU6.26-driven sgRNA cassette.
2. Clone sgRNA into the AarI site.
3. Verify recombinant vectors by Sanger sequencing.
4. Transform recombinant vectors into *Agrobacterium tumefaciens* GV3101 (C58C1 Rif^R, pMP90RK) competent cells.
5. Prepare *Agrobacterium* suspension at optical density (OD600) of 0.5.
6. Infect tomato cotyledon explants with *Agrobacterium* suspension.
7. Culture explants on MS medium supplemented with:
   - 3 mg/L 6-benzylaminopurine.
   - 0.2 mg/L indole-3-acetic acid.
   - 10 mg/L Hygromycin B (for selection of transformed calli).
   - 500 mg/L cefotaxime sodium (to suppress residual *Agrobacterium*).
8. Regenerate shoots.
9. Root shoots and transfer to soil:
   - When shoots reach ~5 cm height, transfer to rooting (RT) medium containing:
     - 4.3 g/L MS salts, 30 g/L sucrose, 100 mg/L inositol, Nitsch vitamins, 0.05 mg/L folic acid, pH 5.8, 0.8% agar.
     - 50 mg/L kanamycin, 125 mg/L cefotaxime, 250 mg/L carbenicillin [{DOI:10.1007/s00299-012-1358-1}](https://doi.org/10.1007/s00299-012-1358-1).
   - Rooted plants are transferred to soil and grown to maturity [{DOI:10.1007/s00299-012-1358-1}](https://doi.org/10.1007/s00299-012-1358-1).

## 5. Genotyping and Western Blotting
1. Extract genomic DNA from young tomato leaves using the standard CTAB method.
2. Perform PCR:
   - Confirm presence of the Cas9 transgene.
   - Amplify target genomic regions for mutation analysis.
3. Subject PCR products to Sanger sequencing.
4. Analyze chromatograms for mutation profiles using the ICE CRISPR Analysis Tool (https://ice.editco.bio/#/).
5. Extract total protein from freeze-dried tomato fruit tissues using NP-40 Lysis Buffer.
6. Perform Western blotting:
   - Primary antibody: anti-profilin 2 (1:2000 dilution, Cat#PHY2385A).
   - Secondary antibody: goat anti-rabbit IgG H&L, HRP-conjugated (1:10,000 dilution, Cat# PHY6000).
7. Verify equal protein loading with Ponceau S staining prior to immunodetection.

## 6. Off-Target Analysis
1. Predict off-target sites using CRISPR-P 2.0 (http://crispr.hzau.edu.cn/CRISPR2/).
2. Select candidate site with highest homology (e.g., Solyc03g083210.3) for experimental validation.
3. Extract genomic DNA from young leaves of all T₀ plants.
4. Amplify predicted off-target genomic region by PCR using site-specific primers flanking the candidate site (≥200 bp on either side).
5. Purify and sequence PCR products by Sanger sequencing.
6. Align chromatograms with wild-type reference sequence using BioEdit software version 7.2.
7. Identify sequence variations indicative of off-target editing.
8. For T₁ generation:
   - Obtain 240 T₁ plants from 12 fertile T₀ lines.
   - Propagate 20 individual plants per line.
   - Screen T₁ plants by PCR to identify Cas9-free plants.
   - Identify homozygous mutated lines (e.g., lines 23-9 and 23-15 with deletions in *Lyc e1.01* and *Lyc e1.02*).

### Inherited References


These are references cited by this protocol that were resolved.
- **standard CTAB method for genomic DNA extraction**

  Extracted from: [10.1093/plphys/kiac022](https://doi.org/10.1093/plphys/kiac022)
- **standard CTAB method for genomic DNA extraction**

  Extracted from: [10.1038/nbt.3389](https://doi.org/10.1038/nbt.3389)
- **standard CTAB method for genomic DNA extraction**

  Extracted from: [10.1007/s00299-012-1358-1](https://doi.org/10.1007/s00299-012-1358-1)

---
