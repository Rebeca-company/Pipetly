# Pipetly — Extracted Protocols

**Search intent:** Measurement of ALPK1 kinase activity using a radiometric assay.

**Generated:** 2026-07-14T21:50:36

---

## Rank 1 — Protocol
**Source:** Quantitative Measurement of the Kinase Activity of Wildtype ALPK1 and Disease-Causing ALPK1 Mutants Using Cell-Free Radiometric Phosphorylation Assays

**DOI:** [10.21769/BioProtoc.5124](https://doi.org/10.21769/BioProtoc.5124)

**Relevance score:** 98.0/100

### Protocol Steps

### Measurement of ALPK1 Kinase Activity Using a Radiometric Assay

**Day 1-2: Transient Expression of FLAG-tagged ALPK1 Constructs**
1.  Plate 15 million ALPK1 KO HEK-Blue cells (≤30 passages) onto each of three 15 cm dishes in 20 mL culture media.
2.  Incubate for 18 hours at 37°C with 5% CO₂ until ~90% confluency.
3.  For each dish, prepare transfection complexes by mixing:
    *   150 µL Lipofectamine 2000 in 600 µL OptiMEM.
    *   60 µg of plasmid (empty vector, *pcDNA5-FRT/TO-FLAG-ALPK1*, or *pcDNA5-FRT/TO-FLAG-ALPK1[S277F]*) in 600 µL OptiMEM.
    *   Combine the Lipofectamine and plasmid mixtures and incubate for 10 minutes at room temperature.
4.  Add the transfection complexes dropwise to the corresponding cell dish and incubate for 4 hours.
5.  Aspirate the media and replace with 15 mL fresh culture media. Incubate for 20 hours.

**Day 3: Preparation and Normalization of Cell Extracts**
1.  Detach cells by pipetting culture media. Centrifuge at 800×g for 5 min at room temperature.
2.  Wash the cell pellet twice with 15 mL room-temperature PBS, aspirating after each centrifugation.
3.  Lyse the pellet in 1 mL ice-cold lysis buffer on ice. Transfer to a 1.5 mL tube.
4.  Centrifuge at 18,000×g for 20 min at 4°C. Transfer the supernatant (cell extract) to a new tube on ice.
5.  Determine protein concentration using the Bradford Protein Assay Kit. Dilute extracts to 2 mg/mL with ice-cold lysis buffer.
6.  Normalize ALPK1 expression levels:
    *   Immunoprecipitate 0.2 mg of each extract with 15 µL anti-FLAG M2 resin for 1 hour at 4°C on a rotating wheel.
    *   Wash resin: 3x with 1 mL ice-cold salt wash buffer, 2x with 1 mL ice-cold wash buffer.
    *   Elute with 20 µL LDS sample buffer (1×) with 2.5% (v/v) 2-mercaptoethanol at 75°C for 5 min.
    *   Analyze 10 µL by SDS-PAGE. Stain with InstantBlue, destain, and quantify FLAG-ALPK1 band intensity relative to WT.
    *   Dilute extracts using empty vector lysate to match the ALPK1 concentration of the lowest-expressing sample.
7.  Aliquot 0.5 mL of each normalized extract, snap-freeze, and store at -80°C.

**Days 4-5: Determination of Linear Rate Conditions for WT ALPK1**
1.  Perform immunoprecipitation for the time-course using 1 mg of WT FLAG-ALPK1 lysate and 300 µL of anti-FLAG resin slurry (washed as in Day 3).
2.  Resuspend the dry immunoprecipitated resin in 350 µL ice-cold reaction buffer. Aliquot 32.5 µL (containing ~15 µL resin) into 18 tubes on ice.
3.  To each tube, add:
    *   2.5 µL of 1 mg/mL GST-TIFA (substrate) or reaction buffer (no substrate control).
    *   2.5 µL of reaction buffer (without activator) or 100 µM ADP-heptose (activator).
4.  Start reactions by adding 2.5 µL radioactive ATP solution at 20-second intervals. Incubate on a thermomixer at 30°C, 1300 rpm.
5.  Terminate reactions at 0 (before ATP addition), 5, 10, 20, and 30 minutes by adding 8.3 µL LDS sample buffer (4×) with 10% (v/v) 2-mercaptoethanol, heating at 75°C for 5 min, and removing resin with Spin-X columns.
6.  Analyze 16.7 µL of the supernatant by SDS-PAGE. Stain with InstantBlue for 1 hour and destain for 24 hours.
7.  Quantify radioactivity in GST-TIFA bands:
    *   Rinse the gel 5x in water (5 min each).
    *   Excise GST-TIFA bands and count in a scintillation counter.
    *   Count triplicate 1 µL aliquots of the radioactive ATP solution to determine specific radioactivity.
8.  Select the longest time point still within the linear range for all subsequent endpoint assays.

**Days 6-7: Measurement of ALPK1 Mutant Activity**
1.  For each cell extract (WT and S277F), immunoprecipitate with anti-FLAG resin and wash as before. Resuspend dry resin from each in 175 µL ice-cold reaction buffer.
2.  Aliquot 32.5 µL of each slurry into eight 1.5 mL tubes on ice.
3.  To each tube, add:
    *   2.5 µL of 1 mg/mL GST-TIFA.
    *   2.5 µL of one of the following in reaction buffer (in duplicate): reaction buffer (control), 100 µM ADP-heptose, 1 mM UDP-mannose, or 1 mM ADP-ribose.
4.  Initiate reactions with 2.5 µL radioactive ATP solution at 20-second intervals. Incubate at 30°C, 1300 rpm for the optimal time determined in Section C.
5.  Terminate and process samples for SDS-PAGE and scintillation counting as described in Section C, steps 5-7.
6.  Analyze and compare the incorporation of radioactivity into GST-TIFA for all conditions.

## Rank 2 — Protocol
**Source:** Discovery and functional analysis of a novel ALPK1 variant in ROSAH syndrome

**DOI:** [10.1098/rsob.240260](https://doi.org/10.1098/rsob.240260)

**Relevance score:** 95.0/100

### Protocol Steps

```markdown
# Protocol: Radiometric ALPK1 Kinase Activity Assay

**Research Intent:** Measurement of ALPK1 kinase activity using a radiometric assay.

This protocol integrates and resolves the detailed methods from the LI Supplementary Protocol [DOI:10.21769/bioprotoc.5124] with the primary method description.

## 1. Preparation of Buffers and Solutions (if not pre-prepared)
1.1. Prepare all necessary buffers (Culture media, Lysis buffer, Wash buffer, Salt wash buffer, Reaction buffer) as detailed in the Recipes section of [DOI:10.21769/bioprotoc.5124].  
1.2. Prepare the radioactive ATP solution immediately before use. To a 1.5 mL tube, add the calculated volume of undiluted [γ-³²P]ATP, 15 µL of 10 mM ATP, and reaction buffer to a final volume of 150 µL. The specific radioactivity should be approximately 500 cpm per pmol of ATP. Handle with due radiation safety precautions [DOI:10.21769/bioprotoc.5124].

## 2. Cell Culture and Transfection (Days 1–2)
2.1. Plate 15 million ALPK1 KO HEK-Blue cells (≤ passage 30) into each of three 15 cm dishes. Add culture media to a total volume of 20 mL and incubate for 18 hours at 37 °C, 5% CO₂ to achieve ~90% confluency.  
2.2. For each dish, dilute 60 µg of plasmid DNA (empty vector, FLAG-ALPK1, or FLAG-ALPK1[S277F]) in 600 µL OptiMEM I reduced serum medium in a 1.5 mL tube.  
2.3. In a separate tube, dilute 150 µL of Lipofectamine™ 2000 in 600 µL OptiMEM I.  
2.4. Add the diluted Lipofectamine to the diluted plasmid, invert five times to mix, and incubate for 10 minutes at room temperature.  
2.5. Add the transfection complex dropwise to the corresponding dish of cells and return to the incubator.  
2.6. After 4 hours, carefully aspirate the culture media and replace with 15 mL of fresh pre-warmed culture media (add slowly down the side of the plate to minimize cell detachment).  
2.7. Return plates to the incubator for 20 hours.

## 3. Preparation and Normalization of Cell Extracts (Day 3)
3.1. 24 hours post-transfection, detach cells by pipetting with a 15 mL serological pipette (no trypsinization).  
3.2. Transfer cell suspensions to 15 mL conical tubes. Centrifuge at 800 × g for 5 minutes at room temperature.  
3.3. Aspirate supernatant and wash pellets twice with 15 mL of room-temperature PBS (perform centrifugation and aspiration step each time).  
3.4. Place cell pellets on ice. All subsequent steps are performed on ice.  
3.5. Add 1 mL of ice-cold Lysis buffer to each pellet and resuspend by pipetting to form a homogenous suspension.  
3.6. Transfer lysates to pre-chilled 1.5 mL microcentrifuge tubes. Centrifuge at 18,000 × g for 20 minutes at 4 °C.  
3.7. Transfer supernatants (cell extracts) to new 1.5 mL tubes on ice.  
3.8. Determine protein concentration using a Bradford Protein Assay Kit.  
3.9. Dilute cell extracts to a final concentration of 2 mg/mL (protein) using ice-cold Lysis buffer. Keep on ice.

### 3.10. Normalization of cell extracts based on relative ALPK1 expression:
3.10.1. For each cell extract, use an aliquot containing 0.2 mg of protein and 15 µL of packed anti-FLAG M2 affinity gel (pre-washed with Lysis buffer).  
3.10.2. Incubate for 1 hour at 4 °C on a rotating wheel.  
3.10.3. Centrifuge at 2,000 × g for 1 minute at 4 °C. Discard supernatant.  
3.10.4. Wash resin three times with ice-cold Salt wash buffer, followed twice with ice-cold Wash buffer. Centrifugal steps: 2,000 × g for 1 minute at 4 °C.  
3.10.5. Remove all supernatant. Resuspend resin in 20 µL LDS sample buffer (1×) containing 2.5% (v/v) 2-mercaptoethanol. Heat for 5 minutes at 75 °C.  
3.10.6. Centrifuge at 13,000 × g for 30 seconds. Transfer supernatant to a Spin-X 0.22 µm column and centrifuge at 13,000 × g for 30 seconds.  
3.10.7. Analyze 10 µL of the eluent by SDS-PAGE with protein standards and stain with InstantBlue Protein Stain for 30 minutes, followed by destaining for 1 hour in water.  
3.10.8. Visualize and quantify the intensity of the FLAG-ALPK1 band (e.g., ~140 kDa) relative to the WT sample.  
3.10.9. If necessary, normalize the cell extracts by diluting samples (using empty vector lysate) to match the ALPK1 concentration of the sample with the lowest expression, such that total protein concentration remains 2 mg/mL.

### 3.11. Aliquoting and storage:
3.11.1. Prepare 0.5 mL aliquots of the diluted, normalized cell extracts on ice, each representing ~0.5 mg of total protein from WT lysate or normalized amounts for mutants.  
3.11.2. Snap-freeze single-use aliquots and store at –80 °C. Use within 1 month. Do not refreeze thawed aliquots.

## 4. Determination of Linear Rate Conditions for WT ALPK1 (Days 4–5)
4.1. Perform a time course phosphorylation assay for WT FLAG-ALPK1 (with and without ADP-heptose) for 5, 10, 20, and 30 minutes to establish the linear kinetic range. Include a 0-minute point (no ADP-heptose, no radioactive ATP) and a control without GST-TIFA.  
4.2. Thaw two aliquots of WT FLAG-ALPK1 lysate (combined for ~1.0 mg protein, sufficient for ~20 reactions) on ice.  
4.3. Wash anti-FLAG M2 affinity resin (sufficient for 18 reactions + 10% excess) twice with Lysis buffer (centrifuge 2,000 × g for 1 min at 4 °C per wash).  
4.4. Resuspend washed resin in the thawed lysate. Incubate for 1 hour at 4 °C on a rotating wheel.  
4.5. Wash the resin: three times with ice-cold Salt wash buffer, twice with ice-cold Wash buffer, and once with ice-cold Reaction buffer (centrifuge 2,000 × g for 1 min at 4 °C).  
4.6. Resuspend the final washed resin in 350 µL ice-cold Reaction buffer.  
4.7. Aliquot 32.5 µL of this slurry (containing ~15 µL packed resin) into 18 individual 1.5 mL microcentrifuge tubes on ice.  
4.8. Add 2.5 µL of 1 mg/mL GST-TIFA (dialyzed against Reaction buffer) to each tube (final concentration: 2.1 µM). For the no-GST-TIFA control, add 2.5 µL Reaction buffer instead.  
4.9. Add 2.5 µL of either Reaction buffer (no ADP-heptose) or 100 µM ADP-heptose in Reaction buffer (assay buffer).  
4.10. Initiate reactions by adding 2.5 µL of the prepared radioactive ATP solution to each tube at 20-second intervals. Immediately transfer tubes to a thermomixer at 30 °C, 1,300 rpm.  
4.11. Terminate the reactions at the designated time points (5, 10, 20, 30 min) by adding 8.3 µL of LDS sample buffer (4×) containing 10% (v/v) 2-mercaptoethanol.  
4.12. Heat all stopped reactions for 5 minutes at 75 °C.  
4.13. Centrifuge briefly and remove the FLAG resin using a Spin-X 0.22 µm column (centrifuge at 13,000 × g for 30 seconds).  
4.14. Analyze half of the supernatant (16.7 µL) by SDS-PAGE (NuPAGE Bis-Tris 4%–12% gel) with protein standards.  
4.15. Stain the gel with InstantBlue Protein Stain for 1 hour, followed by destaining in water for 24 hours with frequent changes.  
4.16. Wash the gel five times in water (5 minutes per wash) to reduce background radiation.  
4.17. Excise the band corresponding to GST-TIFA (as identified from the stained gel; see Figure 1B in [DOI:10.21769/bioprotoc.5124]) using a scalpel. Transfer each gel piece to a 1.5 mL microcentrifuge tube.  
4.18. Centrifuge tubes to bring the gel piece to the bottom (13,000 × g for 1 min).  
4.19. Count each sample using a liquid scintillation counter for 2 minutes per sample.  
4.20. Determine the specific radioactivity of the ATP solution by counting triplicate 1 µL aliquots of the radioactive ATP solution.  
4.21. Convert cpm values to pmol of phosphate incorporated using the specific radioactivity.  
4.22. Plot the data (e.g., pmol phosphate vs. time) to identify the linear range. Select the optimal timepoint (e.g., 20 minutes) for the endpoint assay.

## 5. Measurement of ALPK1 Mutant Activity with Nucleotide Sugars (Days 6–7)
5.1. Perform endpoint phosphorylation assays for WT and mutant ALPK1 in the presence or absence of nucleotide sugars (ADP-heptose, UDP-mannose, ADP-ribose), each in duplicate.  
5.2. Thaw one aliquot of each cell extract (WT and S277F mutant) on ice, sufficient for 10 reactions per extract.  
5.3. Wash anti-FLAG M2 affinity resin (0.6 mL slurry, 10% excess) twice with Lysis buffer (centrifuge 2,000 × g for 1 min at 4 °C per wash).  
5.4. Resuspend washed resin in 300 µL Lysis buffer and add 300 µL of this slurry to each thawed lysate (containing ~150 µL packed resin per sample).  
5.5. Incubate for 1 hour at 4 °C on a rotating wheel.  
5.6. Wash resin: three times with ice-cold Salt wash buffer, twice with ice-cold Wash buffer, and once with ice-cold Reaction buffer (centrifuge 2,000 × g for 1 min at 4 °C).  
5.7. After the final wash, resuspend the packed resin (150 µL) in each sample in a total volume of 175 µL ice-cold Reaction buffer.  
5.8. Aliquot 32.5 µL of each slurry into eight individual 1.5 mL tubes on ice (one tube per condition per duplicate).  
5.9. Add 2.5 µL of 1 mg/mL GST-TIFA to each tube.  
5.10. Add 2.5 µL of one of the following (on ice) to each tube: Reaction buffer (control), 100 µM ADP-heptose in Reaction buffer, 1 mM UDP-mannose in Reaction buffer, or 1 mM ADP-ribose in Reaction buffer.  
5.11. Initiate reactions by adding 2.5 µL of the radioactive ATP solution at 20-second intervals. Transfer tubes to a pre-warmed thermomixer at 30 °C, 1,300 rpm.  
5.12. Terminate the reactions at the optimal timepoint determined in step 4 (e.g., 20 minutes) by adding 8.3 µL of LDS sample buffer (4×) containing 10% (v/v) 2-mercaptoethanol.  
5.13. Heat reactions for 5 minutes at 75 °C.  
5.14. Remove FLAG resin using Spin-X columns (centrifuge at 13,000 × g for 30 seconds).  
5.15. Analyze half of the supernatant (16.7 µL) by SDS-PAGE (NuPAGE Bis-Tris 4%–12% gel) with protein standards.  
5.16. Stain the gel with InstantBlue Protein Stain for 1 hour, followed by destaining in water for 24 hours with frequent changes.  
5.17. Wash the gel five times in water (5 minutes per wash) to reduce background radiation.  
5.18. Excise the GST-TIFA band and process for scintillation counting as described in steps 4.17–4.20.  
5.19. Use the specific radioactivity of the ATP solution to convert cpm values to pmol of phosphate incorporated.
```

### Inherited References


These are references cited by this protocol that were resolved.
- **Cell-free ALPK1 phosphorylation assay detailed method**

  Extracted from: [10.21769/bioprotoc.5124](https://doi.org/10.21769/bioprotoc.5124)

---

## Rank 3 — Protocol
**Source:** A complex of MAST1 and 14-3-3η regulates Tau phosphorylation in the developing cortex

**DOI:** [10.1101/2025.07.09.663707](https://doi.org/10.1101/2025.07.09.663707)

**Relevance score:** 15.0/100

### Protocol Steps

### **Protocol: Radiometric Measurement of ALPK1 Kinase Activity**

#### **A. Substrate Phosphorylation Assay**
1.  **Prepare the kinase reaction:**
    1.  Mix 100 nM ALPK1 kinase and 25 μM substrate in assay buffer (50 mM HEPES pH 7.4, 150 mM NaCl, 1 mM TCEP, 2 mM MgCl₂, 2 mM ATP, 0.25% CHAPS, spiked with 1 μL [γ-³²P] ATP per 100 μL reaction).
2.  **Incubate the reaction:**
    1.  Incubate the reaction mixture at 23°C for a time course up to 2 hours.
3.  **Quench and prepare samples:**
    1.  At desired time points, remove aliquots from the reaction volume.
    2.  Quench each aliquot immediately by adding 80 mM EDTA.
4.  **Analyze by SDS-PAGE and phosphorimaging:**
    1.  Subject equal volumes of each quenched sample to SDS-PAGE.
    2.  Wash the resulting gels three times in dH₂O.
    3.  Dry the gels.
    4.  Expose the dried gels to a phosphor screen for 4 hours.
    5.  Image the screen with an Amersham Typhoon imager (Cytiva).
5.  **Quantify phosphorylation:**
    1.  Perform densitometry on the imaged gels using ImageJ to quantify phosphorylated substrate bands.
    2.  **Prepare internal standards:** Spot 0.5, 1, 5, and 20 pmol of ATP from the reaction onto a strip of Whatman paper.
    3.  Measure the internal standards with densitometry and use this standard curve to calculate the total moles of phosphorylated substrate in each sample.

#### **B. Autophosphorylation Assay**
1.  **Prepare the kinase reaction:**
    1.  Incubate MAST1DK ΔS90 kinase (WT and D499N) at concentrations of 50 nM, 150 nM, and 500 nM in assay buffer (50 mM HEPES pH 7.4, 150 mM NaCl, 1 mM TCEP, 2 mM MgCl₂, 2 mM ATP, 0.25% CHAPS, spiked with 1 μL [γ-³²P] ATP per 100 μL reaction).
2.  **Incubate the reaction:**
    1.  Incubate the reaction mixtures at 23°C for a time course up to 2 hours.
3.  **Quench and prepare samples:**
    1.  At desired time points, remove aliquots from each reaction volume.
    2.  Quench each aliquot immediately by adding 80 mM EDTA.
4.  **Analyze by membrane capture and phosphorimaging:**
    1.  Spot equal volumes of each quenched sample onto a 0.45 μm nitrocellulose membrane.
    2.  Wash the membrane five times with 20 mL of 75 mM H₃PO₄.
    3.  Expose the membrane to a phosphor screen for 4 hours.
    4.  Image the screen with an Amersham Typhoon imager (Cytiva).
5.  **Quantify autophosphorylation:**
    1.  Perform densitometry on the imaged membrane using ImageJ to quantify phosphorylated kinase bands.
    2.  Use an internal ATP standard curve (prepared as in step A.5.2) and densitometry to calculate the total moles of autophosphorylation in each sample.
