"""Utility to unpack the ``item.bin`` file into a tab-separated text file."""
from __future__ import annotations

import argparse
import pathlib
import struct
from typing import Iterable, List, Tuple

# Column layout requested for decoded item data. The binary provides 25 numeric
# attributes; the list below mirrors the supplied attribute order and is
# trimmed to that count when writing headers.
ITEM_ATTRIBUTE_FIELDS = [
    "itemid",
    "name",
    "level",
    "unk",
    "price",
    "pricec",
    "sell",
    "unk",
    "unk",
    "durtype",
    "duration",
    "hp",
    "attmin",
    "attmax",
    "att(trans)min",
    "att(trans)max",
    "TransGauge",
    "Crit",
    "evade",
    "spectrans",
    "speed",
    "transbotdef",
    "transbotatt",
    "transspeed",
    "ranged",
    "luck",
    "unk",
    "effect",
    "image",
    "description",
]

RECORD_SIZE = 236
COUNT_SIZE = 4
NAME_SIZE = 28
ATTR_COUNT = 25
DESC_SIZE = 104
NAME_OFFSET = COUNT_SIZE
ATTR_OFFSET = NAME_OFFSET + NAME_SIZE
DESC_OFFSET = ATTR_OFFSET + ATTR_COUNT * 4

DEFAULT_INPUT = pathlib.Path("item.bin")
DEFAULT_OUTPUT = pathlib.Path("itemout.txt")


def parse_record(blob: bytes) -> Tuple[int, str, Tuple[int, ...], str]:
    """Parse a single ``item.bin`` record into its components."""

    item_id = struct.unpack_from("<I", blob, 0)[0]
    raw_name = blob[NAME_OFFSET : NAME_OFFSET + NAME_SIZE]
    name = raw_name.split(b"\x00", 1)[0].decode("cp949", errors="replace")

    attributes = struct.unpack_from(f"<{ATTR_COUNT}I", blob, ATTR_OFFSET)

    raw_desc = blob[DESC_OFFSET : DESC_OFFSET + DESC_SIZE]
    description = raw_desc.split(b"\x00", 1)[0].decode("cp949", errors="replace")

    return item_id, name, attributes, description


def parse_records(data: bytes) -> Iterable[Tuple[int, str, Tuple[int, ...], str]]:
    """Yield parsed records from the binary *data*."""

    item_count = struct.unpack_from("<I", data, 0)[0]
    for index in range(item_count):
        start = COUNT_SIZE + index * RECORD_SIZE
        end = start + RECORD_SIZE
        yield parse_record(data[start:end])


def write_output(
    destination: pathlib.Path,
    records: Iterable[Tuple[int, str, Tuple[int, ...], str]],
    total_items: int,
):
    """Write a human-readable ``itemout.txt`` file."""

    # Use the provided attribute order, trimming to the 25 numeric attributes
    # present in the binary payload while keeping the description column.
    header_columns = [
        ITEM_ATTRIBUTE_FIELDS[0],  # itemid
        ITEM_ATTRIBUTE_FIELDS[1],  # name
        *ITEM_ATTRIBUTE_FIELDS[2 : 2 + ATTR_COUNT],
        ITEM_ATTRIBUTE_FIELDS[-1],  # description
    ]

    with destination.open("w", encoding="utf-8") as outf:
        outf.write(f"{total_items}\n")
        outf.write("\t".join(header_columns) + "\n")
        for record in records:
            item_id, name, attributes, description = record
            row = [str(item_id), name, *map(str, attributes), description]
            outf.write("\t".join(row) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Decode item.bin into a readable text table")
    parser.add_argument("input", nargs="?", type=pathlib.Path, default=DEFAULT_INPUT, help="Path to item.bin")
    parser.add_argument("output", nargs="?", type=pathlib.Path, default=DEFAULT_OUTPUT, help="Destination file for decoded data")
    args = parser.parse_args()

    binary = args.input.read_bytes()
    total_items = struct.unpack_from("<I", binary, 0)[0]
    records = tuple(parse_records(binary))
    write_output(args.output, records, total_items)


if __name__ == "__main__":
    main()