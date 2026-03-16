import tkinter as tk
from heatmap import run_heatmap
from gdrive.gdrive_loader import download_daily_files


def run():

    try:

        inventory_file, empty_file = download_daily_files()

        run_heatmap(inventory_file, empty_file)

    except Exception as e:

        print(e)


root = tk.Tk()
root.title("Warehouse Heatmap Tool")
root.geometry("300x120")

tk.Button(
    root,
    text="Open Heatmap",
    command=run,
    bg="green",
    fg="white",
    width=20,
    height=2
).pack(pady=30)

root.mainloop()