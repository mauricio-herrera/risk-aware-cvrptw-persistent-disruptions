# Frozen confirmatory outputs

This directory contains only the frozen confirmatory computational evidence
supporting the revised manuscript.

The development project included earlier smoke tests, diagnostics, pilot runs,
runtime calibrations, and superseded implementations. Those materials are not
used as scientific evidence in the final manuscript and are intentionally not
included in this archival release.

## Included stages

| Directory | Scientific role | Status |
|---|---|---|
| R3_REWARDFIX_VAL5_OUTPUT | Final source-day RL/ALNS validation after reward correction | Confirmatory |
| R3_VAL5_LOGS | Execution logs associated with final R3 validation | Provenance |
| R3_UNIFORM_CONTROL_OUTPUT | Uniform operator-selection control | Confirmatory |
| R3_UNIFORM_LOGS | Execution logs associated with uniform control | Provenance |
| R4D_CONFIRMATORY_MULTISEED_OUTPUT | Persistence experiment under controlled mean environmental impact | Confirmatory |
| R4E1_NOMINAL_CROSSDAY_OUTPUT | Nine-day ALNS-Mean versus ALNS-CVaR evaluation | Confirmatory |
| R4E2_ZERO_SHOT_TRANSFER_OUTPUT | Zero-shot learned-policy transfer to Days 2--9 | Confirmatory |
| R5H0_CONFIRMATORY_FREEZE | Prospectively frozen DDDAS day/route-selection protocol | Protocol freeze |
| R5H_CONFIRMATORY_OUTPUT | Sequential causal DDDAS executions | Confirmatory |
| R5H_CONFIRMATORY_ANALYSIS | Final DDDAS scientific and operational analysis | Confirmatory |

## Explicitly excluded

The following development artifacts are intentionally excluded from the
confirmatory archive:

- R3_FAST_SMOKE_OUTPUT
- R3_MULTISEED_OUTPUT
- R3_REWARDFIX_OUTPUT
- generic pre-final R3_LOGS
- R5H0C_FAST_V2_CALIBRATION_DAY1
- R5H0C_RUNTIME_CALIBRATION_DAY1
- legacy fixed-versus-triggered DDDAS results
- outputs produced before the corrected OR-Tools integer scaling
- RL results produced before the final reward correction

## Scientific interpretation

The Hawkes disruption process is exogenous to routing.

The Operational Memory Index (OMI) is an environmental state common to all
routing methods. Routes differ in their exposure because they depart along
arcs at different times.

The final RL evaluation does not establish a robust advantage of learned
operator selection over the corresponding controls.

The final sequential DDDAS implementation is causal and performs bounded local
residual-suffix recourse. Conditional decision-time improvement does not imply
lower cost on the single future trajectory that is subsequently realized.
