from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from .config import load_config, check_service


def _url(value: str) -> str:
    value = value.rstrip("/")
    return value if value.endswith("/v1") else value + "/v1"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Recursively convert PDFs with Marker")
    parser.add_argument("root", nargs="?", help="PDF root directory")
    parser.add_argument("--mode", choices=("balanced", "fast"), default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--output-root", help="Optional output root; preserves input relative directories")
    args = parser.parse_args(argv)
    if not args.root:
        parser.print_help()
        return 0
    root = Path(args.root).resolve()
    if not root.is_dir():
        parser.error(f"Not a directory: {root}")
    config_path = Path(__file__).resolve().parents[1] / ".env"
    try:
        config = load_config(config_path)
    except ValueError as exc:
        parser.error(str(exc))
    if args.mode:
        config["mode"] = args.mode
    from .output import output_complete
    from .scheduler import run_batch
    inputs = sorted(root.rglob("*.pdf"))
    output_root = Path(args.output_root).resolve() if args.output_root else None
    jobs = []
    for input_pdf in inputs:
        output_pdf = (output_root / input_pdf.relative_to(root)) if output_root else input_pdf
        jobs.append((input_pdf, output_pdf))
    if not args.overwrite:
        jobs = [(input_pdf, output_pdf) for input_pdf, output_pdf in jobs if not output_complete(output_pdf)]
    files = [input_pdf for input_pdf, _ in jobs]
    if not files:
        print("No PDFs need conversion.")
        return 0
    try:
        check_service(config["surya_url"], config["api_key"])
    except ValueError as exc:
        parser.error(str(exc))
    print(f"配置文件：{config_path}；Surya：{config['surya_url']}；待处理：{len(files)}")
    started = time.monotonic()
    started_at = datetime.now(timezone.utc).isoformat()
    succeeded, failed, oom_count = run_batch(
        jobs, **config,
    )
    elapsed = time.monotonic() - started
    finished_at = datetime.now(timezone.utc).isoformat()
    report = {"started_at": started_at, "finished_at": finished_at, "elapsed_seconds": round(elapsed, 2),
              "concurrency": config["concurrency"], "requests_per_worker": config["requests_per_worker"],
              "oom_count": oom_count, "total": len(files),
              "succeeded": len(succeeded), "failed": len(failed), "failures": {str(k): v for k, v in failed.items()}}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if failed else 0

if __name__ == "__main__":
    raise SystemExit(main())





