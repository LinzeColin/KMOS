# Recovery and takeover

## Public source

Clone `LinzeColin/KMOS`, start from `main`, then validate this package. Do not reconstruct production configuration from examples.

## Private state

The cleanup snapshot is outside Git under the OneDrive path recorded in `KMFA/HANDOFF.md`. It contains:

- local-only target config with real group IDs;
- `data/all_files_manifest.sqlite3` and cursor state;
- hot archive bodies, chat records, reports, logs and Notion sync state;
- current scripts matching the snapshot.

Restore by copying the whole private DWS runtime to a protected local/OneDrive location. Keep `config/target_groups.yaml`, `data/`, `archive/`, `reports/`, `logs/`, `snapshots/`, `probe/` and output packages out of Git.

Before a live run, minimally verify:

```bash
sqlite3 data/all_files_manifest.sqlite3 'PRAGMA quick_check;'
python3 scripts/validate_dws_output_structure.py --help
DWS_CODEX_CONTROLLED=1 DWS_RUN_SOURCE=codex_manual /bin/sh scripts/run_daily.sh --plan-only
```

The last command is preflight only; remove `--plan-only` only with explicit live-run authorization.
