# Pipetly — Extracted Protocols

**Search intent:** Knockin protocol using Cpf1 in human pluripotent stem cells and for the AAVS1 locus in HEK293T cells.

**Generated:** 2026-07-18T00:52:15

---

## Rank 1 — Protocol
**Source:** AAVS1 Knock-in v1

**DOI:** [10.17504/protocols.io.b37kqrkw](https://doi.org/10.17504/protocols.io.b37kqrkw)

**Relevance score:** 45.0/100

### Protocol Steps

# Knockin Protocol using Cpf1 in Human Pluripotent Stem Cells and for the AAVS1 Locus in HEK293T Cells

1. **Clone the AAVS1-SA-neo-CAGGS-nCas9-RT-2A-GFP targeting vector**
   1.1. Digest the nCas9-RT fragment from pCMV-PE2-GFP with PmeI and SacII.
   1.2. Digest the parental AAVS1-SA-neo-CAGGS vector with EcoRI and KpnI.
   1.3. Perform Gibson assembly of the digested nCas9-RT fragment into the digested parental vector.

2. **Nucleofection of human pluripotent stem cells (hPSCs)**
   2.1. Harvest hPSCs cultured on mouse embryonic fibroblasts (MEFs).
   2.2. Pre-assemble RNP complex with 80 pmol purified Cas9 (Macrolab, UC Berkeley) and 300 pmol chemically-modified sgRNA (Synthego) targeting the AAVS1 locus.
   2.3. Nucleofect cells with 1 µg targeting vector and the pre-assembled RNP.
   2.4. Replate nucleofected cells onto DR4 MEFs in hESC media containing ROCK-inhibitor.

3. **Selection and expansion of targeted clones**
   3.1. Select cells with 70 μg/mL G418 (Invitrogen) for 10 days, changing media daily from day 3.
   3.2. Manually pick survived clones.
   3.3. Expand clones and extract genomic DNA (gDNA).
   3.4. PCR genotype with primers flanking each homologous arm using PrimeStar GXL DNA polymerase (Takara).
   3.5. Expand and bank correctly targeted clones.

### Inherited References


These are references cited by this protocol that were resolved.
- None

---

## Rank 2 — Protocol
**Source:** Generation of the Adenovirus Vector-Mediated CRISPR/Cpf1 System and the Application for Primary Human Hepatocytes Prepared from Humanized Mice with Chimeric Liver

**DOI:** [10.1248/bpb.b18-00222](https://doi.org/10.1248/bpb.b18-00222)

**Relevance score:** 30.0/100

### Protocol Steps

### **Protocol: Cpf1-Mediated Genome Editing at the AAVS1 Locus**

1.  **Plasmid Construction**
    1.  **Prepare Cpf1 Expression Plasmids:**
        1.  Digest `pHM-CBh-hSpCas9` with `AgeI/NotI`.
        2.  Digest `pcDNA3.1-hAsCpf1` or `pcDNA3.1-hLbCpf1` with `HindIII/NotI`.
        3.  Ligate the digested fragments to produce `pHM-CBh-AsCpf1` or `pHM-CBh-LbCpf1`.
    2.  **Prepare gRNA Expression Plasmids:**
        1.  Insert double-stranded oligonucleotides (Table S1) into the `BsmBI` sites of `BPK3079` or `BPK3082` to produce `pU6-asgRNA-AAVS1` or `pU6-lbgRNA-AAVS1`.
        2.  Excise the `U6-asgRNA-AAVS1` or `U6-lbgRNA-AAVS1` fragment from the respective plasmid.
        3.  Insert the fragment into the `pHM5` shuttle vector to generate `pHM-U6-asgRNA-AAVS1` or `pHM-U6-lbgRNA-AAVS1`.
    3.  **Prepare Reporter and Control Plasmids:**
        1.  Use the previously described reporter plasmid `pCAG-EGxxFP-AAVS1` (containing ~500 bp of the AAVS1 locus).
        2.  Use the control plasmid `pHMEF5-mCherry`.

2.  **Adenovirus (Ad) Vector Preparation**
    1.  **Generate Ad Vectors:**
        1.  Integrate expression cassettes from `pHM-CBh-AsCpf1`, `pHM-CBh-LbCpf1`, `pHM-U6-asgRNA-AAVS1`, and `pHM-U6-lbgRNA-AAVS1` into the `I-CeuI/PI-SceI` sites of `pAdHM4` using an improved in vitro ligation method.
        2.  Prepare the control Ad vector `Ad-CA-GFP`.
    2.  **Amplify and Purify Ad Vectors:**
        1.  Amplify the Ad vectors in HEK293 cells.
        2.  Purify the vectors by two rounds of cesium-chloride-gradient ultracentrifugation.
    3.  **Determine Titers:**
        1.  Determine virus particle (VP) titers by spectrophotometric method.
        2.  Determine infectious units (IFU) using an Adeno-X Rapid Titer Kit.

3.  **Cell Culture**
    1.  **HEK293 Cells:** Culture in DMEM supplemented with 10% FBS, 100 µg/mL streptomycin, and 100 U/mL penicillin.
    2.  **H1299 Cells:** Culture in RPMI 1640 supplemented with 10% FBS, 100 µg/mL streptomycin, and 100 U/mL penicillin.
    3.  **Primary Human Hepatocytes (PHHs):** Culture on type I-collagen-coated plates with dHCGM supplied by the manufacturer.

4.  **Validation of gRNAs by EGxxFP Assay**
    1.  Seed HEK293 cells on poly-L-lysine-coated 24-well plates (1×10⁵ cells/well).
    2.  Co-transfect cells with 400 ng of Cpf1-expressing plasmid, 400 ng of `pCAG-EGxxFP-AAVS1`, and 200 ng of `pHMEF5-mCherry` using Lipofectamine 2000.
    3.  Incubate for 48 hours.
    4.  Capture and process images using a BIOREVO digital camera (BZ-9000, Keyence Japan).

5.  **T7 Endonuclease I (T7E1) Assay for Genome Editing Activity**
    1.  **Transfection (for H1299 cells):**
        1.  Seed H1299 cells (7×10⁴ cells/well) in 24-well plates.
        2.  Co-transfect with 400 ng of `pHM-CBh-AsCpf1` or `pHM-CBh-LbCpf1` and 400 ng of `pHM-U6-asgRNA-AAVS1` or `pHM-U6-lbgRNA-AAVS1` using Lipofectamine 2000.
    2.  **Transduction (for H1299 cells and PHHs):**
        1.  Suspend cells in culture medium.
        2.  Mix with Ad vectors (`Ad-AsCpf1` and `Ad-asgRNA-AAVS1`) at the indicated MOIs.
        3.  Seed onto 24-well plates at 7×10⁴ cells/well (H1299) or 4×10⁵ cells/well (PHHs).
    3.  **Assessment of Indel Mutations:**
        1.  Harvest genomic DNA from cells at 2 days (H1299) or 14 days (PHHs) post-transduction/transfection.
        2.  Amplify the target region of the human AAVS1 locus by PCR using the primer set for AAVS1 (Table S1) and PrimeSTAR Max DNA polymerase.
        3.  Denature and re-anneal 100 ng of PCR amplicons by heating and gradual cooling.
        4.  Digest with 30–50 units of T7E1 enzyme for 30 min at 37°C.
        5.  Resolve cleaved fragments by 10% PAGE and stain with Midori Green Advance.
        6.  Capture images using FAS5 (NIPPON Genetics) and show as black-and-white reversal.
        7.  Quantify signal intensity of each band using ImageJ software.
        8.  Calculate the percentage of indels using the formula: `% indels = 100 × (1 − (1 − cleaved band intensity / total band intensities)^(1/2))`.

6.  **Cell Viability Assay**
    1.  Seed PHHs on collagen-coated 96-well plates (7×10⁴ cells/well).
    2.  Assay cell viability 14 days after transduction using alamarBlue Cell Viability Reagent according to the manufacturer’s instructions.

7.  **Western Blot Analysis (for Protein Expression Confirmation)**
    1.  Perform cell lysis and electrophoresis on SDS-PAGE gels.
    2.  Transfer proteins to PVDF membranes.
    3.  Detect HA-tagged Cpf1 proteins using mouse Anti-HA antibody.
    4.  Use mouse anti-β-actin antibody as a loading control.

8.  **Genotyping Assay Using a Mismatch Recognition Nuclease (Supplementary Method)**
    1.  Amplify the target DNA sequence (e.g., AAVS1 locus) by PCR using specific primers (e.g., AAVS1-F/R).
    2.  Denature and re-anneal the PCR products.
    3.  Digest the DNA fragments with a mismatch-sensitive enzyme (e.g., Guide-it Resolvase).
    4.  Analyze the cleavage products by gel electrophoresis.
    5.  Quantify the intensities of each DNA band using ImageJ software.
    6.  Calculate the percentage of indel mutations as previously described. [{DOI:10.1248/bpb.b16-00700}](https://doi.org/10.1248/bpb.b16-00700)

### Inherited References


These are references cited by this protocol that were resolved.
- **spectrophotometric method for virus particle titers**

  Extracted from: [10.1089/10430349950017374](https://doi.org/10.1089/10430349950017374)
- **spectrophotometric method for virus particle titers**

  Extracted from: [10.1248/bpb.b16-00700](https://doi.org/10.1248/bpb.b16-00700)
- **spectrophotometric method for virus particle titers**

  Extracted from: [10.1248/bpb.b16-00700](https://doi.org/10.1248/bpb.b16-00700)
- **spectrophotometric method for virus particle titers**

  Extracted from: [10.1248/bpb.b16-00700](https://doi.org/10.1248/bpb.b16-00700)
- **spectrophotometric method for virus particle titers**

  Extracted from: [10.1016/0042-6822(68)90121-9](https://doi.org/10.1016/0042-6822(68)90121-9)

---
