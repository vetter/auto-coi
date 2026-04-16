#!/usr/bin/env python3
# ==============================================================================
# Automated COA / COI List Generator for NSF & DOE Proposals
# ==============================================================================
# "Because there are better ways to use your time than hunting and pecking
#  your COI list..."
#
# Credit: Jeffrey S. Vetter / Advanced Computing Systems Research
# ==============================================================================

import argparse
import re
import sys
from datetime import datetime

import pandas as pd
import requests
from dateutil.relativedelta import relativedelta

ACRONYMS = {
    "ORNL": "Oak Ridge National Laboratory",
    "ANL": "Argonne National Laboratory",
    "LBNL": "Lawrence Berkeley National Laboratory",
    "LLNL": "Lawrence Livermore National Laboratory",
    "LANL": "Los Alamos National Laboratory",
    "PNNL": "Pacific Northwest National Laboratory",
    "BNL": "Brookhaven National Laboratory",
    "SNLA": "Sandia National Laboratories",
    "SNL": "Sandia National Laboratories",
    "INL": "Idaho National Laboratory",
    "NREL": "National Renewable Energy Laboratory",
    "Fermilab": "Fermi National Accelerator Laboratory",
    "MIT": "Massachusetts Institute of Technology",
    "CMU": "Carnegie Mellon University",
    "GT": "Georgia Institute of Technology",
    "UCLA": "University of California, Los Angeles",
    "UCB": "University of California, Berkeley",
    "UCSD": "University of California, San Diego",
}


def warn(msg):
    print(f"\033[93m[WARNING]\033[0m {msg}")


def error_msg(msg):
    print(f"\033[91m[ERROR]\033[0m {msg}")


def expand_affiliation(raw_name):
    if not raw_name:
        return "Unknown / Independent", []

    words = raw_name.replace(",", "").split()
    expanded_words = []
    notes = []

    for w in words:
        clean_w = w.strip("()")
        if clean_w in ACRONYMS:
            expanded_words.append(ACRONYMS[clean_w])
            notes.append(f"Expanded acronym: {clean_w}")
        else:
            expanded_words.append(w)

    return " ".join(expanded_words), notes


def get_author_name(orcid_id):
    url = f"https://api.openalex.org/authors/https://orcid.org/{orcid_id}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json().get("display_name", orcid_id)
    except requests.exceptions.RequestException:
        pass
    return orcid_id


def get_recent_coauthors(orcid_id, target_name, months_lookback, email, verbose):
    def log(msg):
        if verbose:
            print(f"[DEBUG] {msg}")

    cutoff_date = (datetime.now() - relativedelta(months=months_lookback)).strftime(
        "%Y-%m-%d"
    )
    log(f"Fetching publications for {target_name} ({orcid_id}) since {cutoff_date}...")

    base_url = "https://api.openalex.org/works"
    coauthors = []

    cursor = "*"
    has_more = True
    page_count = 1

    while has_more:
        log(f"Fetching page {page_count}...")
        params = {
            "filter": f"author.orcid:https://orcid.org/{orcid_id},from_publication_date:{cutoff_date}",
            "cursor": cursor,
            "per-page": 50,
        }
        if email:
            params["mailto"] = email

        try:
            response = requests.get(base_url, params=params, timeout=30)
            if response.status_code != 200:
                print(
                    f"Error fetching data for {orcid_id}: {response.status_code} - {response.text}"
                )
                break
        except requests.exceptions.RequestException as e:
            print(f"Network error during API request: {e}")
            break

        data = response.json()
        results = data.get("results", [])

        if not results:
            break

        for work in results:
            full_pub_date = work.get("publication_date", "Unknown")
            pub_year = (
                full_pub_date.split("-")[0] if full_pub_date != "Unknown" else "Unknown"
            )

            authors_list = work.get("authorships", [])

            for authorship in authors_list:
                author = authorship.get("author", {})
                author_name = author.get("display_name")

                if not author_name:
                    continue

                author_orcid_raw = author.get("orcid") or ""

                if (
                    f"orcid.org/{orcid_id}" in author_orcid_raw
                    or author_name == target_name
                ):
                    continue

                parts = author_name.split()
                last_name = parts[-1] if parts else ""
                first_name = " ".join(parts[:-1]) if len(parts) > 1 else ""

                clean_orcid = (
                    author_orcid_raw.replace("https://orcid.org/", "")
                    if author_orcid_raw
                    else ""
                )

                institutions = authorship.get("institutions", [])
                affil_strings = []
                all_notes = []

                if not institutions:
                    affil_strings.append("Unknown / Independent")
                    all_notes.append("Missing affiliation data")
                else:
                    for inst in institutions:
                        raw_inst_name = inst.get("display_name", "")
                        expanded_inst, notes = expand_affiliation(raw_inst_name)
                        affil_strings.append(expanded_inst)
                        all_notes.extend(notes)

                final_affiliation = " / ".join(affil_strings)
                final_comments = "; ".join(set(all_notes))

                coauthors.append(
                    {
                        "Senior/key person linked to": target_name,
                        "First Name": first_name,
                        "Last Name": last_name,
                        "ORCiD": clean_orcid,
                        "Institutional affiliation": final_affiliation,
                        "Reason": "co-author",
                        "Year last applied": pub_year,
                        "COMMENT": final_comments,
                        "_FullDateForSorting": full_pub_date,
                    }
                )

        cursor = data.get("meta", {}).get("next_cursor")
        has_more = bool(cursor)
        page_count += 1

    return coauthors


