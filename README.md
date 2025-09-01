# ISP Service Checker (Console)

A small Python console app that periodically measures your internet connection (download/upload Mbps, ping) and appends results to a CSV file.
Author: nkireland

## Features
- Configurable interval via `config.toml`
- CSV logging with headers (auto-created if missing)
- Graceful shutdown on Ctrl+C (SIGINT) or SIGTERM
- Uses `speedtest-cli` Python library

## Setup

1) Create and activate a virtual environment (recommended):

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2) Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

Configure via `config.toml` in the project root. Defaults are already provided.

```toml
[app]
interval_seconds = 300
log_file = "internet_metrics.csv"
```

- **interval_seconds**: How often to run the check (in seconds).
- **log_file**: Path to the CSV file to append metrics to. If the file does not exist, it is created with headers.

## Run

```bash
python main.py
```

The app will run continuously at the configured interval. Press `Ctrl+C` to stop.

## Output

Appends rows to the CSV log file with the following headers:

```
timestamp_iso,download_mbps,upload_mbps,ping_ms
```

## Notes
- This project uses the `speedtest-cli` library which connects to Ookla servers. Results can vary depending on selected servers and network conditions.


