# Technical demo script — maximum 8 minutes

Use a prepared virtual environment so rendering fits. Keep the recording
unedited and leave genuine failures visible.

## Commands

```powershell
cd .\3_Content_Engine
.\.venv\Scripts\Activate.ps1
python -m unittest discover -s .\tests -v

# Normal single-input run
python .\run.py .\inputs\episode_one_recording_a_week_of_content.md --out .\demo\ --start-date 2026-11-02

# Repeat: expect 20 unchanged
python .\run.py .\inputs\episode_one_recording_a_week_of_content.md --out .\demo\ --start-date 2026-11-02

# New-input refresh: expect only the second input's slots to be created
python .\run.py .\inputs\ --out .\demo\ --start-date 2026-11-02

# Failure then recovery
python .\run.py .\inputs\episode_one_recording_a_week_of_content.md --out .\failure_demo\ --simulate-failure 3
python .\run.py .\inputs\episode_one_recording_a_week_of_content.md --out .\failure_demo\
```

## Running order

| Time | Demonstrate |
|---|---|
| 0:00–0:45 | README architecture, deterministic offline default, and disclosure |
| 0:45–1:35 | Tests and scoped secret scanning |
| 1:35–3:20 | Normal single-input run; inspect `last_run.json`, one spec, calendar, and media |
| 3:20–4:05 | Repeat/idempotency and no duplicates |
| 4:05–5:15 | Add second input and show refresh behavior |
| 5:15–6:35 | Simulated failure exit 1, log line, rerun, and missing-only recovery |
| 6:35–7:20 | Scheduler CSV, UTMs, runtime, and USD 0 offline cost |
| 7:20–8:00 | Optional AI fallback, rights/branding limits, and pending human evidence |

Expected values depend on machine speed. State actual observed results rather
than reading historic figures as if they occurred in the recording.

Expected deterministic counts for the supplied inputs:

- Fresh single input: `planned=20`, `created=20`, `errors=0`, 20 calendar rows.
- Immediate repeat: `created=0`, `unchanged=20`.
- Refresh with both inputs: `created=20`, `unchanged=20`, 40 calendar rows.
- Simulated third-render failure: one render error, 19 created, process exit 1.
- Recovery: one created, 19 unchanged, zero errors, process exit 0.

Runtime is machine-dependent; read the value from that run’s `last_run.json`.
