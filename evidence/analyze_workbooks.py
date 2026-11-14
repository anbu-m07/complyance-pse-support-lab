"""Independent, static inspection of the supplied sample workbooks.

This is not a substitute for observing a live import, API, ASP, or database.
Run from the repository root: python3 evidence/analyze_workbooks.py
Requires openpyxl.
"""

from collections import defaultdict
import csv
import math
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "evidence" / "workbook-analysis.csv"


def round2(value):
    # Source Go code uses math.Round for positive values.
    return math.floor(value * 100 + 0.5) / 100


def rows(filename):
    book = load_workbook(ROOT / "samples" / filename, data_only=True)
    values = list(book["Invoices"].values)
    headers = values[0]
    return [dict(zip(headers, row)) for row in values[1:] if any(v is not None for v in row)]


def main():
    records = []
    for filename in (
        "oasis-builders-nov-2026.xlsx",
        "al-noor-fuel-nov-2026.xlsx",
        "sahara-medical-batch-1116.xlsx",
        "ghaf-cafe-nov-2026.xlsx",
    ):
        groups = defaultdict(list)
        for row in rows(filename):
            groups[row["Invoice number*"]].append(row)
        for number, lines in groups.items():
            net = sum(float(line["Invoice line net amount*"]) for line in lines)
            vat = sum(round2(float(line["Invoice line net amount*"]) * float(line["Invoiced item VAT rate*"]) / 100) for line in lines)
            gross = sum(float(line["Itemquantity*"]) * float(line["Item net price*"]) *
                        (1 + float(line["Invoiced item VAT rate*"]) / 100) for line in lines)
            exclusive, tax, inclusive = round2(net), round2(vat), round2(gross)
            records.append({
                "workbook": filename,
                "invoice_number": number,
                "buyer": lines[0]["Buyer name*"],
                "line_count": len(lines),
                "issue_date": lines[0]["Invoice issue date*"],
                "due_date": lines[0]["Payment due date*"],
                "net_AED": f"{exclusive:.2f}",
                "vat_AED": f"{tax:.2f}",
                "generated_gross_AED": f"{inclusive:.2f}",
                "net_plus_vat_AED": f"{round2(exclusive + tax):.2f}",
                "BR_CO_15_difference_AED": f"{inclusive - round2(exclusive + tax):.2f}",
            })
    with OUT.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)
    for filename in dict.fromkeys(item["workbook"] for item in records):
        part = [item for item in records if item["workbook"] == filename]
        print(filename, len(part), "invoices,", sum(item["line_count"] for item in part), "lines")
    print("Al Noor predicted BR-CO-15 mismatches:",
          [r["invoice_number"] for r in records if r["workbook"].startswith("al-noor")
           and r["BR_CO_15_difference_AED"] != "0.00"])


if __name__ == "__main__":
    main()
