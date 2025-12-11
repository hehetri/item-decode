"""Re-encode ``itemout.txt`` into the original ``item.bin`` layout.

The binary format consists of:
* 4-byte little-endian item count
* Repeating records of 236 bytes comprised of:
  * 4-byte little-endian item id
  * 28-byte item name encoded in CP949 and padded with NUL bytes
  * 25 unsigned 32-bit little-endian attributes
  * 104-byte description encoded in CP949 and padded with NUL bytes

``item.bin`` also contains a large tail after the records; the converter copies
any trailing bytes from an existing template file (defaulting to ``item.bin``)
so regenerated binaries remain byte-identical to the source.
"""
from __future__ import annotations

import argparse
import csv
import pathlib
import struct
from typing import Iterable, List, NamedTuple, Sequence, Tuple

RECORD_SIZE = 236
COUNT_SIZE = 4
ID_SIZE = 4
NAME_SIZE = 28
ATTR_COUNT = 25
DESC_SIZE = 104
NAME_OFFSET = ID_SIZE
ATTR_OFFSET = NAME_OFFSET + NAME_SIZE
DESC_OFFSET = ATTR_OFFSET + ATTR_COUNT * 4

DEFAULT_INPUT = pathlib.Path("itemout.txt")
DEFAULT_OUTPUT = pathlib.Path("itemout.bin")
DEFAULT_TEMPLATE = pathlib.Path("item.bin")


def encode_padded(text: str, size: int) -> bytes:
    """Encode *text* to CP949, truncate to *size*, and pad with NUL bytes."""

    encoded = text.encode("cp949", errors="replace")
    trimmed = encoded[:size]
    return trimmed.ljust(size, b"\x00")


def build_record(
    item_id: int,
    name: str,
    attributes: Sequence[int],
    description: str,
    template: "TemplateRecord | None" = None,
) -> bytes:
    """Build a single binary record matching the ``item.bin`` structure."""

    if len(attributes) != ATTR_COUNT:
        raise ValueError(f"Expected {ATTR_COUNT} attributes, received {len(attributes)}")

    name_bytes = (
        template.name_bytes
        if template is not None and (not name or name == template.name)
        else encode_padded(name, NAME_SIZE)
    )
    desc_bytes = (
        template.desc_bytes
        if template is not None and not description
        else encode_padded(description, DESC_SIZE)
    )

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


def build_binary(
    count: int,
    records: Iterable[Tuple[int, str, Sequence[int], str]],
    templates: Sequence[TemplateRecord] | None = None,
) -> bytes:
    """Construct the full binary payload from parsed records."""

    payload = bytearray()
    payload.extend(struct.pack("<I", count))
    for index, record in enumerate(records):
        item_id, name, attributes, description = record
        template = templates[index] if templates and index < len(templates) else None
        payload.extend(build_record(item_id, name, attributes, description, template))

    return bytes(payload)


def extract_tail(template: pathlib.Path, base_length: int) -> bytes:
    """Return any trailing data that appears after the binary records in *template*.

    The provided ``item.bin`` includes a large zero-filled section and two
    non-zero bytes that occur after the record list. This function preserves any
    such content so the reconstructed file can match the original byte-for-byte
    when a template file is available.
    """

    if not template.exists():
        return b""

    template_bytes = template.read_bytes()
    if len(template_bytes) <= base_length:
        return b""

    return template_bytes[base_length:]


class TemplateRecord(NamedTuple):
    name_bytes: bytes
    name: str
    attributes: Tuple[int, ...]
    desc_bytes: bytes
    description: str


def load_template_records(path: pathlib.Path) -> List[TemplateRecord]:
    """Parse an existing binary file to recover original text fields per record."""

    if not path.exists():
        return []

    template_bytes = path.read_bytes()
    count = struct.unpack_from("<I", template_bytes, 0)[0]
    records: List[TemplateRecord] = []

    for index in range(count):
        start = COUNT_SIZE + index * RECORD_SIZE
        end = start + RECORD_SIZE
        chunk = template_bytes[start:end]

        raw_name = chunk[NAME_OFFSET : NAME_OFFSET + NAME_SIZE]
        raw_desc = chunk[DESC_OFFSET : DESC_OFFSET + DESC_SIZE]

        records.append(
            TemplateRecord(
                raw_name,
                raw_name.split(b"\x00", 1)[0].decode("cp949", errors="replace"),
                struct.unpack_from(f"<{ATTR_COUNT}I", chunk, ATTR_OFFSET),
                raw_desc,
                raw_desc.split(b"\x00", 1)[0].decode("cp949", errors="replace"),
            )
        )

    return records


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
    parser.add_argument(
        "--template",
        type=pathlib.Path,
        default=DEFAULT_TEMPLATE,
        help=(
            "Existing binary to use for copying any trailing bytes that appear after the"
            " record table"
        ),
    )
    args = parser.parse_args()

    count, records = parse_text_table(args.input)
    template_records = load_template_records(args.template)
    base_binary = build_binary(count, records, template_records)
    tail = extract_tail(args.template, len(base_binary))
    binary = base_binary + tail
    args.output.write_bytes(binary)


if __name__ == "__main__":
    main()
