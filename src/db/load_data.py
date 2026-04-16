"""Script to load Olist CSV files into the PostgreSQL database."""

import os
import pandas as pd
from sqlalchemy import create_engine, text
from loguru import logger
from src.config import get_settings

DATASET_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "datasets")

# Mapping: CSV filename → target table name (ORDER MATTERS for FKs)
CSV_TABLE_MAP = {
    "olist_customers_dataset": "olist_customers",
    "olist_sellers_dataset": "olist_sellers",
    "olist_products_dataset": "olist_products",
    "product_category_name_translation": "product_category_name_translation",
    "olist_orders_dataset": "olist_orders",
    "olist_order_items_dataset": "olist_order_items",
    "olist_order_payments_dataset": "olist_order_payments",
    "olist_order_reviews_dataset": "olist_order_reviews",
    "olist_geolocation_dataset": "olist_geolocation",
}

# Primary keys to ensure no duplicates during ingestion
TABLE_PK_MAP = {
    "olist_customers": ["customer_id"],
    "olist_sellers": ["seller_id"],
    "olist_products": ["product_id"],
    "olist_orders": ["order_id"],
    "olist_order_items": ["order_id", "order_item_id"],
    "olist_order_payments": ["order_id", "payment_sequential"],
    "olist_order_reviews": ["review_id"],
    "product_category_name_translation": ["product_category_name"],
}


def load_csv_to_postgres():
    """Read every Olist CSV and bulk-insert into PostgreSQL."""
    settings = get_settings()
    engine = create_engine(settings.database_url)

    # 1. Clear existing data in reverse order to respect FKs
    with engine.connect() as conn:
        logger.info("Clearing existing data...")
        tables = list(CSV_TABLE_MAP.values())
        tables.reverse()
        for table in tables:
            conn.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
        conn.commit()

    # 2. Ingest new data
    with engine.connect() as conn:
        logger.info("Starting ingestion (bypassing FK constraints)...")
        # Disable FK checks for this session
        conn.execute(text("SET session_replication_role = 'replica'"))
        
        for csv_name, table_name in CSV_TABLE_MAP.items():
            csv_path = os.path.join(DATASET_DIR, f"{csv_name}.csv")

            if not os.path.exists(csv_path):
                logger.warning(f"CSV not found, skipping: {csv_path}")
                continue

            logger.info(f"Loading {csv_name}.csv → {table_name} ...")
            df = pd.read_csv(csv_path)

            # Fix common misspellings in Olist dataset to match our clean schema
            if table_name == "olist_products":
                df = df.rename(columns={
                    "product_name_lenght": "product_name_length",
                    "product_description_lenght": "product_description_length"
                })
            
            # Remove duplicates by PK to avoid IntegrityError
            if table_name in TABLE_PK_MAP:
                pk_cols = TABLE_PK_MAP[table_name]
                before_count = len(df)
                df = df.drop_duplicates(subset=pk_cols)
                after_count = len(df)
                if before_count > after_count:
                    logger.warning(f"  ⚠ Dropped {before_count - after_count} duplicate rows from {table_name}")

            # Use 'append' to preserve the schema created by 01_create_tables.sql
            df.to_sql(table_name, conn, if_exists="append", index=False)
            logger.success(f"  ✓ {len(df):,} rows inserted into '{table_name}'")

        # Re-enable FK checks
        conn.execute(text("SET session_replication_role = 'origin'"))
        conn.commit()

    logger.info("All datasets loaded successfully.")


if __name__ == "__main__":
    load_csv_to_postgres()
