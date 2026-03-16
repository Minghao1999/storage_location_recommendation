from db_helper import get_sku_info
import pandas as pd

def get_remaining_space(df):
    capacity = 120

    occupied = df[df["status"] == "occupied"].copy()

    for col in ["长", "宽", "高"]:
        occupied[col] = pd.to_numeric(occupied[col], errors="coerce").fillna(0)

    occupied["占用长度"] = occupied[["长", "宽", "高"]].max(axis=1)

    used = occupied.groupby(["A", "R", "L"])["占用长度"].sum()

    all_slots = df.groupby(["A", "R", "L"]).size().index

    remaining = {}
    for slot in all_slots:
        used_len = used.get(slot, 0)
        remaining[slot] = capacity - used_len

    return remaining


def find_location_by_sku(df, inventory_all, sku):

    sku = sku.strip().upper()

    # ===== 从数据库查SKU =====
    sku_info = get_sku_info(sku)

    if sku_info is None:
        return None, None, None

    item_len = sku_info["最长边"]

    remaining = get_remaining_space(df)

    # ===== Excel库存 =====
    sku_locations = df[
        df["SKU"].astype(str).str.strip().str.upper() == sku
    ]

    warehouse_has_sku = not sku_locations.empty

    # ===== 仓库有SKU =====
    if warehouse_has_sku:

        L1_has_sku = any(sku_locations["L"] == 1)

        # L1有 → L2+
        if L1_has_sku:

            for level in [2,3,4]:

                for (A,R,L), space in remaining.items():

                    if L == level and space >= item_len:
                        return f"A{A}-R{R}-L{L}", item_len, space

        # L1没有 → L1
        else:

            for (A,R,L), space in remaining.items():

                if L == 1 and space >= item_len:
                    return f"A{A}-R{R}-L{L}", item_len, space

    # ===== 仓库没有SKU =====
    else:

        for (A,R,L), space in remaining.items():

            if L == 1 and space >= item_len:
                return f"A{A}-R{R}-L{L}", item_len, space

    return None, item_len, None

def find_location_by_size(df, item_len):

    remaining = get_remaining_space(df)

    # 找能放下的储位
    valid_slots = {k:v for k,v in remaining.items() if v >= item_len}

    if not valid_slots:
        return None, item_len, None

    # 优先 L1
    L1_slots = {k:v for k,v in valid_slots.items() if k[2] == 1}

    if L1_slots:
        best = min(L1_slots, key=L1_slots.get)
    else:
        best = min(valid_slots, key=valid_slots.get)

    A,R,L = best

    return f"A{A}-R{R}-L{L}", item_len, valid_slots[best]