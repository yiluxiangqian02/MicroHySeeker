# G1 Pilot Run Report (2026-06-02)

## Scope

Small-sample pilot run for 3 papers (text-only path, VLM disabled):

1. 2017_uchino_relationship_between_the_redox_reactions_on_a_bipolar_pl_eb3da9
2. 2022_kim_cathodic_protection_system_against_a_reverse_current_aft_180201
3. 2023_a_effects_of_operation_and_shutdown_parameters_and_electro_86a3bb

Each paper was executed with:

1. Dry-run import (`--dry-run --import-backend resource`)
2. Actual overwrite import (`--overwrite --import-backend resource`)

## Results

| Paper ID | Dry-run | Overwrite | Included | Skipped Non-whitelist | Missing Required |
|---|---|---|---:|---:|---:|
| 2017_uchino_relationship_between_the_redox_reactions_on_a_bipolar_pl_eb3da9 | OK | OK | 16 | 0 | 0 |
| 2022_kim_cathodic_protection_system_against_a_reverse_current_aft_180201 | OK | OK | 30 | 0 | 0 |
| 2023_a_effects_of_operation_and_shutdown_parameters_and_electro_86a3bb | OK | OK | 46 | 0 | 0 |

Pilot aggregate:

- Papers tested: 3
- Dry-run errors: 0
- Overwrite import errors: 0
- Total included files: 92
- Total skipped_non_whitelist: 0
- Total missing_required: 0

## Runtime Notes

Observed during overwrite runs:

- Repeated backend log line: `Error batch deleting records: Collection 'context' does not exist`
- Repeated semantic processor warning: `VLM not available, using empty summary/default overview`

Assessment:

- These warnings did not block import completion.
- All 3 papers were imported successfully with expected whitelist-only file stats.
- Behavior is consistent with text-only execution mode.

## Conclusion

G1 small-sample pilot run is successful for the selected 3 papers.

- Functional outcome: PASS
- Blocking issue: none
- Follow-up recommendation: proceed to G3 regression validation focused on retrieval quality and warning triage.
