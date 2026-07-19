# Pipetly — Extracted Protocols

**Search intent:** Measurement of ALPK1 kinase activity using a radiometric assay.

**Generated:** 2026-07-13T23:50:49

---

## Rank 1 — Protocol
**Source:** Quantitative Measurement of the Kinase Activity of Wildtype ALPK1 and Disease-Causing ALPK1 Mutants Using Cell-Free Radiometric Phosphorylation Assays.

**DOI:** [10.21769/bioprotoc.5124](https://doi.org/10.21769/bioprotoc.5124)

**Relevance score:** 98.0/100

### Protocol Steps

### Protocol for Measurement of ALPK1 Kinase Activity via Radiometric Assay

#### 1. Preparation of FLAG-ALPK1 Resin
1.1. Prepare anti-FLAG M2 affinity resin by adding 600 µL of slurry (50% resin by volume) to a 1.5 mL microcentrifuge tube on ice.
1.2. Centrifuge the slurry at 2,000 × g for 1 min at 4 °C and aspirate the supernatant.
1.3. Wash the resin by resuspending in 1 mL of ice-cold lysis buffer, centrifuging at 2,000 × g for 1 min at 4 °C, and aspirating; repeat this wash step twice.
1.4. Resuspend the dry resin in 1 mg of lysate expressing WT FLAG-ALPK1 (for time course) or specific ALPK1 mutants (for endpoint assays).
1.5. Incubate the mixture at 4 °C for 1 h on a rotating wheel to allow protein binding.
1.6. Wash the resin-bound protein three times with ice-cold salt wash buffer, twice with ice-cold wash buffer, and once with ice-cold reaction buffer, centrifuging at 2,000 × g for 1 min at 4 °C between each wash.
1.7. Resuspend the final packed resin in ice-cold reaction buffer to achieve a ratio of 15 µL resin per 17.5 µL buffer (e.g., 300 µL resin in 350 µL total volume).

#### 2. Kinase Reaction Setup
2.1. Aliquot 32.5 µL of the resin slurry into individual 1.5 mL microcentrifuge tubes on ice, ensuring the pipette tip reaches the bottom of the tube to prevent resin drying.
2.2. Add 2.5 µL of 1 mg/mL GST-TIFA (final concentration 2.1 µM) to each tube on ice.
    * *Note: For negative controls, substitute GST-TIFA with reaction buffer.*
2.3. Add 2.5 µL of the appropriate stimulator or buffer to the tubes on ice:
    * For time course: 100 µM ADP-heptose or reaction buffer.
    * For endpoint assays: 100 µM ADP-heptose, 1 mM UDP-mannose, 1 mM ADP-ribose, or reaction buffer.
2.4. Initiate the reaction by adding 2.5 µL of radioactive ATP solution (containing 1 mM ATP and [γ-32P]ATP) at 20-second intervals.
    * *Note: For 0-min time points, terminate the reaction before adding the radioactive ATP solution.*
2.5. Incubate the tubes in a prewarmed thermomixer at 30 °C and 1,300 rpm for the specified duration (5, 10, 20, or 30 min for time course; optimal linear time for endpoint assays).

#### 3. Reaction Termination and Protein Separation
3.1. Terminate the reactions at the designated time points by adding 8.3 µL of 4× LDS sample buffer containing 10% (v/v) 2-mercaptoethanol.
3.2. Heat the samples for 5 min at 75 °C.
3.3. Remove the resin by transferring the samples to Spin-X columns and centrifuging.
3.4. Load 16.7 µL of the supernatant onto an SDS-PAGE gel.
3.5. Run the SDS-PAGE, stopping the run before the dye front enters the running buffer.
3.6. Excise the dye front from the gel and discard as solid radioactive waste.
3.7. Stain the gel with InstantBlue for 1 h, then destain in water for 24 h with frequent water changes.

#### 4. Quantification of Radioactivity
4.1. Wash the destained gel five times in water for 5 min each to reduce background radiation.
4.2. Transfer the gel to a plastic pocket, remove excess water with filter paper, and excise the bands corresponding to GST-TIFA using a scalpel.
4.3. Place the excised gel pieces into 1.5 mL microcentrifuge tubes and centrifuge at 13,000 × g for 1 min to pellet the gel.
4.4. Measure the radioactivity of each gel sample using a scintillation counter for 2 min per sample.
4.5. Determine the specific radioactivity of the ATP source by counting triplicate 1 µL aliquots of the radioactive ATP solution.
4.6. Calculate the linear rate conditions (for time course) or relative kinase activity (for endpoint assays) based on cpm values and specific radioactivity.

### Inherited References


These are references cited by this protocol that were resolved.
- None

---

## Rank 2 — Protocol
**Source:** Discovery and functional analysis of a novel ALPK1 variant in ROSAH syndrome

**DOI:** [10.1098/rsob.240260](https://doi.org/10.1098/rsob.240260)

**Relevance score:** 98.0/100

### Protocol Steps

1. **Immunoprecipitation of FLAG-ALPK1**
    1. Wash 15 μl of packed anti-FLAG M2 affinity gel twice with lysis buffer.
    2. Combine 0.05 mg of cell extract protein (containing WT or mutant FLAG-ALPK1, normalized for expression) with the washed 15 μl of packed anti-FLAG M2 affinity gel.
    3. Incubate the mixture for 1 h at 4°C on a rotating wheel.
    4. Centrifuge the mixture for 30 s at 1000 × g at 4°C and discard the supernatant.
    5. Wash the pelleted gel three times with Buffer A (50 mM Tris–HCl pH 7.5, 2 mM DTT, 0.1% Triton X-100) supplemented with 500 mM NaCl.
    6. Wash the pelleted gel twice with Buffer A.
    7. Wash the pelleted gel once with Buffer B (50 mM Tris–HCl pH 7.5, 2 mM DTT, 0.1 mM EGTA, 10 mM magnesium acetate).

2. **Kinase Assay Reaction**
    1. Prepare a reaction mix in a final volume of 25 µl of Buffer B containing 2.1 μM GST-TIFA (previously dialyzed against 50 mM Tris–HCl pH 7.5, 2 mM DTT).
    2. Add the immunoprecipitated FLAG-ALPK1 resin to the reaction mix.
    3. Initiate the reaction by adding [γ-32P]ATP to a final concentration of 0.1 mM (specific radioactivity 500 cpm pmol−1).
    4. Incubate the reaction for 30 min at 30°C.
    5. Terminate the reaction by adding lithium dodecylsulfate sample buffer containing 2.5% (v/v) 2-mercaptoethanol.
    6. Heat the samples for 5 min at 75°C.

3. **Detection and Quantification**
    1. Centrifuge the samples for 30 s at 13,000 × g to pellet the FLAG resin.
    2. Collect the supernatant and load onto an SDS-PAGE gel for electrophoresis.
    3. Stain the gel for 30 min with InstantBlue Protein Stain.
    4. Destain the gel for 16 h in water, changing the water frequently.
    5. Excise the protein bands corresponding to GST-TIFA from the gel.
    6. Measure the incorporation of 32P-radioactivity in the excised bands using Cerenkov counting.
    7. Convert the recorded cpm values to pmol of phosphate based on the specific radioactivity of the ATP.

## Rank 3 — Protocol
**Source:** Discovery of a selective alpha-kinase 1 inhibitor for the rare genetic disease ROSAH syndrome.

**DOI:** [10.1038/s41467-025-63731-5](https://doi.org/10.1038/s41467-025-63731-5)

**Relevance score:** 98.0/100

### Protocol Steps

1. **Reaction Mixture Preparation**
    1. Prepare the kinase reaction buffer containing 20 mM HEPES (pH 7.5), 10 mM MgCl2, 1 mM EGTA, 0.01% Brij35, 0.02 mg/mL BSA, 0.1 mM Na3VO4, 2 mM DTT, and 1% DMSO.
    2. Mix recombinant human ALPK1 (0.5 nM), human TIFA (10 µM), and ADP-D-heptose (5 nM) in the kinase reaction buffer.
    3. For ALPK1[T237M] variants, replace ALPK1 with ALPK1[T237M] and replace ADP-D-heptose with 10 μM UDP-mannose.

2. **Inhibitor Addition**
    1. Prepare 3-fold serial dilutions of DF-003 in DMSO, ranging from 1 µM to 50.8 pM.
    2. Add the DF-003 dilutions to the reaction mixture.
    3. Prepare vehicle control samples using DMSO without DF-003.

3. **Kinase Reaction Initiation and Incubation**
    1. Initiate the reaction by adding [33P]-ATP to a final concentration of 20 µM (specific activity: 0.01 µCi/µL).
    2. Incubate the mixture at room temperature for 60 minutes.
    3. For time-course experiments (without DF-003), proceed to the next step at intervals of 20, 40, and 60 minutes.

4. **Detection and Quantification**
    1. Spot the reaction samples onto P81 ion exchange paper (#3698-915, Whatman).
    2. Wash the filter paper extensively with 0.75% phosphoric acid to remove unreacted ATP.
    3. Measure the radioactive phosphorylated substrate remaining on the filter paper using a scintillation counter.
    4. Calculate the percentage of remaining ALPK1 kinase activity relative to the vehicle control.
    5. Perform curve fitting and IC50 value calculations using GraphPad Prism 4.
