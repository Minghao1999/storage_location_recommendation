import tkinter as tk
from tkinter import filedialog, messagebox
from heatmap import run_heatmap

inventory_file = None
empty_file = None


def select_inventory():
    global inventory_file
    inventory_file = filedialog.askopenfilename(filetypes=[("Excel","*.xlsx")])

    if inventory_file:
        inventory_label.config(
            text="✔ " + inventory_file.split("/")[-1],
            fg="green"
        )


def select_empty():
    global empty_file
    empty_file = filedialog.askopenfilename(filetypes=[("Excel","*.xlsx")])

    if empty_file:
        empty_label.config(
            text="✔ " + empty_file.split("/")[-1],
            fg="green"
        )


def run():
    if not inventory_file or not empty_file:
        messagebox.showerror("Error","Please upload both files")
        return

    run_heatmap(inventory_file, empty_file)


root = tk.Tk()
root.title("Warehouse Heatmap Tool")
root.geometry("400x200")

tk.Button(root,text="Upload Inventory",command=select_inventory).pack(pady=10)

inventory_label = tk.Label(root,text="No inventory file selected",fg="gray")
inventory_label.pack()

tk.Button(root,text="Upload Empty Slots",command=select_empty).pack(pady=10)

empty_label = tk.Label(root,text="No empty slots file selected",fg="gray")
empty_label.pack()

tk.Button(root,text="Generate Heatmap",command=run,bg="green",fg="white").pack(pady=20)

root.mainloop()