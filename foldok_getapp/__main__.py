"""CLI: regenerate the snippet whenever the landing URL changes."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .qr import QRStyle, module_count
from .widget import landing_note, widget


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="foldok_getapp", description=__doc__)
    parser.add_argument("--url", required=True, help="the landing page the QR points at")
    parser.add_argument("--android", default="", help="direct Android install URL")
    parser.add_argument("--ios", default="", help="iOS URL, if there is one yet")
    parser.add_argument("--id", default="getCapture", help="element id")
    parser.add_argument("--size", type=int, default=168, help="QR size in px")
    parser.add_argument("--out", default="", help="write here instead of stdout")
    args = parser.parse_args(argv)

    modules = module_count(args.url)
    if modules > 45:
        print(
            f"warning: {modules} modules — that URL is long enough to be awkward to scan "
            "from a laptop screen. A shorter path scans faster.",
            file=sys.stderr,
        )

    html = widget(
        args.url, android_url=args.android, ios_url=args.ios,
        element_id=args.id, qr_style=QRStyle(size=args.size),
    )
    if args.out:
        Path(args.out).write_text(html + "\n", encoding="utf-8")
        print(f"wrote {args.out} ({len(html)} bytes, QR {modules}x{modules} modules)")
        print()
        print(landing_note(args.url))
    else:
        print(html)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
