"""CLI entry point for HoleritePRO"""

import sys
import argparse
from pathlib import Path


def cmd_process(args):
    """Process PDFs through the pipeline."""
    from src.core.pipeline import Pipeline, pipeline_to_json

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: {input_path} does not exist", file=sys.stderr)
        sys.exit(1)

    # Collect PDF files
    if input_path.is_dir():
        pdf_paths = sorted(str(p) for p in input_path.glob("*.pdf"))
    else:
        pdf_paths = [str(input_path)]

    if not pdf_paths:
        print(f"No PDF files found in {input_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Processing {len(pdf_paths)} PDF(s)...")

    pipeline = Pipeline()
    result = pipeline.process_pdfs(pdf_paths)

    # Output
    json_output = pipeline_to_json(result)

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(json_output, encoding="utf-8")
        print(f"Output written to {output_path}")
    else:
        print(json_output)

    # Summary
    r = result.relatorio
    print(f"\n--- Summary ---", file=sys.stderr)
    print(f"PDFs: {r.get('total_pdfs', 0)}", file=sys.stderr)
    print(f"Holerites: {r.get('total_holerites', 0)}", file=sys.stderr)
    print(f"Verbas: {r.get('total_verbas', 0)}", file=sys.stderr)
    print(f"CPFs: {r.get('cpfs_unicos', 0)}", file=sys.stderr)
    print(f"Errors: {r.get('erros_count', 0)}", file=sys.stderr)

    if result.erros:
        for e in result.erros:
            print(f"  ! {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        prog="holeritepro",
        description="HoleritePRO — Payslip PDF processing engine",
    )
    subparsers = parser.add_subparsers(dest="command")

    # process command
    proc = subparsers.add_parser("process", help="Process PDF files")
    proc.add_argument("--input", "-i", required=True, help="PDF file or directory")
    proc.add_argument("--output", "-o", help="Output JSON file (default: stdout)")
    proc.set_defaults(func=cmd_process)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
