import argparse
import json
import signal
import sys

from .engine import run_scan
from .models import Control, RecoveryError
from .restore import image_device, recover, write_json_exclusive
from .source import ImageSource
from .store import Store, protect_history
from .windows import WindowsRawSource, enumerate_devices


def main(argv=None):
    parser = argparse.ArgumentParser(description="RecoverX: read-only disk image recovery")
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("scan")
    scan.add_argument("image")
    scan.add_argument("--mode", choices=["quick", "deep"], default="deep")
    scan.add_argument("--db", default="recoverx.sqlite")
    scan.add_argument("--report")
    scan.add_argument("--resume")
    scan.add_argument("--sector-size", type=int, choices=[512, 4096], default=512)
    export = sub.add_parser("recover")
    export.add_argument("image")
    export.add_argument("scan_id")
    export.add_argument("destination")
    export.add_argument("--db", default="recoverx.sqlite")
    export.add_argument("--id", action="append", help="Candidate ID; repeat for multiple files")
    export.add_argument("--allow-image-disk", action="store_true")
    report = sub.add_parser("report")
    report.add_argument("scan_id")
    report.add_argument("destination")
    report.add_argument("--db", default="recoverx.sqlite")
    sub.add_parser("devices")
    imaging = sub.add_parser("image-device")
    imaging.add_argument("disk_number", type=int)
    imaging.add_argument("destination")
    imaging.add_argument(
        "--consent", action="store_true", required=True, help="I am authorized to read this specific disk"
    )
    args = parser.parse_args(argv)
    control = Control()
    signal.signal(signal.SIGINT, lambda *_: control.cancelled.set())

    def progress(done, total, phase):
        print(f"\r{phase}: {done:,} / {total:,} bytes", file=sys.stderr, end="", flush=True)

    store = None
    try:
        if args.command == "devices":
            print(json.dumps(enumerate_devices(), indent=2))
            return 0
        if args.command == "image-device":
            device = next((d for d in enumerate_devices() if d["number"] == args.disk_number), None)
            if not device:
                raise RecoveryError("Device is no longer present")
            with WindowsRawSource(device["number"], device["size"], device["sector_size"]) as source:
                result = image_device(source, args.destination, control, progress)
            print(json.dumps(result))
            return 0
        if hasattr(args, "image"):
            protect_history(args.image, args.db)
        store = Store(args.db)
        if args.command == "report":
            write_json_exclusive(args.destination, store.report(args.scan_id))
            return 0
        with ImageSource(args.image) as source:
            if args.command == "scan":
                scan_id = run_scan(source, store, args.mode, control, progress, args.resume, args.sector_size)
                if args.report:
                    write_json_exclusive(args.report, store.report(scan_id))
                print(
                    json.dumps(
                        {
                            "scan_id": scan_id,
                            "status": store.get(scan_id)["status"],
                            "candidates": store.count(scan_id),
                        }
                    )
                )
                return 0 if store.get(scan_id)["status"] == "complete" else 2
            scan = store.get(args.scan_id)
            if json.loads(scan["source_identity"]) != source.identity:
                raise RecoveryError("Source does not match this scan")
            outcomes, failures = [], 0
            for offset in range(0, store.count(args.scan_id), 1000):
                for candidate in store.results(args.scan_id, offset, 1000):
                    if args.id and candidate.id not in args.id:
                        continue
                    if not args.id and not candidate.sha256:
                        continue
                    try:
                        outcome = recover(
                            source, candidate, args.destination, control, progress, args.allow_image_disk
                        )
                    except RecoveryError as exc:
                        failures += 1
                        outcome = {"id": candidate.id, "status": "failed", "error": str(exc)}
                    outcomes.append(outcome)
            print(json.dumps(outcomes, indent=2))
            return 1 if failures else 0
    except (RecoveryError, OSError) as exc:
        print(f"\nRecoverX: {exc}", file=sys.stderr)
        return 1
    finally:
        if store:
            store.close()


if __name__ == "__main__":
    raise SystemExit(main())
