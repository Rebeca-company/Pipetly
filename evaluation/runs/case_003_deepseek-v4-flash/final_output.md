# Pipetly — Extracted Protocols

**Search intent:** Generate transgene-free tomato plants via CRISPR-Cas9 Agrobacterium-mediated transformation, including gene editing induction and regeneration steps, starting from prepared Agrobacterium and sterilized seeds.

**Generated:** 2026-07-14T22:08:54

---

## Rank 1 — Protocol
**Source:** CRISPR-Cas9 Protocol for Efficient Gene Knockout and Transgene-free Plant Generation

**DOI:** [10.21769/BioProtoc.5012](https://doi.org/10.21769/BioProtoc.5012)

**Relevance score:** 95.0/100

### Protocol Steps

1. **Seed sterilization and germination (Day 1–11)** {[DOI:10.1007/978-1-4939-8778-8_16]}(https://doi.org/10.1007/978-1-4939-8778-8_16)
   1.1. Immerse 1 g of seeds in 25 mL of 70% ethanol for 2 min, then wash with sterile deionized water.
   1.2. Add 25 mL of sterilization solution (20% bleach + one drop Tween 20) and agitate at 250 rpm for 20 min.
   1.3. Rinse seeds three times with sterile deionized water.
   1.4. Sow 20–30 seeds per Magenta box containing 62.5 mL of ½ MS medium. Use eight boxes per transformation.
   1.5. Keep boxes at 4°C for 2 days, then transfer to 25°C in darkness for 8 days.

2. **Agrobacterium culture initiation (Day 10)** {[DOI:10.1007/978-1-4939-8778-8_16]}(https://doi.org/10.1007/978-1-4939-8778-8_16)
   2.1. Pick a single colony from a fresh Agrobacterium plate (≤1 week old) and inoculate 4 mL of LB broth with appropriate antibiotics. Also prepare a control culture with LB only (no antibiotics) and a culture with LB + antibiotics (no bacteria).
   2.2. Incubate at 28°C, 250 rpm, overnight (14–16 h).

3. **Cotyledon explant preparation and preculture (Day 11)**
   3.1. Transfer germinated seedlings to an autoclaved glass plate lined with moistened filter paper.
   3.2. Excise cotyledons at petiole, cut off both tips, and cut into ~1 cm sections.
   3.3. Transfer the explants to CIM I plates, placing them with the abaxial side down. Distribute 30–40 cotyledons per plate; use eight plates total.
   3.4. Incubate plates at 25°C under dim light for 24 h.

4. **Agrobacterium subculture and OD measurement (Day 11–12)** {[DOI:10.1007/978-1-4939-8778-8_16]}(https://doi.org/10.1007/978-1-4939-8778-8_16)
   4.1. Prepare four Erlenmeyer flasks each containing 250 mL of LB with appropriate antibiotics.
   4.2. Inoculate with 1, 2, 5, and 10 µL of the overnight culture (from step 2.2). Incubate at 28°C, 250 rpm for 14–16 h.
   4.3. Measure OD600. The ideal OD is 0.5–0.6; usable range is 0.4–0.9.
   4.4. Select the flask with the best OD. Transfer the culture into two 15 mL Falcon tubes and centrifuge at 1600 × g for 10 min.
   4.5. Discard supernatant, resuspend pellet in 10 mL of sterile 10 mM MgSO₄, and pour the suspension into a sterile Petri dish.

5. **Infection and co-culture (Day 12–14)**
   5.1. Immerse the explants (from step 3.4) in the Agrobacterium suspension for 10 min with gentle hand stirring.
   5.2. Remove explants, blot briefly on sterile filter paper without drying them, and immediately transfer to CIM II plates.
   5.3. Leave 20 uninfected cotyledons (controls): 10 positive controls (transfer to CIM II without antibiotics) and 10 negative controls (transfer to CIM II with antibiotics).
   5.4. Seal plates with Parafilm and incubate at 25°C under dim light for 48 h.

6. **Shoot induction (Day 14 onwards)** {[DOI:10.1007/978-1-4939-8778-8_16]}(https://doi.org/10.1007/978-1-4939-8778-8_16)
   6.1. Transfer explants to SIM I plates, 15–20 explants per plate. For controls: transfer 10 uninfected cotyledons to SIM I without antibiotics (positive) and 10 to SIM I with antibiotics (negative).
   6.2. Incubate at 25°C under a 16 h light / 8 h dark photoperiod for 14–18 days.
   6.3. Every 15 days (starting day 28–32), transfer explants to fresh SIM I.
   6.4. When green tissue appears, use a scalpel to separate it from brown/yellow explant remnants. Transfer the green tissue to SIM II plates.
   6.5. Continue subculturing remaining explants in SIM I until they also produce green tissue.

7. **Shoot elongation and rooting (Day 45–70)**
   7.1. When shoots reach sufficient height (~2 cm), cut them at the base without carrying explant remnants.
   7.2. Transfer each shoot to a tall Petri dish containing RIM.
   7.3. For controls: transfer 10 positive control shoots (from step 6.2, without antibiotic exposure) to RIM without kanamycin, and 10 negative control shoots to RIM with kanamycin.
   7.4. Incubate at 25°C under a 16 h light / 8 h dark photoperiod.
   7.5. After 10–12 days, check for root growth into the medium. Roots growing above the medium indicate escape; discard those. Transplant rooted shoots to soil.

8. **Molecular analysis – T0 generation** {[DOI:10.1105/tpc.108.061713]}(https://doi.org/10.1105/tpc.108.061713)
   8.1. When plants have first true leaves (~20 days), collect 100 mg leaf tissue and grind in liquid nitrogen.
   8.2. Add 500 µL CTAB extraction buffer (2% CTAB, 1.4 M NaCl, 0.2 M EDTA, 0.1 M Tris-HCl) and incubate at 65°C for 30 min.
   8.3. Add 500 µL chloroform, vortex, and centrifuge at 12,000 × g for 10 min.
   8.4. Transfer aqueous phase to a new tube, add 350 µL isopropanol, mix, and centrifuge at 12,000 × g for 20 min.
   8.5. Wash pellet with 500 µL 70% ethanol, dry, and resuspend in TE buffer (10 mM Tris-HCl, 1 mM EDTA).
   8.6. PCR amplify using primers for the vector (e.g., Cas9) to confirm presence. Also perform PCR with primers designed to flank the sgRNA target site (primers should hybridize ≥100 bp from the sgRNAs).
   8.7. Run 5 µL of PCR product on a 2% agarose gel – a double band indicates a large deletion. Sanger sequence the remaining product; frameshift in the sgRNA area indicates editing (heterozygous).
   8.8. If no frameshift is observed, perform sequence alignment to check for homozygous editing (rare) or no editing.

9. **Transgene-free line identification – T1 generation**
   9.1. Germinate 10 seeds from each T0 plant with confirmed editing.
   9.2. Extract gDNA from T1 seedlings as in steps 8.1–8.5.
   9.3. PCR amplify using Cas9-specific primers. A negative PCR result indicates transgene-free plants.
   9.4. PCR amplify the sgRNA target region, sequence, and align to identify homozygous edits.
   9.5. Select T1 lines that are both edited and transgene-free. If none are found, repeat screening in subsequent generations.

### Inherited References


These are references cited by this protocol that were resolved.
- **CTAB gDNA extraction method from leaves**

  Extracted from: [10.1007/978-1-4939-8778-8_16](https://doi.org/10.1007/978-1-4939-8778-8_16)
- **CTAB gDNA extraction method from leaves**

  Extracted from: [10.1105/tpc.108.061713](https://doi.org/10.1105/tpc.108.061713)

---

## Rank 2 — Protocol
**Source:** Genome editing and regeneration pipeline for engineering disease resistance in tomato using CRISPR/Cas9.

**DOI:** [10.3389/fpls.2026.1754287](https://doi.org/10.3389/fpls.2026.1754287)

**Relevance score:** 85.0/100

### Protocol Steps

1.  Germinate sterilized tomato seeds in vitro on full-strength MS medium solidified with 0.7% agar for 10 days.
2.  Prepare an *Agrobacterium* suspension at an OD600 of 0.3–0.5, supplemented with 100 µM ACS.
3.  Excise cotyledon explants from the germinated seedlings.
4.  Co-cultivate the cotyledon explants with the *Agrobacterium* suspension for 5–10 minutes.
5.  Transfer the explants to co-cultivation medium and incubate in the dark for 48 hours.
6.  After 48 hours, transfer the explants to shoot induction medium (TS1: full-strength MS supplemented with 0.5 mg/L zeatin, 0.1 mg/L IAA, 0.1 mg/L BAP, 10 mg/L kanamycin, and 200 mg/L timentin).
7.  Maintain the cultures under a 16-hour light/8-hour dark photoperiod.
8.  After approximately 2 weeks, when shoots emerge, continue maintaining the explants on TS1 medium for approximately 7 weeks.
9.  Transfer regenerated shoots to half-strength MS rooting medium supplemented with IBA.
10. Acclimatize rooted plants in soil under controlled growth chamber conditions (23 °C, long-day photoperiod).

## Rank 3 — Protocol
**Source:** Enhancing tomato fruit sweetness by CRISPR/Cas9-mediated SlVIF gene editing

**DOI:** [10.1016/j.plaphy.2026.111270](https://doi.org/10.1016/j.plaphy.2026.111270)

**Relevance score:** 78.0/100

### Protocol Steps

1. **Design and assemble the dual-sgRNA CRISPR/Cas9 vector.**
   - Select two target sequences with on-target scores >0.5 and low off-target potential using the Target Design online tool ([http://skl.scau.edu.cn/targetdesign/](http://skl.scau.edu.cn/targetdesign/)).
   - Amplify the T1T2 cassette from the pCBC-DT1T2 template using four primers (Target1-BsF, Target1-F, Target2-BsR, Target2-R).
   - Set up a Golden Gate restriction-ligation reaction: mix the purified T1T2-PCR fragment with the pKSE402 dual-editing vector, Bsa I, and T4 DNA Ligase. Incubate in a thermocycler for 5 hours at 37°C, then 5 min at 50°C, and 10 min at 80°C [{10.1186/s12870-014-0327-y}](https://doi.org/10.1186/s12870-014-0327-y). The recombinant product is pKSE402-SlVIF.

2. **Transform the vector into *E. coli* DH5α via heat shock.**
   - Thaw chemically competent DH5α cells on ice for 20–30 min.
   - Add 1–5 µL of pKSE402-SlVIF plasmid DNA (1–100 ng) to 50–100 µL of cells in a pre-chilled tube. Mix gently and incubate on ice for 20–30 min.
   - Heat shock at 42°C for exactly 30–45 sec, then place on ice for 2–5 min [{10.3791/253}](https://doi.org/10.3791/253).
   - Add 500–1000 µL of LB broth and incubate at 37°C with shaking (200–250 rpm) for 45–60 min.
   - Spread 50–200 µL onto LB agar plates containing 50 mg/L kanamycin. Incubate at 37°C overnight.
   - Validate positive clones by PCR and sequencing.

3. **Transfer the validated vector into *Agrobacterium* GV3101 via freeze-thaw method.**
   - Follow the freeze-thaw protocol (Holsters et al., 1978) to introduce pKSE402-SlVIF into GV3101.

4. **Prepare plant material and inoculate cotyledon explants.**
   - Germinate sterilized seeds of tomato cultivar ‘1912’ in tissue culture conditions (16 h light/8 h dark, 26°C, 50% humidity).
   - Excise cotyledons from 7-day-old seedlings.
   - Immerse cotyledon explants in a suspension of GV3101 (carrying pKSE402-SlVIF) for 15 min.
   - Blot dry and co-cultivate on MS medium + 2 mg/L zeatin in the dark for 2 days.

5. **Induce shoot regeneration and rooting.**
   - Transfer explants to MS solid medium + 2 mg/L zeatin, 200 mg/L timentin, and 75 mg/L kanamycin. Culture under 16 h light/8 h dark at 25°C for 4 weeks.
   - Excise regenerated shoots (~2 cm long) and transfer to 1/2 MS medium + 3 mg/L IBA and 100 mg/L timentin for rooting.

6. **Identify transgenic and edited lines.**
   - Screen rooted plants by PCR using primers 402-F and U626t-R to confirm transgene presence.
   - Amplify target sequences from positive plants with primers VIF-F/R and sequence PCR products to identify mutations.
   - Calculate editing efficiency = (edited plants / positive plants) × 100.

7. **Select Cas9-free homozygous mutants.**
   - Self-pollinate T0 homozygous mutants to produce T1 progeny.
   - Screen T1 plants by PCR with Cas9-specific primers (Cas9-F/R). Select individuals lacking a PCR band (Cas9-free).
   - Validate homozygosity by sequencing.

### Inherited References


These are references cited by this protocol that were resolved.
- **freeze-thaw method for Agrobacterium transformation**

  Extracted from: [10.1186/s12870-014-0327-y](https://doi.org/10.1186/s12870-014-0327-y)
- **freeze-thaw method for Agrobacterium transformation**

  Extracted from: [10.3791/253](https://doi.org/10.3791/253)
- **freeze-thaw method for Agrobacterium transformation**

  Extracted from: [10.1007/bf00267408](https://doi.org/10.1007/bf00267408)

---
