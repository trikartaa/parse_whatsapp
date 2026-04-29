import argparse
import sys
import os

# Import our tools
from whatsapp_parser import analyze_whatsapp_data
from inspect_whatsapp_data import inspect_docx

def main():
    parser = argparse.ArgumentParser(description="WhatsApp Marketing Data Tool Suite")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Inspect command
    inspect_parser = subparsers.add_parser("inspect", help="Quickly preview DOCX structure")
    inspect_parser.add_argument("input", help="Path to the input .docx file")
    inspect_parser.add_argument("-n", "--lines", type=int, default=50, help="Number of paragraphs to show")

    # Parse command
    parse_parser = subparsers.add_parser("parse", help="Analyze WhatsApp data and export to CSV")
    parse_parser.add_argument("input", help="Path to the input .docx file")
    parse_parser.add_argument("-o", "--output", help="Path to the output .csv file")

    args = parser.parse_args()

    if args.command == "inspect":
        inspect_docx(args.input, args.lines)
    elif args.command == "parse":
        output = args.output
        if not output:
            base = os.path.splitext(args.input)[0]
            output = f"{base}_Analysis.csv"
        analyze_whatsapp_data(args.input, output)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
