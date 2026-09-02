# Prepared real-data samples

This directory contains compact samples created from the original public archives:

- `uci_mt001_30days_15min.csv`: UCI client MT_001 at its native 15-minute resolution.
- `iblend_academic_30days_15min.csv`: I-BLEND Academic building readings converted from watts and aggregated from one minute to 15 minutes in Asia/Kolkata time.

Regenerate them with `backend/scripts/prepare_real_datasets.py`. The raw third-party archives are intentionally not committed inside the application ZIP.
