import requests
import os

def download_file(file_id, output):

    url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"

    r = requests.get(url)

    with open(output, "wb") as f:
        f.write(r.content)


def download_daily_files():

    inventory_id = "1Upbjv3sonyg40F9Rk1wTp7IltCK4ROB-"
    empty_id = "1NV_g66yMuLzttr2X7fvx71oMjTpPlQ2d"

    # 创建 gdrive 文件夹（如果不存在）
    os.makedirs("gdrive", exist_ok=True)

    inventory_path = os.path.join("gdrive", "inventory.xlsx")
    empty_path = os.path.join("gdrive", "empty.xlsx")

    download_file(inventory_id, inventory_path)
    download_file(empty_id, empty_path)

    return inventory_path, empty_path