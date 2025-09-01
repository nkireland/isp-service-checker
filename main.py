#!/usr/bin/env python3

import csv
import os
import signal
import sys
import time
from datetime import datetime, timezone

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


_STOP_REQUESTED = False


def _handle_stop_signal(signum, frame):  # noqa: ARG001 (frame unused)
    global _STOP_REQUESTED
    _STOP_REQUESTED = True


def load_config(config_path: str) -> dict:
    if not os.path.isfile(config_path):
        # Defaults if no config present
        return {
            "app": {
                "interval_seconds": 300,
                "log_file": "internet_metrics.csv",
            }
        }

    with open(config_path, "rb") as f:
        data = tomllib.load(f)

    # Ensure defaults if keys missing
    app_cfg = data.get("app", {})
    interval = int(app_cfg.get("interval_seconds", 300))
    log_file = str(app_cfg.get("log_file", "internet_metrics.csv"))
    return {"app": {"interval_seconds": interval, "log_file": log_file}}


def ensure_csv_with_headers(csv_path: str) -> None:
    file_exists = os.path.exists(csv_path)
    needs_header = True
    if file_exists:
        try:
            needs_header = os.path.getsize(csv_path) == 0
        except OSError:
            needs_header = True

    if (not file_exists) or needs_header:
        os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
        with open(csv_path, mode="a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp_iso", "download_mbps", "upload_mbps", "ping_ms"])


def run_speed_test() -> tuple[float, float, float]:
    """Return (download_mbps, upload_mbps, ping_ms)."""
    # Lazy import to reduce startup time when only configuring
    import speedtest  # type: ignore

    tester = speedtest.Speedtest()
    tester.get_best_server()

    # bytes per second -> megabits per second: (bytes/s * 8) / 1e6
    download_bps = tester.download()
    upload_bps = tester.upload()
    ping_ms = float(tester.results.ping)

    download_mbps = (download_bps * 8.0) / 1_000_000.0
    upload_mbps = (upload_bps * 8.0) / 1_000_000.0

    return float(download_mbps), float(upload_mbps), ping_ms


def append_result(csv_path: str, when: datetime, download_mbps: float, upload_mbps: float, ping_ms: float) -> None:
    with open(csv_path, mode="a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            when.replace(tzinfo=timezone.utc).isoformat(),
            f"{download_mbps:.2f}",
            f"{upload_mbps:.2f}",
            f"{ping_ms:.2f}",
        ])


def main() -> int:
    signal.signal(signal.SIGINT, _handle_stop_signal)
    try:
        signal.signal(signal.SIGTERM, _handle_stop_signal)
    except Exception:
        # Not all platforms have SIGTERM in the same way; ignore if unsupported
        pass

    cfg = load_config("config.toml")
    interval_seconds = int(cfg["app"]["interval_seconds"])
    csv_path = str(cfg["app"]["log_file"])

    ensure_csv_with_headers(csv_path)
    print(f"[isp-service-checker] Logging to: {csv_path}")
    print(f"[isp-service-checker] Interval: {interval_seconds} seconds")

    while not _STOP_REQUESTED:
        started = datetime.utcnow()
        try:
            dl, ul, ping = run_speed_test()
            append_result(csv_path, started, dl, ul, ping)
            print(
                f"[{started.isoformat()}Z] Download: {dl:.2f} Mbps | Upload: {ul:.2f} Mbps | Ping: {ping:.2f} ms"
            )
        except Exception as exc:  # noqa: BLE001 (broad for resiliency)
            print(f"[isp-service-checker] Error during speed test: {exc}", file=sys.stderr)

        # Sleep in small steps to react faster to stop signal
        slept = 0
        while slept < interval_seconds and not _STOP_REQUESTED:
            time.sleep(min(1, interval_seconds - slept))
            slept += 1

    print("[isp-service-checker] Stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


