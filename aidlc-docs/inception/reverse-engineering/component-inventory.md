# Component Inventory

## Application Packages
- `src/core` - batch validation pipeline (load, schema, synth, pipeline, report, features)
- `src/run.py` - entry point

## Infrastructure Packages
- None (deployment via `scripts/sync.sh`, not IaC)

## Shared Packages
- `src/core/features/_shared.py` - Utilities - shared metric formatting

## Test Packages
- `tests/` - Unit / compliance - pipeline contract, schema reporting, run entry, adopt script, spec compliance

## Total Count
- **Total Packages**: 3
- **Application**: 1
- **Infrastructure**: 0
- **Shared**: 1
- **Test**: 1
