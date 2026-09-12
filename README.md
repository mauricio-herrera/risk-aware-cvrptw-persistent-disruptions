# Risk-Aware Last-Mile Routing under Persistent Disruptions

## Reproducibility package

This repository contains the frozen reproducibility materials supporting the
revised manuscript:

**Risk-Aware Last-Mile Routing under Persistent Disruptions:
Tail-Risk Planning and Selective Dynamic Recourse**

Manuscript reference: **TRIP-D-26-00192**

The package is designed to make the final numerical evidence, figure
construction, manuscript source, supplementary material, and computational
provenance independently inspectable.

---

## Scientific scope

The study separates three decision layers:

1. an exogenous temporally persistent disruption environment;
2. risk-aware preoperational routing;
3. causal bounded online recourse.

The Hawkes process is exogenous to vehicle routes and realized delays.

The Operational Memory Index (OMI) is an environmental quantity common to all
methods. Different routes experience different exposure because their arc
departure times differ.

The principal confirmatory findings are:

- temporal persistence increases upper-tail tardiness even under controls for
  average environmental impact;
- CVaR-oriented adaptive large neighbourhood search improves the aligned
  tail-risk objective and tail tardiness across all nine operational days;
- learned operator selection does not show a robust incremental advantage under
  the matched evaluation protocol;
- causal DDDAS performs selective local residual-suffix recourse;
- conditional decision-time improvement does not guarantee lower cost on the
  subsequently realized single trajectory.

---

## Repository structure

```text
manuscript/
    Revised manuscript source, compiled PDF, bibliography, highlights,
    and Elsevier bibliography style.

supplement/
    Revised Supplementary Material source and compiled PDF.

figures/
    main/
        Canonical Figures 1--6 in PDF, PNG, and TIFF.
    supplementary/
        Supplementary Figures S1--S6 in PDF, PNG, and TIFF.

figure_data/
    Compact publication-facing CSV tables used by the figure scripts.

frozen_outputs/
    Confirmatory R3, R4-D, R4-E1, R4-E2, and R5-H outputs.
    Development-stage and superseded results are intentionally excluded.

scripts/
    Figure-generation and frozen-result audit scripts.

audits/
    Scientific-claim, bibliography, integrity, provenance, and SHA-256 audits.

environment/
    Scientific-analysis and final-build environment records.

data_external/
    Provenance information for the external Athens source dataset.
```
