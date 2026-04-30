"""
Fetches Montgomery County tax delinquency data from the county Tax Claim Bureau.

Source: https://www.montgomerycountypa.gov/2635/Prior-Sales-Results
The "Prior Sales Results" page lists all upset sale result PDFs by year.
This fetcher finds the most recent upset sale PDFs, downloads them, and
extracts delinquent parcel IDs using pdfplumber.

Note: These are *results* (properties that appeared in a completed upset sale),
which are a reliable proxy for tax delinquency. Properties are often redeemed
before the sale date, so this list skews toward chronic delinquencies.

Output columns (matches workers/ingest/tax_delinquency.py):
  parcel_id, tax_year, amount_due, delinquency_status, sale_eligible

Run:
  python -m workers.fetch.tax_delinquency --out data/tax_delinquency.csv
"""
import argparse
import csv
import re
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

import time

import pdfplumber
import requests
from bs4 import BeautifulSoup

from workers.common.log import elapsed, log

_PREFIX = "fetch_tax"

# Authoritative page listing all upset sale result PDFs by year.
PRIOR_RESULTS_URL = "https://www.montgomerycountypa.gov/2635/Prior-Sales-Results"

# Fallback: the tax claim home page also links to the same documents.
TAX_CLAIM_URL = "https://taxclaim.montcopa.org/"

# Maximum number of most-recent PDFs to process (1 = current year only).
MAX_PDFS = 2

# Montgomery County parcel ID format verified from live PDFs (2026-04-29):
#   "10-00-05252-00-3"  →  2-2-5-2-1 segments, always 12 digits when hyphens stripped
# Secondary formats kept for older documents.
PARCEL_RE = re.compile(
    r"\b(?:\d{2}-\d{2}-\d{5}-\d{2}-\d{1}|\d{2}-\d{2}-\d{5}-\d{3,4}|\d{2}-\d{3}-\d{4}-\d{3}|\d{12})\b"
)
AMOUNT_RE = re.compile(r"\$?([\d,]+\.\d{2})")
YEAR_RE   = re.compile(r"\b(20\d{2})\b")


def _find_pdf_urls(session: requests.Session) -> list[tuple[int, str]]:
    """
    Scrape the Prior Sales Results page for upset sale PDF links.
    Returns list of (year, absolute_url) sorted by year descending.
    """
    found: list[tuple[int, str]] = []
    try:
        r = session.get(PRIOR_RESULTS_URL, timeout=20)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"  WARNING: could not fetch {PRIOR_RESULTS_URL}: {e}")
        return found

    soup = BeautifulSoup(r.text, "lxml")
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        href = a.get("href", "")
        # Match "YYYY Upset Sale Results" or "YYYY Continued Upset Sale Results"
        if "upset" in text.lower() and ("results" in text.lower() or "list" in text.lower()):
            year_m = YEAR_RE.search(text)
            year   = int(year_m.group(1)) if year_m else 0
            abs_url = urljoin(PRIOR_RESULTS_URL, href)
            if abs_url not in (u for _, u in found):
                found.append((year, abs_url))

    found.sort(key=lambda x: x[0], reverse=True)
    return found


