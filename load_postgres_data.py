import os
from sqlalchemy import create_engine, text
from datetime import datetime
from urllib.parse import urlparse
from env_loader import load_environment

load_environment()

# List of PostgreSQL database URIs from environment
DB_URIS = [
    os.getenv("VPS_DB_URI_BD_CARS"),
    os.getenv("VPS_DB_URI_COM"),
    os.getenv("VPS_DB_URI_CARS_CONTENT"),
]


async def load_postgres_data_dbs(): # Changed to a regular function
    # Directory to save output files
    UPLOAD_DIR = "uploads"
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    for DB_URI in DB_URIS:
        if not DB_URI:
            print("Skipping empty DB URI...")
            continue
        try:
            engine = create_engine(DB_URI)
            db_url = urlparse(DB_URI.replace("postgresql+psycopg2", "postgresql"))
            db_name = db_url.path.lstrip("/")

            with engine.connect() as connection:
                # Get table names
                tables_query = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                  AND table_type = 'BASE TABLE';
                """)
                table_names = [row[0] for row in connection.execute(tables_query).fetchall()]

                content_lines = [
                    f"Database Export Timestamp: {datetime.now().isoformat()}",
                    f"Database: {db_name}",
                    "=" * 40 + "\n"
                ]

                if not table_names:
                    content_lines.append("No tables found in this database.\n")

                for table_name in table_names:
                    content_lines.append(f"\nTable: {table_name}")
                    content_lines.append("-" * 30)

                    fetch_data_query = text(f"SELECT * FROM {table_name};")
                    result = connection.execute(fetch_data_query)
                    rows = result.mappings().all()

                    if rows:
                        content_lines.append(f"Row Count: {len(rows)}")
                        for idx, row in enumerate(rows, 1):
                            content_lines.append(f"  Row {idx}:")
                            for col, val in row.items():
                                content_lines.append(f"    Column: {col} | Value: {val}")
                            content_lines.append("    ---")
                    else:
                        content_lines.append("  Table is empty.")
                    content_lines.append("")

                # Write to file
                timestamp_str = datetime.now().strftime("%Y-%m-%d_%H%M%S")
                output_file = os.path.join(UPLOAD_DIR, f"{db_name}_{timestamp_str}_dump.txt")
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write("\n".join(content_lines))


        except Exception as e:
            print(f"Error with  (URI: {DB_URI}): {e}")
            # The code will now continue to the next DB_URI

    return True # Returns True after trying all URIs
