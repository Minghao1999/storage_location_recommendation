import os
import glob
import sqlite3
import pandas as pd

DB_FILE = "database.db"
EXCEL_FOLDER = "../database"


def normalize_columns(df):

    # 统一列名
    df = df.rename(columns={
    "FOP商品编码": "SKU",
    "客户SKU": "CLIENT_SKU",
    "商品名称": "商品名称",
    "仓库采集商品长度": "长",
    "仓库采集商品宽度": "宽",
    "仓库采集商品高度": "高"
})

    needed = ["SKU", "CLIENT_SKU", "商品名称", "长", "宽", "高"]

    df = df[needed].copy()

    # 数据清洗
    df["SKU"] = df["SKU"].astype(str).str.strip().str.upper()
    df["CLIENT_SKU"] = df["CLIENT_SKU"].astype(str).str.strip().str.upper()
    df["商品名称"] = df["商品名称"].astype(str).str.strip()

    df["长"] = pd.to_numeric(df["长"], errors="coerce")
    df["宽"] = pd.to_numeric(df["宽"], errors="coerce")
    df["高"] = pd.to_numeric(df["高"], errors="coerce")

    # 删除空值
    df = df.dropna(subset=["SKU", "长", "宽", "高"])

    # 最长边
    df["最长边"] = df[["长", "宽", "高"]].max(axis=1)

    return df


def main():

    excel_files = glob.glob(os.path.join(EXCEL_FOLDER, "*.xlsx"))

    if not excel_files:
        print("没有找到 Excel 文件")
        return

    all_data = []

    for file in excel_files:

        print(f"正在读取: {file}")

        df = pd.read_excel(file)

        df = normalize_columns(df)

        all_data.append(df)

    final_df = pd.concat(all_data, ignore_index=True)

    # SKU去重
    final_df = final_df.drop_duplicates(subset=["SKU"])

    conn = sqlite3.connect(DB_FILE)

    final_df.to_sql("sku_info", conn, if_exists="replace", index=False)

    # 建索引
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sku ON sku_info (SKU)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_client_sku ON sku_info (CLIENT_SKU)")
    
    conn.commit()
    conn.close()

    print(f"数据库已生成: {DB_FILE}")
    print(f"总SKU数量: {len(final_df)}")


if __name__ == "__main__":
    main()