def main():
    parser = argparse.ArgumentParser(
        description="Automated COI list generator for NSF/DOE using the OpenAlex API.",
        epilog="Example: python coa_generator.py 0000-0002-2449-6720 0000-0001-2345-6789 -o team_coi.csv",
    )

    parser.add_argument(
        "orcids", nargs="+", help="REQUIRED: One or more ORCID IDs separated by spaces"
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output CSV filename (default: <LastName>-<YYYY-MM-DD>-CoAuthors.csv)",
    )
    parser.add_argument(
        "-m",
        "--months",
        type=int,
        default=48,
        help="Lookback period in months (default: 48 for NSF/DOE)",
    )
    parser.add_argument(
        "-e",
        "--email",
        default=None,
        help="Email address for OpenAlex 'polite pool' (faster API responses)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output for debugging and progress tracking",
    )
    parser.add_argument(
        "--no-dedup",
        action="store_true",
        help="Disable deduplication and keep all authorship instances",
    )

    args = parser.parse_args()

    print(
        f"\n=============================================================================="
    )
    print(f"Automated COA / COI List Generator")
    print(
        f"==============================================================================\n"
    )

    # --- ORCID Validation Engine ---
    valid_orcids = []
    # Standard 16-digit ORCID format, with the final digit potentially being an 'X'
    orcid_pattern = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")

    for maybe_orcid in args.orcids:
        if orcid_pattern.match(maybe_orcid):
            valid_orcids.append(maybe_orcid)
        else:
            error_msg(
                f"'{maybe_orcid}' does not match the ORCID format (XXXX-XXXX-XXXX-XXXX). Skipping."
            )

    if not valid_orcids:
        error_msg("No valid ORCIDs were provided. Exiting.")
        sys.exit(1)
    # -------------------------------

    all_coauthors = []
    output_filename = args.output

    for i, orcid in enumerate(valid_orcids):
        print(f"Processing target ORCID: {orcid}...")
        target_name = get_author_name(orcid)
        if args.verbose:
            print(f"Target author identified as: {target_name}")

        if i == 0 and output_filename is None:
            raw_last_name = target_name.split()[-1] if target_name else "Author"
            safe_last_name = "".join(char for char in raw_last_name if char.isalnum())
            today_str = datetime.now().strftime("%Y-%m-%d")
            output_filename = f"{safe_last_name}-{today_str}-CoAuthors.csv"
            if args.verbose:
                print(f"[DEBUG] Default output filename set to: {output_filename}")

        records = get_recent_coauthors(
            orcid, target_name, args.months, args.email, args.verbose
        )
        all_coauthors.extend(records)
        print(f"Finished fetching records for {target_name}.\n")

    df = pd.DataFrame(all_coauthors)

    if not df.empty:
        if args.verbose:
            print("Consolidating datasets and sorting by true publication date...")
        df = df.sort_values(by="_FullDateForSorting", ascending=False)

        print("Running Data Hygiene Checks...")
        conflict_count = 0

        unknowns = df[df["Institutional affiliation"] == "Unknown / Independent"]
        for _, row in unknowns.iterrows():
            warn(
                f"Missing affiliation for: {row['First Name']} {row['Last Name']} (Pub Date: {row['_FullDateForSorting'][:4]})"
            )

        orcid_groups = df[df["ORCiD"] != ""].groupby("ORCiD")
        for orcid, group in orcid_groups:
            unique_affiliations = group["Institutional affiliation"].unique()
            if len(unique_affiliations) > 1:
                fname = group.iloc[0]["First Name"]
                lname = group.iloc[0]["Last Name"]
                warn(
                    f"Affiliation change for {fname} {lname} (ORCID: {orcid}). Found: {', '.join(unique_affiliations)}. Auto-resolving to most recent."
                )
                conflict_count += 1

        no_orcid_df = df[df["ORCiD"] == ""]
        name_groups = no_orcid_df.groupby(["First Name", "Last Name"])
        for (fname, lname), group in name_groups:
            unique_affiliations = group["Institutional affiliation"].unique()
            if len(unique_affiliations) > 1:
                warn(
                    f"Potential conflict for {fname} {lname} (No ORCID). Found: {', '.join(unique_affiliations)}. Keeping ALL variants for manual review."
                )
                conflict_count += 1

        if conflict_count == 0 and unknowns.empty:
            print("  -> No conflicts or missing fields detected.\n")
        else:
            print("")

        if not args.no_dedup:
            if args.verbose:
                print("Deduplicating dataset across all ORCIDs...")
            df["DedupKey"] = df.apply(
                lambda row: (
                    row["ORCiD"]
                    if row["ORCiD"] != ""
                    else f"{row['First Name']}|{row['Last Name']}|{row['Institutional affiliation']}"
                ),
                axis=1,
            )
            df = df.drop_duplicates(subset=["DedupKey"], keep="first")
            df = df.drop(columns=["DedupKey"])

        df = df.drop(columns=["_FullDateForSorting"])
        df = df.sort_values(by="Last Name")

        cols = [
            "Senior/key person linked to",
            "First Name",
            "Last Name",
            "ORCiD",
            "Institutional affiliation",
            "Reason",
            "Year last applied",
            "COMMENT",
        ]
        df = df[cols]

        df.to_csv(output_filename, index=False)
        print(f"Success! Exported {len(df)} co-author records to '{output_filename}'.")
    else:
        print("No co-authors found in the specified timeframe.")


if __name__ == "__main__":
    main()
