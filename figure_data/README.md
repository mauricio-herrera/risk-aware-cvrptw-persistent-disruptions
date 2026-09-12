# Figure source data

This directory contains the compact, publication-facing source tables used by
the final figure-generation scripts.

These files do not replace the complete confirmatory computational outputs
stored under `frozen_outputs/`. They provide a transparent intermediate layer
between the frozen analysis outputs and the publication figures.

## Main figures

- `main/Fig2_environment.csv`
  Environmental persistence diagnostics.

- `main/Fig3_persistence_routing.csv`
  Routing performance under the persistence control.

- `main/Fig4_crossday.csv`
  Day-level ALNS-Mean versus ALNS-CVaR contrasts.

- `main/Fig4_overall.csv`
  Across-day summary statistics shown in Figure 4.

- `main/Fig5_RL.csv`
  Final source-day ALNS/RL performance summaries.

- `main/Fig5C_cost.csv`
  Computational-budget comparison.

- `main/Fig6_DDDAS.csv`
  Day-level sequential DDDAS scientific contrasts.

- `main/Fig6D_counts.csv`
  Sequential DDDAS operational accounting.

## Supplementary figures

- `supplementary/S1_R3_budget_parity.csv`
  Search-budget parity audit.

- `supplementary/S2_R4D_mean_impact_control.csv`
  Mean-impact-matched persistence control.

- `supplementary/S3_R4E1_crossday_gains.csv`
  Nine-day joint cross-instance results.

- `supplementary/S4_R4E2_zero_shot_audit.csv`
  Zero-shot-transfer structural and performance audit.

- `supplementary/S5_R5H_operational_by_day.csv`
  Online recourse accounting by selected day.

- `supplementary/S6_R5H_decision_outcomes.csv`
  Conditional decision-time versus realized online outcomes.

All scientific claims should ultimately be traced to the frozen confirmatory
outputs rather than to manually transcribed figure values.
