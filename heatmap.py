from data_loader import load_data
from sku_finder import find_location_by_sku, find_location_by_size
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
from matplotlib.widgets import RadioButtons, Button
import tkinter as tk
from db_helper import get_sku_info
from matplotlib.patches import Rectangle



def run_heatmap(inventory_path, empty_path):

    # 读取数据
    df, inventory_all = load_data(inventory_path, empty_path)

    # 颜色
    cmap = LinearSegmentedColormap.from_list(
        "warehouse",
        ["green","yellow","red"]
    )

    capacity_cmap = ListedColormap([
        "red",
        "orange",
        "lightgreen",
        "green"
    ])

    def compute_heatmap(data):

        total = data.groupby(["A", "R"]).size().unstack()
        occ = data[data["status"] == "occupied"].groupby(["A", "R"]).size().unstack()

        occ = occ.reindex(index=total.index, columns=total.columns, fill_value=0)

        util = occ / total
        util[(total > 0) & util.isna()] = 0

        heatmap = util.T
        heatmap = heatmap.sort_index()
        heatmap = heatmap.iloc[::-1]

        return heatmap

    fig = plt.figure(figsize=(20,10))

    ax_result = plt.axes([0.80,0.68,0.15,0.10])
    result_text = ax_result.text(
        0.5,0.5,"",
        ha="center",
        va="center",
        fontsize=12,
        bbox=dict(boxstyle="round", fc="white", ec="black")
    )
    ax_result.axis("off")


    ax_heatmap = plt.axes([0.25,0.1,0.65,0.8])
    ax_L = plt.axes([0.92,0.1,0.05,0.8])
    ax_menu = plt.axes([0.05,0.4,0.12,0.25])

    # 查询按钮
    axbutton = plt.axes([0.80,0.86,0.15,0.04])
    search_button = Button(axbutton, "Search")
    def ask_sku_popup():
        root = tk.Tk()
        root.withdraw() 
        popup = tk.Toplevel(root)
        popup.title("Enter SKU")
        popup.geometry("300x120")

        tk.Label(popup, text="SKU:").pack(pady=5)

        entry = tk.Entry(popup, width=30)
        entry.pack(pady=5)
        entry.focus_set()

        def select_all_on_double_click(event):
            widget = event.widget
            widget.after(1, lambda: widget.select_range(0, 'end'))
            widget.after(1, lambda: widget.icursor('end'))
            return "break"

        def select_all_on_ctrl_a(event):
            widget = event.widget
            widget.select_range(0, 'end')
            widget.icursor('end')
            return "break"

        entry.bind("<Double-Button-1>", select_all_on_double_click)
        entry.bind("<Control-a>", select_all_on_ctrl_a)
        entry.bind("<Control-A>", select_all_on_ctrl_a)

        result = {"value": None}

        def confirm():
            result["value"] = entry.get().strip()
            popup.destroy()

        tk.Button(popup, text="Confirm", command=confirm).pack(pady=8)
        entry.bind("<Return>", lambda event: confirm())

        popup.wait_window()

        return result["value"]
    axbutton.set_visible(False)

    current_mode = "Total"

    current_heatmap_data = compute_heatmap(df)

    annot_box = None

    sns.heatmap(
        current_heatmap_data,
        cmap=cmap,
        linewidths=0.3,
        annot=False,
        vmin=0,
        vmax=1,
        ax=ax_heatmap,
        cbar=True
    )

    annot_box = ax_heatmap.annotate(
        "",
        xy=(0,0),
        xytext=(20,20),
        textcoords="offset points",
        bbox=dict(boxstyle="round", fc="white", ec="black"),
        arrowprops=dict(arrowstyle="->")
    )

    annot_box.set_visible(False)

    highlight_rect = None

    def highlight_location(location):

        nonlocal highlight_rect

        if location is None:
            return

        try:
            parts = location.split("-")
            A = int(parts[0].replace("A",""))
            R = int(parts[1].replace("R",""))

            col = list(current_heatmap_data.columns).index(A)
            row = list(current_heatmap_data.index).index(R)

        except:
            return

        # 删除旧框
        if highlight_rect:
            highlight_rect.remove()

        highlight_rect = Rectangle(
            (col, row),
            1,
            1,
            fill=False,
            edgecolor="blue",
            linewidth=3
        )

        ax_heatmap.add_patch(highlight_rect)

        fig.canvas.draw_idle()

    ax_heatmap.set_title("Warehouse Utilization (Total)")
    ax_heatmap.set_xlabel("A Row")
    ax_heatmap.set_ylabel("R Segment")

    ax_L.axis("off")

    def onhover(event):

        nonlocal annot_box, current_mode, current_heatmap_data

        if event.inaxes != ax_heatmap:
            annot_box.set_visible(False)
            fig.canvas.draw_idle()
            return

        if event.xdata is None or event.ydata is None:
            return

        col = int(event.xdata)
        row = int(event.ydata)

        if col < 0 or row < 0:
            return

        if col >= len(current_heatmap_data.columns) or row >= len(current_heatmap_data.index):
            return

        A = current_heatmap_data.columns[col]
        R = current_heatmap_data.index[row]

        if current_mode != "Total":

            level = int(current_mode.replace("L",""))

            subset = df[
                (df["A"] == A) &
                (df["R"] == R) &
                (df["L"] == level)
            ]
            # ===== 如果没有储位 =====
            if subset.empty:

                annot_box.xy = (col + 0.5, row + 0.5)
                annot_box.set_text(
                    f"Location: A{A}-R{R}\n\nNo Slot"
                )
                annot_box.set_visible(True)

                fig.canvas.draw_idle()
                return
            # ===== 正常计算 =====
            occupied = subset[subset["status"] == "occupied"].copy()
            used_length = occupied[["长", "宽", "高"]].max(axis=1).sum()
            capacity = 120
            remaining = capacity - used_length

            if remaining < 0:
                remaining = 0

            pallet_size = 40
            capacity_left = int(remaining // pallet_size)

            if capacity_left == 1:
                pallet_text = "1 pallet"
            else:
                pallet_text = f"{capacity_left} pallets"

            text = (
                f"Location: A{A}-R{R}\n\n"
                f"Used length: {used_length:.0f}\" \n"
                f"Remaining: {remaining:.0f}\" \n\n"
                f"Capacity left:\n"
                f"{pallet_text}"
            )

            annot_box.xy = (col + 0.5, row + 0.5)
            annot_box.set_text(text)
            annot_box.set_visible(True)

            fig.canvas.draw_idle()
            return

        # ===== TOTAL MODE =====

        annot_box.set_visible(False)

        subset = df[(df["A"] == A) & (df["R"] == R)]

        occ_L = subset[subset["status"]=="occupied"].groupby("L").size()
        total_L = subset.groupby("L").size()

        util_L = (occ_L / total_L).fillna(0)
        util_L = util_L.sort_index()

        ax_L.clear()

        if len(util_L) == 0:

            ax_L.text(0.5,0.5,"No Slots",ha="center",va="center")
            ax_L.axis("off")

        else:

            L_data = util_L.values.reshape(-1,1)

            sns.heatmap(
                L_data,
                cmap=cmap,
                linewidths=0.5,
                annot=False,
                vmin=0,
                vmax=1,
                yticklabels=util_L.index,
                ax=ax_L,
                cbar=False
            )

            ax_L.set_title(f"A{A}-R{R}")
            ax_L.set_ylabel("L")

        fig.canvas.draw_idle()

    fig.canvas.mpl_connect("motion_notify_event", onhover)

    levels = ["Total"] + [f"L{i}" for i in sorted(df["L"].unique())]

    radio = RadioButtons(ax_menu, levels)

    def compute_capacity_heatmap(data):

        capacity = 120
        pallet_size = 40

        # 真实存在的储位位置
        total = data.groupby(["A", "R"]).size().unstack()

        # 已占用长度
        occupied = data[data["status"] == "occupied"].copy()
        used_per_item = occupied[["长", "宽", "高"]].max(axis=1)
        occupied = occupied.assign(占用长度=used_per_item)

        used = occupied.groupby(["A", "R"])["占用长度"].sum().unstack()
        # 对齐到真实存在的位置
        used = used.reindex(index=total.index, columns=total.columns)

        # 只把“存在但没货”的位置补成 0
        used = used.mask(total.notna() & used.isna(), 0)

        remaining = capacity - used
        remaining[remaining < 0] = 0

        capacity_left = (remaining // pallet_size)

        # 不存在的位置保持 NaN
        capacity_left = capacity_left.where(total.notna())

        heatmap = capacity_left.T
        heatmap = heatmap.sort_index()
        heatmap = heatmap.iloc[::-1]

        return heatmap

    def update(label):

        nonlocal current_mode, annot_box, current_heatmap_data

        current_mode = label

        ax_heatmap.clear()

        for cbar in fig.axes:
            if cbar not in [ax_heatmap, ax_L, ax_menu, axbutton, ax_result]:
                fig.delaxes(cbar)

        if label == "Total":
            data = df
            ax_L.axis("off")
            axbutton.set_visible(False)
        else:
            level = int(label.replace("L",""))
            data = df[df["L"] == level]
            ax_L.clear()
            ax_L.axis("off")
            axbutton.set_visible(True)

        if label == "Total":
            current_heatmap_data = compute_heatmap(data)
            cmap_used = cmap
            vmin = 0
            vmax = 1
        else:
            current_heatmap_data = compute_capacity_heatmap(data)
            cmap_used = capacity_cmap
            vmin = 0
            vmax = 3

        sns.heatmap(
            current_heatmap_data,
            cmap=cmap_used,
            linewidths=0.3,
            annot=False,
            vmin=vmin,
            vmax=vmax,
            ax=ax_heatmap,
            cbar=(label == "Total")
        )

        annot_box = ax_heatmap.annotate(
            "",
            xy=(0,0),
            xytext=(20,20),
            textcoords="offset points",
            bbox=dict(boxstyle="round", fc="white", ec="black"),
            arrowprops=dict(arrowstyle="->")
        )
        annot_box.set_visible(False)

        ax_heatmap.set_title(f"Warehouse Utilization ({label})")
        ax_heatmap.set_xlabel("A Row")
        ax_heatmap.set_ylabel("R Segment")

        fig.canvas.draw_idle()

    radio.on_clicked(update)

    def search_sku(event):

        nonlocal result_text

        if current_mode == "Total":
            result_text.set_text("Switch to L1-L4")
            fig.canvas.draw_idle()
            return

        sku = ask_sku_popup()

        if not sku:
            return

        sku_info = get_sku_info(sku)
        # ===== SKU不存在 =====

        if sku_info is None:

            popup = tk.Toplevel()
            popup.title("New SKU")

            tk.Label(popup,text="Length").grid(row=0,column=0)
            tk.Label(popup,text="Width").grid(row=1,column=0)
            tk.Label(popup,text="Height").grid(row=2,column=0)

            length_entry = tk.Entry(popup)
            width_entry = tk.Entry(popup)
            height_entry = tk.Entry(popup)

            length_entry.grid(row=0,column=1)
            width_entry.grid(row=1,column=1)
            height_entry.grid(row=2,column=1)

            def confirm():

                try:

                    l = float(length_entry.get())
                    w = float(width_entry.get())
                    h = float(height_entry.get())

                    item_len = max(l,w,h)

                    location, item_len, space = find_location_by_size(df, item_len)

                    if location:

                        result_text.set_text(
                            f"New SKU: {sku}\n\n"
                            f"Longest side: {item_len:.0f}\" \n\n"
                            f"Suggested:\n{location}\n\n"
                            f"Remaining:\n{space:.0f}\""
                        )

                        highlight_location(location)

                    else:

                        result_text.set_text(
                            f"New SKU: {sku}\n\n"
                            f"Longest side: {item_len:.0f}\" \n\n"
                            f"No available location"
                        )

                    fig.canvas.draw_idle()

                    popup.destroy()

                except:
                    pass

            tk.Button(popup,text="Confirm",command=confirm).grid(row=3,columnspan=2)

            return

        # ===== 原有SKU =====
        location, item_len, space = find_location_by_sku(df, inventory_all, sku)
        if location:

            result_text.set_text(
                f"SKU: {sku}\n\n"
                f"SKU length: {item_len:.0f}\" \n\n"
                f"Suggested:\n{location}\n\n"
                f"Remaining:\n{space:.0f}\""
            )

            highlight_location(location)

        else:

            result_text.set_text(
                f"SKU: {sku}\n\n"
                f"SKU length: {item_len:.0f}\" \n\n"
                f"No available location"
            )

        fig.canvas.draw_idle()
    search_button.on_clicked(search_sku)

    plt.show()