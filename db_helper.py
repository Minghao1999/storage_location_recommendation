import sqlite3

DB_FILE = "database.db"


def get_connection():
    return sqlite3.connect(DB_FILE)


def get_sku_info(sku):
    sku = str(sku).strip().upper()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT SKU, 长, 宽, 高, 最长边
        FROM sku_info
        WHERE SKU = ?
    """, (sku,))

    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return {
        "SKU": row[0],
        "长": row[1],
        "宽": row[2],
        "高": row[3],
        "最长边": row[4]
    }