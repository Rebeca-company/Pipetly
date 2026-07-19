# Pipetly — Extracted Protocols

**Search intent:** Generation of transgene-free CRISPR-Cas9 edited tomato plants via Agrobacterium-mediated transformation and regeneration.

**Generated:** 2026-07-14T00:14:39

---

## Rank 1 — Protocol
**Source:** Identification of transgene-free CRISPR edited plants of rice and tomato by monitoring DsRED fluorescence in dry seeds

**DOI:** [10.1101/533034](https://doi.org/10.1101/533034)

**Relevance score:** 95.0/100

### Protocol Steps

### Protocol for Generation of Transgene-Free CRISPR-Cas9 Edited Tomato Plants

#### 1. Vector Construction and Preparation
1.  **Design and Domestication:** Adapt all genetic elements (Level 0 parts) by incorporating flanking BsaI recognition sites and 4 bp standard barcodes, while removing internal BsmBI and BsaI sites [[10.1186/s13007-016-0101-2](https://doi.org/10.1186/s13007-016-0101-2)].
2.  **gRNA Assembly:** 
    1.  Anneal complementary primers (1 μM in water) for 30 minutes at room temperature.
    2.  Perform a BsmBI restriction–ligation reaction using pUPD2 and 75 ng of the level -1 tRNA-scaffold plasmid to assemble guide RNAs on level 0 [[10.1186/s13007-016-0101-2](https://doi.org/10.1186/s13007-016-0101-2)].
3.  **Final Vector Assembly:** Use multipartite BsaI restriction–ligation reactions to assemble the following Transcriptional Units (TUs) into a binary destination plasmid:
    1.  Cas9 TU under the CaMV 35S promoter.
    2.  Multiplexed sgRNA TU under the U6-26 promoter.
    3.  Kanamycin resistance (KanR) selection marker.
    4.  DsRED fluorescent protein TU under the CaMV 35S promoter [[10.1186/s13007-016-0101-2](https://doi.org/10.1186/s13007-016-0101-2)].
4.  **Agrobacterium Preparation:** Transform the final construct into *Agrobacterium tumefaciens* strain LBA 4404. Grow overnight, then dilute to $D_{660} = 0.10–0.15$ in LB medium with 25 mg/L kanamycin. Incubate for 4–5 hours until $D_{660} = 0.20–0.30$. Resuspend bacteria and adjust acetosyringone to 200 µM [[10.1007/s00122-002-0928-y](https://doi.org/10.1007/s00122-002-0928-y)].

#### 2. Plant Transformation and Regeneration
1.  **Seed Sterilization and Germination:** 
    1.  Immerse tomato seeds in 5% (w/v) sodium hypochlorite with 0.1% (v/v) 7X-O-matic for 30 minutes. Rinse three times with sterile deionized-distilled water [[10.1007/s00122-002-0928-y](https://doi.org/10.1007/s00122-002-0928-y)].
    2.  Germinate seeds in darkness on GM medium (MS salts, 1% sucrose, 0.8% agar, pH 5.7). Move to a tissue-culture chamber (24 °C, 16-h light) once radicles emerge [[10.1007/s00122-002-0928-y](https://doi.org/10.1007/s00122-002-0928-y)].
2.  **Explant Preparation and Inoculation:**
    1.  Cut cotyledons from 12–15 day old seedlings transversally. Pre-incubate segments on PCM medium for 2 days in darkness [[10.1007/s00122-002-0928-y](https://doi.org/10.1007/s00122-002-0928-y)].
    2.  Submerge explants in the Agrobacterium inoculum for 8–10 minutes with gentle swirling. Blot dry and transfer to CCM medium for 24–48 hours at 26 °C in darkness [[10.1007/s00122-002-0928-y](https://doi.org/10.1007/s00122-002-0928-y)].
3.  **Selection and Rooting:**
    1.  Wash explants in WM medium (containing 600 mg/L cefotaxime) for 10 minutes. Blot dry and culture on non-selective SIM for 48 hours under light [[10.1007/s00122-002-0928-y](https://doi.org/10.1007/s00122-002-0928-y)].
    2.  Transfer to selective SIM (100 mg/L kanamycin, 300 mg/L cefotaxime). Subculture every 3 weeks until shoots emerge [[10.1007/s00122-002-0928-y](https://doi.org/10.1007/s00122-002-0928-y)].
    3.  Excise shoots and perform a rooting test on selective RM (50 mg/L kanamycin). Retain KanR transgenic lines for G2 seed production [[10.1007/s00122-002-0928-y](https://doi.org/10.1007/s00122-002-0928-y)].

#### 3. Identification of Transgene-Free Mutants
1.  **Fluorescence Screening:** Observe dry G2 seeds under a stereoscope with a DsRED filter. Select lines showing a 3:1 ratio of fluorescent to non-fluorescent seeds.
2.  **Segregation and Growth:** Separate DsRED-negative (non-fluorescent) seeds and grow them in greenhouse conditions.
3.  **Genomic Verification:**
    1.  Extract genomic DNA from leaves of DsRED-negative plants.
    2.  Perform PCR using Cas9-specific primers (F: 5'-ggcggagcaagccaggaggaa-3'; R: 5'-cttgacagccgcccccatcct-3') to confirm the absence of the T-DNA.
    3.  PCR-amplify and sequence the CRISPR-target regions in confirmed DsRED-negative/Cas9-negative plants to identify stable, transgene-free mutations.

### Inherited References


These are references cited by this protocol that were resolved.
- **tomato in vitro transformation protocol**

  Extracted from: [10.1186/s13007-016-0101-2](https://doi.org/10.1186/s13007-016-0101-2)
- **tomato in vitro transformation protocol**

  Extracted from: [10.1007/s00122-002-0928-y](https://doi.org/10.1007/s00122-002-0928-y)

---

## Rank 2 — Protocol
**Source:** Enhancing tomato fruit sweetness by CRISPR/Cas9-mediated SlVIF gene editing

**DOI:** [10.1016/j.plaphy.2026.111270](https://doi.org/10.1016/j.plaphy.2026.111270)

**Relevance score:** 92.0/100

### Protocol Steps

1. **Vector Construction and Cloning**
    1. Design two sgRNAs for *SlVIF* using the Target Design online tool with an on-target score >0.5 and low predicted off-target events.
    2. Amplify the gRNA expression cassette using pCBC-DT1T2 as a DNA template and four primers (Target1-BsF, Target1-F, Target2-BsR, and Target2-R) via PCR.
    3. Set up a Golden Gate restriction-ligation reaction by mixing the purified PCR fragment (T1T2-PCR) and the pKSE402 binary vector with *Bsa* I and T4 Ligase [[10.1186/s12870-014-0327-y](https://doi.org/10.1186/s12870-014-0327-y)].
    4. Incubate the reaction in a thermocycler for 5 hours at 37°C, followed by 5 min at 50°C and 10 min at 80°C [[10.1186/s12870-014-0327-y](https://doi.org/10.1186/s12870-014-0327-y)].
    5. Transform the recombinant product (pKSE402-SlVIF) into *Escherichia coli* DH5α using the heat shock method.
    6. Screen for positive clones on LB medium supplemented with 50 mg/mL kanamycin and validate via PCR and sequencing.

2. **Agrobacterium Transformation and Plant Inoculation**
    1. Transfer the validated pKSE402-SlVIF plasmid into *Agrobacterium* GV3101 using the freeze-thaw method.
    2. Prepare a suspension of the transformed GV3101 and immerse tomato cotyledon explants in the suspension for 15 min.
    3. Transfer explants to MS medium containing 2 mg/L zeatin and co-cultivate in the dark for two days.

3. **Regeneration and Selection of Transgenic Lines**
    1. Transfer explants to MS solid medium supplemented with 2 mg/L zeatin, 200 mg/L timentin, and 75 mg/L kanamycin.
    2. Incubate at 25 °C under a 16-h light/8-h dark photoperiod for 4 weeks to induce adventitious bud differentiation.
    3. Excise regenerated shoots (~2 cm in length) and transfer them to 1/2 MS medium supplemented with 3 mg/L IBA and 100 mg/L timentin for root induction.
    4. Identify T0 transgenic lines via PCR amplification using specific primers 402-F and U626t-R.

4. **Mutant Identification and Transgene-Free Selection**
    1. Extract DNA from PCR-positive T0 plants and amplify the target region using primers VIF-F/R.
    2. Sequence the PCR products to identify and select *SlVIF*-edited homozygous mutants.
    3. Self-pollinate the T0 homozygous mutants to generate T1 progeny.
    4. Screen T1 plants via PCR using Cas9-specific primers (Cas9-F/R); identify individuals lacking the PCR band as Cas9-free homozygous mutants.

### Inherited References


These are references cited by this protocol that were resolved.
- **freeze-thaw transformation of Agrobacterium GV3101**

  Extracted from: [10.1186/s12870-014-0327-y](https://doi.org/10.1186/s12870-014-0327-y)
- **freeze-thaw transformation of Agrobacterium GV3101**

  Extracted from: [10.3791/253](https://doi.org/10.3791/253)
- **freeze-thaw transformation of Agrobacterium GV3101**

  Extracted from: [10.1007/bf00267408](https://doi.org/10.1007/bf00267408)

---

## Rank 3 — Protocol
**Source:** Transgene-Free Genome Editing in Tomato and Potato Plants Using Agrobacterium-Mediated Delivery of a CRISPR/Cas9 Cytidine Base Editor

**DOI:** [10.3390/ijms20020402](https://doi.org/10.3390/ijms20020402)

**Relevance score:** 92.0/100

### Protocol Steps

1. **Preparation of Explants and Inoculation**
    1. Harvest cotyledon segments from 8–12 day-old seedlings of the *Solanum lycopersicum* cv WVA106 cultivar.
    2. Prepare the *Agrobacterium tumefaciens* strain C58 pGV2260 containing the CBE binary vector with *SlALS1* sgRNA.
    3. Inoculate the cotyledon segments using MSO medium supplemented with 0.9 mg/L thiamine, 0.2 mg/L 2–4D, 0.1 mg/L kinetin, and 0.2 mM Acetosyringone [[10.1371/journal.pone.0029595]](https://doi.org/10.1371/journal.pone.0029595).

2. **Selection and Regeneration**
    1. Transfer inoculated cotyledon pieces to regeneration medium (MSO medium with 2 mg/L zeatin) supplemented with 100 mg/L kanamycin and 225 mg/L timentin [[10.1371/journal.pone.0029595]](https://doi.org/10.1371/journal.pone.0029595).
    2. Maintain cultures in a growth chamber at 22°C during the day and 18°C during the night with a 16 h photoperiod [[10.1371/journal.pone.0029595]](https://doi.org/10.1371/journal.pone.0029595).
    3. After one or two weeks of initial kanamycin selection, transfer cotyledon pieces to fresh selective medium containing 40 ng/mL chlorsulfuron.
    4. Subculture the tissues onto fresh chlorsulfuron selective medium every two weeks until buds regenerate.

3. **Elongation and Rooting**
    1. Transplant regenerated buds individually onto elongation medium (MSO medium with MS salts reduced to ½) containing 100 mg/L kanamycin and 225 mg/L timentin [[10.1371/journal.pone.0029595]](https://doi.org/10.1371/journal.pone.0029595).
    2. Continue incubation on elongation medium until plantlets have rooted.

4. **Molecular Screening and Sequencing**
    1. Extract genomic DNA from regenerated plantlets.
    2. Perform PCR analysis using GoTaq® G2 Flexi DNA Polymerase to detect the stable integration of the T-DNA.
    3. Amplify the target locus using GoTaq® G2 Flexi DNA Polymerase for all independent transformation events.
    4. Purify the resulting PCR products.
    5. Perform Sanger sequencing on the purified products to characterize the edited target locus.

### Inherited References


These are references cited by this protocol that were resolved.
- **Agrobacterium-mediated transformation of tomato cotyledon segments**

  Extracted from: [10.1371/journal.pone.0029595](https://doi.org/10.1371/journal.pone.0029595)

---
