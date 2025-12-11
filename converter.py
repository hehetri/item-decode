"""Re-encode ``itemout.txt`` into the original ``item.bin`` layout.

The binary format consists of:
* 4-byte little-endian item count
* Repeating records of 236 bytes comprised of:
  * 4-byte little-endian item id
  * 28-byte item name encoded in CP949 and padded with NUL bytes
  * 25 unsigned 32-bit little-endian attributes
  * 104-byte description encoded in CP949 and padded with NUL bytes
"""
from __future__ import annotations

import argparse
import csv
import pathlib
import struct
from typing import Iterable, List, Sequence, Tuple

RECORD_SIZE = 236
COUNT_SIZE = 4
NAME_SIZE = 28
ATTR_COUNT = 25
DESC_SIZE = 104

DEFAULT_INPUT = pathlib.Path("itemout.txt")
DEFAULT_OUTPUT = pathlib.Path("itemout.bin")


def encode_padded(text: str, size: int) -> bytes:
    """Encode *text* to CP949, truncate to *size*, and pad with NUL bytes."""

    encoded = text.encode("cp949", errors="replace")
    trimmed = encoded[:size]
    return trimmed.ljust(size, b"\x00")


def build_record(item_id: int, name: str, attributes: Sequence[int], description: str) -> bytes:
    """Build a single binary record matching the ``item.bin`` structure."""

    if len(attributes) != ATTR_COUNT:
        raise ValueError(f"Expected {ATTR_COUNT} attributes, received {len(attributes)}")

    name_bytes = encode_padded(name, NAME_SIZE)
    desc_bytes = encode_padded(description, DESC_SIZE)

    return b"".join(
        [
            struct.pack("<I", item_id),
            name_bytes,
            struct.pack(f"<{ATTR_COUNT}I", *attributes),
            desc_bytes,
        ]
    )


def parse_text_table(path: pathlib.Path) -> Tuple[int, List[Tuple[int, str, List[int], str]]]:
    """Read ``itemout.txt``-style data and return the count and record tuples."""

    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f, delimiter="\t")
        try:
            total_items = int(next(reader)[0])
        except StopIteration as exc:
            raise ValueError("The input file is empty") from exc

        try:
            _headers = next(reader)
        except StopIteration as exc:
            raise ValueError("The input file is missing header rows") from exc

        records: List[Tuple[int, str, List[int], str]] = []
        for row_index, row in enumerate(reader, start=1):
            if not row:
                continue
            if len(row) != 2 + ATTR_COUNT + 1:
                raise ValueError(
                    f"Row {row_index} has {len(row)} columns; expected {2 + ATTR_COUNT + 1}"
                )

            item_id = int(row[0])
            name = row[1]
            attributes = [int(value) for value in row[2:-1]]
            description = row[-1]
            records.append((item_id, name, attributes, description))

    if total_items != len(records):
        raise ValueError(
            f"Item count ({total_items}) does not match rows provided ({len(records)})"
        )

    return total_items, records


def build_binary(count: int, records: Iterable[Tuple[int, str, Sequence[int], str]]) -> bytes:
    """Construct the full binary payload from parsed records."""

    payload = bytearray()
    payload.extend(struct.pack("<I", count))
    for record in records:
        payload.extend(build_record(*record))

    return bytes(payload)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Encode itemout.txt back into the original binary format"
    )
    parser.add_argument(
        "input",
        nargs="?",
        type=pathlib.Path,
        default=DEFAULT_INPUT,
        help="Path to the tab-separated item data (itemout.txt)",
    )
    parser.add_argument(
        "output",
        nargs="?",
        type=pathlib.Path,
        default=DEFAULT_OUTPUT,
        help="Destination for the reconstructed binary file",
    )
    args = parser.parse_args()

    count, records = parse_text_table(args.input)
    binary = build_binary(count, records)
    args.output.write_bytes(binary)


if __name__ == "__main__":
    main()
