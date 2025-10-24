import csv
import sys
from collections import defaultdict
import os
import requests
from io import StringIO
import time # Import time for a timestamp in logs

def find_duplicates_in_csv(csv_location, column_name):
    """
    Finds duplicate values in a specific column of a CSV file (local or from URL).
    Writes the duplicate rows to a new file.
    """
    start_time = time.time()
    print(f"[{time.strftime('%H:%M:%S')}] Checking for duplicates in column '{column_name}' from '{csv_location}'...")

    lines = []
    fieldnames = []
    try:
        if csv_location.startswith('http://') or csv_location.startswith('https://'):
            print(f"[{time.strftime('%H:%M:%S')}] Attempting to download CSV from URL...")
            response = requests.get(csv_location)
            response.raise_for_status()
            csv_data = StringIO(response.text)
            reader = csv.DictReader(csv_data)
            fieldnames = reader.fieldnames
            lines = list(reader)
            print(f"[{time.strftime('%H:%M:%S')}] Successfully downloaded and read CSV from URL. Total rows: {len(lines)}")
        else:
            print(f"[{time.strftime('%H:%M:%S')}] Attempting to read CSV from local file system...")
            with open(csv_location, 'r', newline='', encoding='utf-8') as infile:
                reader = csv.DictReader(infile)
                fieldnames = reader.fieldnames
                lines = list(reader)
            print(f"[{time.strftime('%H:%M:%S')}] Successfully read CSV from local file. Total rows: {len(lines)}")
    except FileNotFoundError:
        print(f"[{time.strftime('%H:%M:%S')}] Error: File not found at '{csv_location}'")
        return
    except requests.exceptions.RequestException as e:
        print(f"[{time.strftime('%H:%M:%S')}] Error downloading file: {e}")
        return
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] An error occurred while reading the CSV: {e}")
        return

    if not fieldnames or column_name not in fieldnames:
        print(f"[{time.strftime('%H:%M:%S')}] Error: Column '{column_name}' not found in the CSV file.")
        print(f"[{time.strftime('%H:%M:%S')}] Available columns: {fieldnames}")
        return

    print(f"[{time.strftime('%H:%M:%S')}] Starting duplicate count for column '{column_name}'...")
    # Count occurrences
    seen = defaultdict(int)
    for row in lines:
        value = row.get(column_name)
        if value:
            seen[value] += 1
    
    print(f"[{time.strftime('%H:%M:%S')}] Finished counting. Total unique values in column: {len(seen)}")

    duplicates = {key: count for key, count in seen.items() if count > 1}

    if not duplicates:
        print(f"[{time.strftime('%H:%M:%S')}] No duplicates found.")
    else:
        print(f"[{time.strftime('%H:%M:%S')}] Found {len(duplicates)} duplicate value(s) in column '{column_name}':")
        for value, count in duplicates.items():
            print(f"  - Value: '{value}' | Count: {count}")

        output_filename = f"duplicates_{column_name}.csv"
        print(f"[{time.strftime('%H:%M:%S')}] Writing all rows containing these duplicate values to '{output_filename}'...")
        try:
            with open(output_filename, 'w', newline='', encoding='utf-8') as outfile:
                writer = csv.DictWriter(outfile, fieldnames=fieldnames)
                writer.writeheader()

                for row in lines:
                    if row.get(column_name) in duplicates:
                        writer.writerow(row)
            print(f"[{time.strftime('%H:%M:%S')}] Successfully wrote {len(duplicates)} sets of duplicate rows to '{output_filename}'.")
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] An error occurred while writing the output file: {e}")
    
    end_time = time.time()
    print(f"[{time.strftime('%H:%M:%S')}] Script finished in {end_time - start_time:.2f} seconds.")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python check_csv_duplicates.py <path_or_url_to_csv> <column_name>")
        sys.exit(1)
    
    csv_location_arg = sys.argv[1]
    column_to_check_arg = sys.argv[2]
    find_duplicates_in_csv(csv_location_arg, column_to_check_arg)
