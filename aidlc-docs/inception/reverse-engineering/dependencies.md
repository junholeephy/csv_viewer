# Dependencies

## Internal Dependencies

```mermaid
flowchart LR
    main_mod["__main__"] --> load_mod["load"]
    main_mod --> schema_mod["schema"]
    main_mod --> synth_mod["synth"]
    main_mod --> pipeline_mod["pipeline"]
    main_mod --> report_mod["report"]
    synth_mod --> schema_mod
    pipeline_mod --> template_mod["features.template"]
    template_mod --> shared_mod["features._shared"]
    template_mod --> schema_mod
```

### __main__ depends on load, schema, synth, pipeline, report
- **Type**: Runtime. **Reason**: orchestrates the run.
### synth depends on schema
- **Type**: Runtime. **Reason**: generates rows from `INPUT_SCHEMA`.

## External Dependencies
### pytest
- **Version**: 9.1.1. **Purpose**: tests (dev only). **License**: MIT
### anthropic
- **Version**: 0.75.0. **Purpose**: dev-only tooling (must never be imported in `src/`). **License**: MIT
