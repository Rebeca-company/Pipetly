# Pipetly — Extracted Protocols

**Search intent:** Measure ALPK1 kinase activity using a radiometric assay after cell preparation, transfection, and extract normalization.

**Generated:** 2026-07-14T00:10:35

---

## Rank 1 — Protocol
**Source:** Quantitative Measurement of the Kinase Activity of Wildtype ALPK1 and Disease-Causing ALPK1 Mutants Using Cell-Free Radiometric Phosphorylation Assays.

**DOI:** [10.21769/bioprotoc.5124](https://doi.org/10.21769/bioprotoc.5124)

**Relevance score:** 95.0/100

### Protocol Steps

1. **Transient expression of FLAG-tagged ALPK1 constructs in ALPK1 KO HEK-Blue cells (Days 1–2)**
    1.1. Plate 3 × 15 cm dishes with 15 million ALPK1 KO HEK-Blue cells each.
      - From two confluent 15 cm dishes (passage ≤30), aspirate media, add 10 mL PBS, aspirate, add 3 mL trypsin-EDTA, incubate at 37°C for 2–3 min.
      - Add 15 mL culture media, pipette to single-cell suspension, combine into a 50 mL tube.
      - Dilute 20 µL cell suspension with 80 µL media, mix 20 µL with 20 µL trypan blue, count (viability ≥90%).
      - Plate 15 million cells per dish, add media to 20 mL total, distribute by figure-of-8 motion.
      - Incubate at 37°C, 5% CO₂ for 18 h.
    1.2. Transfect cells (after 18 h, confluency ~90%).
      - For each plate: add 150 µL Lipofectamine 2000 to 600 µL OptiMEM in a 1.5 mL tube, invert 5 times.
      - Dilute 60 µg of each plasmid (empty vector, FLAG-ALPK1, FLAG-ALPK1[S277F]) in 600 µL OptiMEM in separate tubes, invert 5 times.
      - Add diluted Lipofectamine to diluted plasmid, invert 5 times, incubate 10 min at RT.
      - Add solution dropwise to corresponding dish, return to incubator.
      - After 4 h, carefully aspirate media, add 15 mL fresh culture media (pipette slowly against side).
      - Incubate for 20 h.

2. **Preparation and normalization of cell extracts from transfected ALPK1 KO HEK-Blue cells (Day 3)**
    2.1. Prepare cell extracts (24 h post-transfection, all steps on ice after cell pelleting).
      - Pipette culture media up and down to detach cells, transfer to 15 mL tubes.
      - Centrifuge at 800×g, 5 min, RT. Aspirate supernatant.
      - Add 15 mL PBS (do not resuspend), centrifuge again, aspirate. Repeat for total 2 washes.
      - After final aspiration, place pellets on ice.
      - Add 1 mL ice-cold lysis buffer to each pellet, pipette to homogenous suspension.
      - Transfer to pre-chilled 1.5 mL tubes, centrifuge at 18,000×g, 20 min, 4°C. Transfer supernatant (cell extract) to new tubes on ice.
    2.2. Determine protein concentration using Bradford assay.
      - Dilute 5 µL of each extract with 20 µL water (1:5).
      - Transfer 5 µL of each diluted extract (triplicate) to a 96-well plate. Also, 5 µL triplicate of BSA standards (2.0, 1.0, 0.75, 0.5, 0.25, 0.125, 0.0625 mg/mL in water).
      - Add 195 µL Bradford reagent, measure A595.
      - Calculate protein concentration by interpolation, including dilution factor.
      - Dilute extracts to 2 mg/mL with ice-cold lysis buffer in a 15 mL tube on ice. Keep at 4°C.
    2.3. Normalize cell extracts based on relative ALPK1 expression.
      - Prepare anti-FLAG M2 affinity resin (55 µL resin per 3 samples + 20% extra): add 110 µL slurry (50% resin) to a 1.5 mL tube on ice.
      - Centrifuge at 2,000×g, 1 min, 4°C. Aspirate supernatant.
      - Wash resin with 1 mL ice-cold lysis buffer (invert 5 times), centrifuge, aspirate. Repeat twice.
      - After final wash, resuspend beads in 945 µL ice-cold lysis buffer, invert 5 times.
      - Using trimmed pipette tip, add 270 µL slurry to 3 × 1.5 mL tubes (15 µL resin per tube).
      - Add 100 µL ice-cold cell extract (0.2 mg protein) to each tube.
      - Incubate at 4°C for 1 h on rotating wheel.
      - Centrifuge at 2,000×g, 1 min, 4°C. Aspirate supernatant.
      - Wash resin 3× with 1 mL ice-cold salt wash buffer (centrifuge, aspirate each time), then 2× with 1 mL ice-cold wash buffer.
      - After final wash, aspirate all residual buffer to dry resin.
      - Perform all following steps at RT.
      - Resuspend resin in 20 µL of 1× LDS sample buffer with 2.5% (v/v) 2-mercaptoethanol (prepare by mixing 20 µL LDS 4×, 58 µL water, 2 µL 2-ME). Heat at 75°C for 5 min.
      - Centrifuge at 13,000×g for 30 s, transfer supernatant to Spin-X column.
      - Centrifuge Spin-X at 13,000×g for 30 s.
      - Analyze 10 µL eluent (50%) by SDS-PAGE alongside 5 µL protein ladder.
      - Stain gel with InstantBlue for 30 min, destain in water for 1 h (change water often).
      - Image gel, quantify intensity of each FLAG-ALPK1 band relative to WT.
      - Calculate dilution factor to normalize ALPK1 amounts: dilute each extract to match the lowest ALPK1 concentration, using lysate from empty vector-transfected cells to keep total protein at 2 mg/mL.
      - Prepare 0.5 mL aliquots of normalized extracts on ice (0.5 mg protein per aliquot). Snap-freeze and store at -80°C (use within 1 month, do not re-freeze).

3. **Determination of linear rate conditions for WT ALPK1 (Days 4–5)**
    3.1. Perform time course phosphorylation assays.
      - Thaw 2 aliquots of WT FLAG-ALPK1 lysate on ice, combine (sufficient for 20 reactions).
      - Add 600 µL anti-FLAG M2 resin slurry (50% resin) to a 1.5 mL tube on ice.
      - Centrifuge at 2,000×g, 1 min, 4°C. Aspirate.
      - Wash resin 3× with 1 mL ice-cold lysis buffer (centrifuge, aspirate each time).
      - After final wash, resuspend dry resin in the combined lysate (1 mg total protein).
      - Incubate at 4°C for 1 h on rotating wheel.
      - Wash sample 3× with ice-cold salt wash buffer, 2× with ice-cold wash buffer, and 1× with ice-cold reaction buffer.
      - Resuspend the 300 µL of packed resin in 350 µL ice-cold reaction buffer.
      - Aliquot 32.5 µL of this slurry into 18 individual 1.5 mL tubes on ice (15 µL resin + 17.5 µL buffer per tube). Keep pipette tip at bottom to avoid drying.
      - Add 2.5 µL GST-TIFA (1 mg/mL) to each tube (except one "no GST-TIFA" control, add 2.5 µL reaction buffer instead).
      - Add 2.5 µL of either reaction buffer (for no ADP-heptose) or 2.5 µL of 100 µM ADP-heptose in reaction buffer to appropriate tubes.
      - For the 0-min timepoint: add 2.5 µL radioactive ATP solution (see step 3.1.9) then immediately terminate (step 3.1.10). For other timepoints: add 2.5 µL radioactive ATP solution at 20 s intervals, then place tubes in prewarmed thermomixer at 30°C, 1,300 rpm.
      - Terminate reactions at 5, 10, 20, and 30 min by adding 8.3 µL LDS sample buffer 4× with 10% (v/v) 2-ME, heat at 75°C for 5 min, then remove resin using Spin-X columns.
      - Analyze half of supernatant (16.7 µL) by SDS-PAGE (stop before dye front enters running buffer; excise dye front and discard as solid radioactive waste).
      - Stain gel with InstantBlue for 1 h, destain in water for 24 h with frequent changes (discard destaining water as aqueous radioactive waste).
    3.2. Quantify incorporation of radioactivity into GST-TIFA.
      - Wash gel 5× in water for 5 min each (discard wash water as radioactive waste).
      - Transfer gel to A4 plastic pocket, dab with filter paper to remove excess water.
      - Cut out GST-TIFA bands (see dashed box in Figure 1B) using scalpel, place in 1.5 mL tubes.
      - Centrifuge tubes at 13,000×g for 1 min to bring gel pieces to bottom.
      - Count each sample in scintillation counter for 2 min.
      - Also count triplicate 1 µL aliquots of radioactive ATP solution to determine specific radioactivity (cpm per nmol ATP).
      - Plot data (cpm vs time) to determine linear range. Choose the longest timepoint still within linear range (e.g., 20 min).

4. **Measurement of the activity of ALPK1 mutants in the presence of nucleotide sugars (Days 6–7)**
    4.1. Perform endpoint phosphorylation assays.
      - Thaw one aliquot of each normalized cell extract (WT and mutant) on ice, sufficient for 10 reactions each.
      - Add 0.6 mL anti-FLAG M2 resin slurry (50% resin) to a 1.5 mL tube on ice.
      - Centrifuge at 2,000×g, 1 min, 4°C. Aspirate.
      - Wash resin 3× with 1 mL ice-cold lysis buffer (centrifuge, aspirate each time).
      - After final wash, resuspend the 300 µL resin in 300 µL lysis buffer.
      - Add 300 µL of this slurry to each of the two lysate aliquots (WT and mutant).
      - Incubate at 4°C for 1 h on rotating wheel.
      - Wash each sample 3× with ice-cold salt wash buffer, 2× with ice-cold wash buffer, 1× with ice-cold reaction buffer.
      - After final wash, resuspend the 150 µL packed resin in each sample in 175 µL ice-cold reaction buffer.
      - Aliquot 32.5 µL of each slurry into 8 individual 1.5 mL tubes on ice (15 µL resin + 17.5 µL buffer per tube).
      - Add 2.5 µL GST-TIFA (1 mg/mL) to each tube.
      - Add 2.5 µL of either reaction buffer, 100 µM ADP-heptose, 1 mM UDP-mannose, or 1 mM ADP-ribose (in reaction buffer) to duplicate tubes as appropriate.
      - Add 2.5 µL radioactive ATP solution to each tube at 20 s intervals, place in prewarmed thermomixer at 30°C, 1,300 rpm.
      - Terminate reactions at the optimal timepoint determined in Section 3 (e.g., 20 min) by adding 8.3 µL LDS sample buffer 4× with 10% (v/v) 2-ME, heat at 75°C for 5 min.
      - Remove resin using Spin-X columns.
      - Analyze half of supernatant (16.7 µL) by SDS-PAGE, stain with InstantBlue for 1 h, destain in water for 24 h with frequent changes.
    4.2. Determine incorporation of radioactivity into GST-TIFA by scintillation counting.
      - Follow the same gel washing, band excision, and counting procedure as in Section 3.2 (steps 3.2.1–3.2.5).

## Rank 2 — Protocol
**Source:** Discovery and functional analysis of a novel ALPK1 variant in ROSAH syndrome

**DOI:** [10.1098/rsob.240260](https://doi.org/10.1098/rsob.240260)

**Relevance score:** 95.0/100

### Protocol Steps

1.  **Prepare cell extracts and normalize ALPK1 expression.**
    1.  Transfect 60 µg of plasmid DNA (encoding WT or mutant FLAG-ALPK1) into a 15 cm dish of ALPK1 KO HEK293-Blue cells using 150 µL of Lipofectamine 2000.
    2.  After 24 h, wash the cells twice with PBS.
    3.  Scrape the cells in 1 mL of ice-cold lysis buffer (50 mM Tris–HCl pH 7.5, 1 mM EDTA, 1 mM EGTA, 1% (v/v) Triton X-100, 2 mM DTT, 270 mM sucrose, supplemented with protease inhibitor cocktail).
    4.  Clarify the lysate by centrifugation at 20,000× g for 20 min at 4°C.
    5.  Transfer the supernatant (cell extract) to a new 1.5 mL microcentrifuge tube.
    6.  Normalize the cell extracts for ALPK1 expression and use 0.05 mg of protein for the immunoprecipitation.

2.  **Immunoprecipitate FLAG-ALPK1.**
    1.  Wash 15 µL of packed anti-FLAG M2 affinity gel twice with lysis buffer.
    2.  Incubate the normalized cell extract (0.05 mg protein) with the washed anti-FLAG M2 affinity gel for 1 h at 4°C on a rotating wheel.
    3.  Centrifuge at 1,000× g for 30 s at 4°C and discard the supernatant.
    4.  Wash the pelleted gel three times with Buffer A (50 mM Tris–HCl pH 7.5, 2 mM DTT, 0.1% Triton X-100) containing 500 mM NaCl.
    5.  Wash the pelleted gel twice with Buffer A.
    6.  Wash the pelleted gel once with Buffer B (50 mM Tris–HCl pH 7.5, 2 mM DTT, 0.1 mM EGTA, 10 mM magnesium acetate).

3.  **Perform the kinase reaction.**
    1.  Resuspend the immunoprecipitated FLAG-ALPK1 in 25 µL of Buffer B.
    2.  Add 2.1 µM GST-TIFA (dialyzed against 50 mM Tris–HCl pH 7.5, 2 mM DTT).
    3.  Initiate the reaction by adding 0.1 mM [γ-³²P]ATP (specific radioactivity 500 cpm pmol⁻¹).
    4.  Incubate at 30°C for 30 min.
    5.  Terminate the reaction by adding lithium dodecylsulfate (LDS) sample buffer containing 2.5% (v/v) 2-mercaptoethanol.
    6.  Heat the sample for 5 min at 75°C.
    7.  Pellet the FLAG resin by centrifugation at 13,000× g for 30 s.
    8.  Subject the supernatant to SDS-PAGE.

4.  **Quantify phosphate incorporation.**
    1.  Stain the gel with InstantBlue Protein Stain for 30 min.
    2.  Destain the gel in water for 16 h with frequent water changes.
    3.  Excise the bands corresponding to GST-TIFA.
    4.  Analyze the incorporation of ³²P-radioactivity by Cerenkov counting.
    5.  Convert the cpm values to pmol of phosphate using the specific radioactivity of the [γ-³²P]ATP.

### Inherited References


These are references cited by this protocol that were resolved.
- **Cell-free ALPK1 phosphorylation assay protocol**

  Extracted from: [10.21769/bioprotoc.5124](https://doi.org/10.21769/bioprotoc.5124)

---

## Rank 3 — Protocol
**Source:** In vitro kinase assay reveals ADP-heptose-dependent ALPK1 autophosphorylation and altered kinase activity of disease-associated ALPK1 mutants

**DOI:** [10.1038/s41598-023-33459-7](https://doi.org/10.1038/s41598-023-33459-7)

**Relevance score:** 35.0/100

### Protocol Steps

1. **Seed and transfect HEK293 cells**  
   - 72 hours before the experiment, seed 400,000 cells per well in 6-well plates.  
   - The next day, transfect cells with wild-type or mutated myc-ALPK1 constructs using FuGENE6 (Roche) according to the manufacturer’s instructions.

2. **Stimulate or infect cells (on experiment day)**  
   - Infect or stimulate cells with ADPH (as per experimental design).  
   - Immediately proceed to lysis.

3. **Lyse cells**  
   - Prepare lysis buffer: 1% NP-40, 150 mM NaCl, 10 mM Tris, 5 mM EDTA, 10% Glycerol, 1 mM vanadate, and Complete Protease Inhibitors (Roche).  
   - Add lysis buffer to cells and keep lysates on ice for 20 minutes.  
   - Centrifuge at 16,000 × g for 30 minutes at 4°C.  
   - Collect supernatant (total lysate).

4. **Immunoprecipitate myc-tagged ALPK1**  
   - Incubate supernatant with 1 μg of mouse monoclonal anti-myc antibody (9E10, Santa Cruz Biotechnology) on a rotating wheel overnight at 4°C.  
   - The next day, equilibrate Protein G Dynabeads (Invitrogen Thermo Fisher Scientific) in lysis buffer.  
   - Add the equilibrated beads to the lysate-antibody mixture and incubate on a rotating wheel for 1 hour at 4°C.

5. **Wash immunoprecipitates**  
   - Use a magnet (Dynamag, Invitrogen) to separate beads.  
   - Wash beads five times with lysis buffer.  
   - Wash beads once with 1 mL of kinase buffer (62.5 mM HEPES, 1.625 mM DTT, 46.9 mM MgCl₂, 3.125 mM EGTA, 15.6 mM beta-glycero-phosphate).

6. **Perform kinase reaction**  
   - Resuspend the entire bead-bound immunoprecipitate in 60 μL of kinase buffer containing 1 μg of recombinant GST-TIFA and 0.15 mM ATPγS.  
   - Incubate the suspension on a rotating wheel for 30 minutes at 37°C.

7. **Stop reaction and alkylate thiophosphate**  
   - Add EDTA to a final concentration of 20 mM and para-nitro-benzyl-mesylate (PNBM, Abcam) to a final concentration of 2.5 mM.  
   - Incubate on a rotating wheel for 1 hour at room temperature.

8. **Prepare samples for immunoblot analysis**  
   - Add 20 μL of 4× Laemmli buffer containing 20 mM DTT and 2 mM vanadate.  
   - Store samples at –20°C until immunoblot analysis.

### Inherited References


These are references cited by this protocol that were resolved.
- None

---
