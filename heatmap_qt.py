import sys
import datetime
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from PySide6.QtWidgets import QDialog, QFormLayout, QLineEdit, QDialogButtonBox
from matplotlib.patches import Rectangle

from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton,
    QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox
)

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from data_loader import load_data
from sku_finder import find_location_by_sku


def log(msg):
    with open("debug.log", "a") as f:
        t = datetime.datetime.now().strftime("%H:%M:%S")
        f.write(f"{t} | {msg}\n")


class HeatmapApp(QWidget):

    def __init__(self, inventory_path, empty_path):
        super().__init__()
        self.current_mode = "Total"

        self.hover_elements = []

        self.df, self.inventory_all = load_data(inventory_path, empty_path)

        self.suggested_location = None
        self.suggested_len = None
        self.putaway_stack = []
        self.current_mode = "Total"

        self.highlight_rect = None

        self.init_ui()
        self.draw_heatmap()

    def init_ui(self):

        self.setWindowTitle("Warehouse Slotting Tool")
        self.resize(1200, 700)

        main_layout = QHBoxLayout()

        # matplotlib figure
        self.figure = Figure(figsize=(12,9))
        self.canvas = FigureCanvas(self.figure)

        main_layout.addWidget(self.canvas, 3)

        # right panel
        right = QVBoxLayout()

        self.sku_input = QLineEdit()
        self.sku_input.returnPressed.connect(self.search_sku)
        self.sku_input.setPlaceholderText("Enter SKU")

        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self.search_sku)

        self.result_label = QLabel("")

        self.confirm_btn = QPushButton("Confirm Putaway")
        self.confirm_btn.clicked.connect(self.confirm_putaway)
        self.confirm_btn.hide()

        self.undo_btn = QPushButton("Undo")
        self.undo_btn.clicked.connect(self.undo_putaway)
        self.undo_btn.hide()

        self.mode_label = QLabel("View Mode")

        self.btn_total = QPushButton("Total")
        self.btn_l1 = QPushButton("L1")
        self.btn_l2 = QPushButton("L2")
        self.btn_l3 = QPushButton("L3")
        self.btn_l4 = QPushButton("L4")

        self.btn_total.clicked.connect(lambda: self.change_mode("Total"))
        self.btn_l1.clicked.connect(lambda: self.change_mode("L1"))
        self.btn_l2.clicked.connect(lambda: self.change_mode("L2"))
        self.btn_l3.clicked.connect(lambda: self.change_mode("L3"))
        self.btn_l4.clicked.connect(lambda: self.change_mode("L4"))

        right.addWidget(self.mode_label)
        right.addWidget(self.btn_total)
        right.addWidget(self.btn_l1)
        right.addWidget(self.btn_l2)
        right.addWidget(self.btn_l3)
        right.addWidget(self.btn_l4)

        right.addWidget(self.sku_input)
        right.addWidget(search_btn)
        right.addWidget(self.result_label)
        right.addWidget(self.confirm_btn)
        right.addWidget(self.undo_btn)

        right.addStretch()

        main_layout.addLayout(right,1)

        self.setLayout(main_layout)

        self.canvas.mpl_connect("motion_notify_event", self.on_hover)

    def draw_side_legend(self, ax):

        colors = ["green", "lightgreen", "orange", "red"]
        labels = ["3 pallets", "2 pallets", "1 pallet", "0"]

        x = 1.02   # ⭐右侧
        y_start = 0.8
        height = 0.08

        for i in range(4):
            rect = Rectangle(
                (x, y_start - i*0.12),
                0.05,
                height,
                transform=ax.transAxes,
                facecolor=colors[i],
                edgecolor="black",
                clip_on=False
            )
            ax.add_patch(rect)

            ax.text(
                x + 0.06,
                y_start - i*0.12 + height/2,
                labels[i],
                transform=ax.transAxes,
                va="center",
                fontsize=9
            )
    
    def closeEvent(self, event):

        if not self.putaway_stack:
            event.accept()
            return

        reply = QMessageBox.question(
            self,
            "Confirm Exit",
            "Closing will lose all putaway records.\n\nAre you sure you want to exit?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()


    def on_hover(self, event):

        # ===== 清 hover =====
        for elem in self.hover_elements:
            try:
                elem.remove()
            except:
                pass

        self.hover_elements = []
        
        if not self.figure.axes:
            return

        ax = self.figure.axes[0]

        if event.inaxes != ax:
            return

        if event.xdata is None or event.ydata is None:
            return

        if self.current_mode == "Total":
            heatmap = self.compute_heatmap()
        else:
            level = int(self.current_mode.replace("L",""))
            heatmap = self.compute_heatmap_level(self.df[self.df["L"]==level])

        col = int(event.xdata)
        row = int(event.ydata)

        if col >= len(heatmap.columns) or row >= len(heatmap.index):
            return

        A = heatmap.columns[col]
        R = heatmap.index[row]

        if self.current_mode == "Total":

            display = []

            for level in [1,2,3,4]:

                subset = self.df[
                    (self.df["A"]==A) &
                    (self.df["R"]==R) &
                    (self.df["L"]==level)
                ]

                if subset.empty:
                    color = "lightgray"
                else:
                    occ = subset[subset["status"]=="occupied"]
                    used = occ[["长","宽","高"]].max(axis=1).sum()
                    remaining = max(0, 120 - used)

                    if remaining >= 120:
                        color = "green"
                    elif remaining >= 80:
                        color = "lightgreen"
                    elif remaining >= 40:
                        color = "orange"
                    else:
                        color = "red"

                display.append((level, color))

            # ===== 画右侧竖条 =====
            ax.set_xlabel(f"A{A}-R{R}", fontsize=10)

            # ===== 连续竖条 =====

            x = 1.02
            y_top = 0.8
            total_height = 0.4   # ⭐整体高度
            block_height = total_height / 4

            # 外框（让它更像一个整体）
            container = Rectangle(
                (x, y_top - total_height),
                0.05,
                total_height,
                transform=ax.transAxes,
                facecolor="none",
                edgecolor="black",
                linewidth=1.5,
                clip_on=False
            )
            ax.add_patch(container)
            self.hover_elements.append(container)

            # 分段填充
            for i, (level, color) in enumerate(display):

                y = y_top - (i+1)*block_height

                rect = Rectangle(
                    (x, y),
                    0.05,
                    block_height,
                    transform=ax.transAxes,
                    facecolor=color,
                    edgecolor="white",
                    linewidth=1.5,   
                    clip_on=False,
                    zorder=5
                )
                ax.add_patch(rect)
                self.hover_elements.append(rect)

                # 文字
                txt = ax.text(
                    x + 0.06,
                    y + block_height/2,
                    f"L{level}",
                    transform=ax.transAxes,
                    va="center",
                    fontsize=9,
                    zorder=6
                )
                self.hover_elements.append(txt)

            self.canvas.draw_idle()
            return

        level = int(self.current_mode.replace("L",""))

        subset = self.df[
            (self.df["A"]==A) &
            (self.df["R"]==R) &
            (self.df["L"]==level)
        ]

        if subset.empty:

            text = (
                f"A{A}-R{R}\n"
                f"No Slot"
            )

            ax.set_xlabel(text, fontsize=10)
            self.canvas.draw_idle()
            return

        occ = subset[subset["status"]=="occupied"]

        used = occ[["长","宽","高"]].max(axis=1).sum()

        remaining = max(0, 120 - used)

        if remaining >= 120:
            pallets = 3
        elif remaining >= 80:
            pallets = 2
        elif remaining >= 40:
            pallets = 1
        else:
            pallets = 0

        text = (
            f"A{A}-R{R}\n"
            f"Used: {used:.0f}\"\n"
            f"Remaining: {remaining:.0f}\"\n"
            f"Pallets fit: {pallets}"
        )
        ax.set_xlabel(text, fontsize=10)

        self.canvas.draw_idle()

    def highlight_location(self, location):

        if not location:
            return

        try:
            parts = location.split("-")
            A = int(parts[0].replace("A",""))
            R = int(parts[1].replace("R",""))
            L = int(parts[2].replace("L",""))

            if self.current_mode == "Total":
                return

            if self.current_mode != "Total":
                current_L = int(self.current_mode.replace("L",""))
                if current_L != L:
                    return

            heatmap = (
                self.compute_heatmap()
                if self.current_mode == "Total"
                else self.compute_heatmap_level(
                    self.df[self.df["L"] == int(self.current_mode.replace("L",""))]
                )
            )

            col = list(heatmap.columns).index(A)
            row = list(heatmap.index).index(R)

        except:
            return

        ax = self.figure.axes[0]

        # 删除旧框
        if self.highlight_rect:
            try:
                if self.highlight_rect.axes:
                    self.highlight_rect.remove()
            except:
                pass

        # 画新框
        self.highlight_rect = Rectangle(
            (col, row),
            1,
            1,
            fill=False,
            edgecolor="blue",
            linewidth=3
        )

        ax.add_patch(self.highlight_rect)

        self.canvas.draw_idle()

    def get_size_input(self):

        dialog = QDialog(self)
        dialog.setWindowTitle("New SKU Size")

        layout = QFormLayout(dialog)

        length_input = QLineEdit()
        width_input = QLineEdit()
        height_input = QLineEdit()

        layout.addRow("Length:", length_input)
        layout.addRow("Width:", width_input)
        layout.addRow("Height:", height_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )

        layout.addWidget(buttons)

        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        if dialog.exec():

            try:
                l = float(length_input.text())
                w = float(width_input.text())
                h = float(height_input.text())

                return l, w, h

            except:
                return None

        return None

    def compute_heatmap(self):

        total = self.df.groupby(["A","R"]).size().unstack()

        occ = self.df[self.df["status"]=="occupied"].groupby(["A","R"]).size().unstack()

        occ = occ.reindex(index=total.index, columns=total.columns)

        util = occ / total

        util[(total > 0) & util.isna()] = 0

        util = util.where(total.notna())

        heatmap = util.T
        heatmap = heatmap.iloc[::-1]

        return heatmap
    
    def compute_heatmap_level(self, data):

        capacity = 120
        pallet_size = 40

        total = self.df.groupby(["A","R"]).size().unstack()

        occupied = data[data["status"]=="occupied"].copy()

        used = occupied[["长","宽","高"]].max(axis=1)

        occupied = occupied.assign(占用长度=used)

        used_sum = occupied.groupby(["A","R"])["占用长度"].sum().unstack()

        used_sum = used_sum.reindex(index=total.index, columns=total.columns)

        used_sum = used_sum.mask(total.notna() & used_sum.isna(), 0)

        remaining = capacity - used_sum

        capacity_left = (remaining // pallet_size)

        heatmap = capacity_left.T
        heatmap = heatmap.iloc[::-1]

        return heatmap
    
    def change_mode(self, mode):

        self.current_mode = mode

        self.draw_heatmap()

    capacity_cmap = ListedColormap([
        "red",        # 0 pallet
        "yellow",     # 1 pallet
        "lightgreen", # 2 pallet
        "green"       # 3 pallet
    ])

    def draw_heatmap(self):

        self.figure.clear()

        ax = self.figure.add_subplot(111)

        if self.current_mode == "Total":

            heatmap = self.compute_heatmap()

        else:

            level = int(self.current_mode.replace("L",""))

            df_level = self.df[self.df["L"] == level]

            heatmap = self.compute_heatmap_level(df_level)

        if self.current_mode == "Total":

            sns.heatmap(
                heatmap,
                cmap="RdYlGn_r",
                linewidths=0.5,
                vmin=0,
                vmax=1,
                mask=heatmap.isna(),
                ax=ax,
                cbar=False   # ⭐加这个
            )

        else:

            sns.heatmap(
                heatmap,
                cmap=self.capacity_cmap,
                linewidths=0.5,
                vmin=0,
                vmax=3,
                mask=heatmap.isna(),
                ax=ax,
                cbar=False
            )

        today = datetime.datetime.now().strftime("%Y-%m-%d")

        if self.current_mode == "Total":
            title = f"Warehouse Utilization (Total) | {today}"
        else:
            title = f"Warehouse Utilization ({self.current_mode}) | {today}"

        ax.set_title(title, fontsize=12, fontweight="bold")

        self.figure.subplots_adjust(bottom=0.25)

        self.canvas.draw()

        # ===== 恢复高亮 =====
        if self.suggested_location:
            self.highlight_location(self.suggested_location)

    def search_sku(self):

        sku = self.sku_input.text().strip()

        if not sku:
            return

        location, item_len, space = find_location_by_sku(
            self.df, self.inventory_all, sku
        )

        # ===== 找到 SKU =====
        if location:

            self.suggested_location = location
            self.suggested_len = item_len

            # ⭐ 自动切换到对应L
            try:
                L = int(location.split("-")[2].replace("L",""))
                self.change_mode(f"L{L}")
            except:
                pass

            self.confirm_btn.show()
            self.undo_btn.hide()

            self.result_label.setText(
                f"SKU: {sku}\n\n"
                f"Length: {item_len:.0f}\"\n\n"
                f"Suggested:\n{location}\n\n"
                f"Remaining: {space:.0f}\""
            )

            return

        # ===== 没找到 SKU → 弹窗输入尺寸 =====

        size = self.get_size_input()

        if not size:
            return

        length, width, height = size
        item_len = max(length, width, height)

        item_len = max(length, width, height)

        from sku_finder import find_location_by_size

        location, item_len, space = find_location_by_size(
            self.df, item_len
        )

        self.suggested_location = location
        self.suggested_len = item_len

        if location:
            try:
                L = int(location.split("-")[2].replace("L",""))
                self.change_mode(f"L{L}")
            except:
                pass

            self.result_label.setText(
                f"New SKU: {sku}\n\n"
                f"Longest side: {item_len:.0f}\"\n\n"
                f"Suggested:\n{location}\n\n"
                f"Remaining: {space:.0f}\""
            )

            self.highlight_location(location)

            self.confirm_btn.show()
            self.undo_btn.hide()

        else:

            self.result_label.setText(
                f"New SKU: {sku}\n\n"
                f"Longest side: {item_len:.0f}\"\n\n"
                f"No available location"
            )

    def confirm_putaway(self):

        log("Confirm clicked")

        if not self.suggested_location:
            return

        parts = self.suggested_location.split("-")

        A = int(parts[0].replace("A",""))
        R = int(parts[1].replace("R",""))
        L = int(parts[2].replace("L",""))

        new_row = {
            "A":A,
            "R":R,
            "L":L,
            "长":self.suggested_len,
            "宽":0,
            "高":0,
            "status":"occupied",
            "SKU":"PUTAWAY"
        }

        self.df.loc[len(self.df)] = new_row
        self.putaway_stack.append(new_row)

        self.draw_heatmap()

        QMessageBox.information(
            self,
            "Success",
            f"Putaway completed\n{self.suggested_location}"
        )

        self.confirm_btn.hide()
        self.undo_btn.show()

    def undo_putaway(self):

        if not self.putaway_stack:
            return

        last = self.putaway_stack.pop()

        A,R,L = last["A"], last["R"], last["L"]

        idx = self.df[
            (self.df["A"]==A)&
            (self.df["R"]==R)&
            (self.df["L"]==L)
        ].index

        if len(idx):
            self.df = self.df.drop(idx[-1])

        self.draw_heatmap()

        if not self.putaway_stack:
            self.undo_btn.hide()


def run_heatmap_qt(inventory, empty):

    window = HeatmapApp(inventory, empty)

    window.show()

    return window