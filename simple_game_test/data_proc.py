
import sqlite3
import pandas as pd
import dill as pickle
import sys
from pathlib import Path

# Add the project root directory to Python path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.group_teaching.codes.simple_rl import *


def print_table_data(database_file):
    try:
        # Connect to the database
        conn = sqlite3.connect(database_file)
        cursor = conn.cursor()

        # Fetch all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        if not tables:
            print("No tables found in the database.")
            return

        # Iterate through each table and print its data
        for table in tables:
            table_name = table[0]
            print(f"\nTable: {table_name}")
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()

            # Fetch column names
            column_names = [description[0] for description in cursor.description]
            print(" | ".join(column_names))  # Print column headers

            # Print each row
            for row in rows:
                print(" | ".join(map(str, row)))

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        # Close the database connection
        if conn:
            conn.close()




def convert_db_to_excel(database_file, output_excel_file):
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(database_file)
        
        # Fetch all table names
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        if not tables:
            print("No tables found in the database.")
            return

        # Create a Pandas Excel writer
        with pd.ExcelWriter(output_excel_file, engine='openpyxl') as writer:
            # Iterate through each table and save its data to a separate Excel sheet
            for table in tables:
                table_name = table[0]
                print(f"Exporting table: {table_name}")

                # Escape table names that may contain reserved keywords
                escaped_table_name = f"[{table_name}]"

                # Read table data
                cursor.execute(f"SELECT * FROM {escaped_table_name}")
                rows = cursor.fetchall()

                # Fetch column names
                column_names = [description[0] for description in cursor.description]
                print(" | ".join(column_names))  # Print column headers

                # Process rows to deserialize PickleType columns
                processed_rows = []
                for row in rows:
                    processed_row = []
                    for value in row:
                        # Attempt to deserialize pickle data, otherwise keep the original value
                        if isinstance(value, bytes):
                            try:
                                processed_value = pickle.loads(value)
                            except (pickle.UnpicklingError, EOFError, AttributeError):
                                processed_value = value  # Leave as-is if unpickling fails
                        else:
                            processed_value = value
                        processed_row.append(processed_value)
                    processed_rows.append(processed_row)

                # Convert to a DataFrame
                df = pd.DataFrame(processed_rows, columns=column_names)

                # Write DataFrame to an Excel sheet
                df.to_excel(writer, sheet_name=table_name, index=False)
        
        print(f"Database converted to Excel file: {output_excel_file}")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        # Close the database connection
        if conn:
            conn.close()

# Replace 'app.db' with your database file and 'output.xlsx' with the desired Excel file name
convert_db_to_excel('app.db', 'output.xlsx')


# Replace 'app.db' with your database file path if needed
# print_table_data('app.db')
