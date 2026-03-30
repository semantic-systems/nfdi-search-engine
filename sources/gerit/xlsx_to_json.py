

import argparse
import json
import os
import pandas as pd

def convert(input_path: str, output_path: str) -> None:
    print(f"Reading: {input_path}")
    df = pd.read_excel(input_path)

    # replace missing values with None so they serialise to null in json
    df = df.where(pd.notna(df), other=None)

    records = df.to_dict(orient="records")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print(f"Written {len(records)} records to: {output_path}")


def main() -> None:
    """
    Convert the GERiT institution .xlsx file to a .json file.

    Usage:
        python xlsx_to_json.py [--input <path>] [--output <path>]

    Defaults:
        --input  sources/gerit/institutionen_gerit.xlsx
        --output sources/gerit/institutionen_gerit.json
    """
    parser = argparse.ArgumentParser(
        description="Convert GERiT .xlsx to .json"
    )

    # default input and output if no paths are given
    default_input = os.path.join(os.path.dirname(__file__), "institutionen_gerit.xlsx")
    default_output = os.path.join(os.path.dirname(__file__), "institutionen_gerit.json")

    parser.add_argument(
        "--input",
        default=default_input,
        help="Path to the source .xlsx file (default: sources/gerit/institutionen_gerit.xlsx)",
    )
    parser.add_argument(
        "--output",
        default=default_output,
        help="Path for the output .json file (default: sources/gerit/institutionen_gerit.json)",
    )
    args = parser.parse_args()

    convert(
        input_path=os.path.abspath(args.input),
        output_path=os.path.abspath(args.output),
    )


if __name__ == "__main__":
    main()
