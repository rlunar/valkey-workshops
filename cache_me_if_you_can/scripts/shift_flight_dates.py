#!/usr/bin/env python3
"""
Shift all datetime values in the `flight` table INSERT statements
forward by 5 months in a SQL dump file.

Usage:
    python scripts/shift_flight_dates.py data/temp_dump.sql data/temp_dump_shifted.sql

Processes the file line-by-line to handle very large files without
loading everything into memory.
"""

import re
import sys
from datetime import datetime
from dateutil.relativedelta import relativedelta

MONTHS_AHEAD = 6

# Matches datetime strings like '2025-12-07 21:25:00'
DATETIME_RE = re.compile(r"'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})'")


def shift_date(match: re.Match) -> str:
    """Shift a matched datetime string forward by MONTHS_AHEAD months."""
    dt = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S")
    dt_shifted = dt + relativedelta(months=MONTHS_AHEAD)
    return f"'{dt_shifted.strftime('%Y-%m-%d %H:%M:%S')}'"


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <input.sql> <output.sql>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    in_flight_insert = False
    lines_processed = 0

    with open(input_file, "r", encoding="latin-1") as fin, \
         open(output_file, "w", encoding="latin-1") as fout:

        for line in fin:
            # Detect start of a flight INSERT block
            if line.startswith("INSERT INTO `flight`"):
                in_flight_insert = True

            # If we're inside a flight INSERT block, shift dates
            if in_flight_insert:
                line = DATETIME_RE.sub(shift_date, line)
                lines_processed += 1

                # Detect end of INSERT statement (line ends with ';')
                if line.rstrip().endswith(";"):
                    in_flight_insert = False
            # Stop processing flight data if we hit another table's structure
            elif in_flight_insert and "Table structure for table" in line:
                in_flight_insert = False

            fout.write(line)

    print(f"Done! Shifted dates across {lines_processed} lines in flight INSERT blocks by {MONTHS_AHEAD} months.")
    print(f"Output: {output_file}")


if __name__ == "__main__":
    main()