def _parse_pdf(pdf_path: Path, year: int, writer, seen: set) -> int:
    """Extract delinquent parcel rows from an upset sale result PDF."""
    count = 0
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            # Try structured table extraction first
            tables = page.extract_tables() or []
            for table in tables:
                for row in (table or []):
                    if not row:
                        continue
                    row_text = " ".join(str(c or "") for c in row)
                    # Normalize hyphens: "30 00 34228 005" → no help; look raw
                    pid_m = PARCEL_RE.search(row_text)
                    if not pid_m:
                        continue
                    pid = pid_m.group(0).replace("-", "")  # normalize to 12-digit DB format
                    if pid in seen:
                        continue

                    amount = 0.0
                    amt_m = AMOUNT_RE.search(row_text)
                    if amt_m:
                        try:
                            amount = float(amt_m.group(1).replace(",", ""))
                        except ValueError:
                            pass

                    yr_m = YEAR_RE.search(row_text)
                    tax_year = int(yr_m.group(1)) if yr_m else year

                    writer.writerow({
                        "parcel_id":          pid,
                        "tax_year":           tax_year,
                        "amount_due":         amount,
                        "delinquency_status": "upset_sale",
                        "sale_eligible":      "true",
                    })
                    seen.add(pid)
                    count += 1

            # Fall back to raw text scan if no tables extracted
            if not tables:
                text = page.extract_text() or ""
                for line in text.splitlines():
                    pid_m = PARCEL_RE.search(line)
                    if not pid_m:
                        continue
                    pid = pid_m.group(0).replace("-", "")  # normalize to 12-digit DB format
                    if pid in seen:
                        continue

                    amount = 0.0
                    amt_m = AMOUNT_RE.search(line)
                    if amt_m:
                        try:
                            amount = float(amt_m.group(1).replace(",", ""))
                        except ValueError:
                            pass

                    writer.writerow({
                        "parcel_id":          pid,
                        "tax_year":           year,
                        "amount_due":         amount,
                        "delinquency_status": "upset_sale",
                        "sale_eligible":      "true",
                    })
                    seen.add(pid)
                    count += 1
    return count


def fetch_all(out_path: str) -> int:
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers["User-Agent"] = "PropFinder/1.0 public-data-ingestion"
    session.max_redirects = 10

    fieldnames = ["parcel_id", "tax_year", "amount_due", "delinquency_status", "sale_eligible"]

    log(_PREFIX, f"searching for upset sale PDFs: {PRIOR_RESULTS_URL}")
    pdf_entries = _find_pdf_urls(session)

    if not pdf_entries:
        log(_PREFIX, f"WARNING: no upset sale PDFs found — verify {PRIOR_RESULTS_URL}")
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=fieldnames).writeheader()
        return 0

    log(_PREFIX, f"found {len(pdf_entries)} upset sale PDF(s); processing {min(MAX_PDFS, len(pdf_entries))}")

    total = 0
    seen: set[str] = set()
    tmp_path = Path(out_path).parent / "_tax_sale_tmp.pdf"

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        start = time.time()
        for year, url in pdf_entries[:MAX_PDFS]:
            log(_PREFIX, f"downloading {year} PDF: {url}")
            try:
                r = session.get(url, timeout=60, stream=True)
                r.raise_for_status()
            except requests.RequestException as e:
                log(_PREFIX, f"WARNING: download failed for {url}: {e}")
                continue

            content_type = r.headers.get("content-type", "")
            if "pdf" not in content_type and not url.lower().endswith(".pdf"):
                soup = BeautifulSoup(r.text, "lxml")
                pdf_a = soup.find("a", href=re.compile(r"\.pdf", re.IGNORECASE))
                if pdf_a:
                    pdf_url = urljoin(url, pdf_a["href"])
                    log(_PREFIX, f"following viewer to PDF: {pdf_url}")
                    try:
                        r = session.get(pdf_url, timeout=60, stream=True)
                        r.raise_for_status()
                    except requests.RequestException as e:
                        log(_PREFIX, f"WARNING: could not download PDF: {e}")
                        continue
                else:
                    log(_PREFIX, f"WARNING: no PDF found at {url}")
                    continue

            size_kb = 0
            with open(tmp_path, "wb") as tmp:
                for chunk in r.iter_content(chunk_size=8192):
                    tmp.write(chunk)
                    size_kb += len(chunk) // 1024
            log(_PREFIX, f"  downloaded {size_kb:,} KB — parsing...")

            try:
                n = _parse_pdf(tmp_path, year, writer, seen)
                log(_PREFIX, f"  extracted {n} parcel records from {year} PDF")
                total += n
            except Exception as e:
                log(_PREFIX, f"WARNING: PDF parse failed for {url}: {e}")
            finally:
                tmp_path.unlink(missing_ok=True)

    log(_PREFIX, f"wrote {total:,} tax delinquency records → {out_path}  ({elapsed(start)})")
    return total


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/tax_delinquency.csv")
    args = parser.parse_args()
    fetch_all(args.out)
