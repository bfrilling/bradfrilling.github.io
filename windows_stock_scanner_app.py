#!/usr/bin/env python3
"""Windows desktop wrapper for weekly growth scanner.

Build into a Windows .exe using PyInstaller (on Windows):
    pyinstaller --noconfirm --clean --onefile --windowed \
      --name WeeklyGrowthScanner windows_stock_scanner_app.py
"""

from __future__ import annotations

import threading
import traceback
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import scan_weekly_growth as scanner


class ScannerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Weekly Growth Scanner")
        self.geometry("980x640")

        self.symbols_file_var = tk.StringVar(value="")
        self.fixture_dir_var = tk.StringVar(value="")
        self.output_csv_var = tk.StringVar(value="weekly_growth_scan.csv")
        self.top_var = tk.StringVar(value="50")
        self.workers_var = tk.StringVar(value="24")
        self.limit_var = tk.StringVar(value="0")

        self._build_ui()

    def _build_ui(self) -> None:
        form = ttk.Frame(self, padding=12)
        form.pack(fill=tk.X)

        self._add_path_row(form, "Symbols file (optional)", self.symbols_file_var, 0, is_file=True)
        self._add_path_row(form, "Fixture dir (optional)", self.fixture_dir_var, 1, is_file=False)
        self._add_path_row(form, "Output CSV", self.output_csv_var, 2, is_file=True, save_file=True)

        self._add_entry_row(form, "Top rows to show", self.top_var, 3)
        self._add_entry_row(form, "Workers", self.workers_var, 4)
        self._add_entry_row(form, "Limit symbols (0 = all)", self.limit_var, 5)

        buttons = ttk.Frame(form)
        buttons.grid(row=6, column=0, columnspan=3, sticky="w", pady=(10, 0))

        self.scan_btn = ttk.Button(buttons, text="Run Scan", command=self.run_scan)
        self.scan_btn.pack(side=tk.LEFT)

        ttk.Label(
            form,
            text="Educational tool only. Not financial advice.",
            foreground="#8a4f00",
        ).grid(row=7, column=0, columnspan=3, sticky="w", pady=(10, 0))

        columns = ("symbol", "score", "weekly_return_pct", "rsi14", "vol_ratio", "reasons")
        self.table = ttk.Treeview(self, columns=columns, show="headings", height=18)

        for col, width in [
            ("symbol", 80),
            ("score", 70),
            ("weekly_return_pct", 120),
            ("rsi14", 80),
            ("vol_ratio", 80),
            ("reasons", 500),
        ]:
            self.table.heading(col, text=col)
            self.table.column(col, width=width, anchor=tk.W)

        scroll = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.table.yview)
        self.table.configure(yscrollcommand=scroll.set)

        self.table.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=(12, 0), pady=12)
        scroll.pack(fill=tk.Y, side=tk.RIGHT, padx=(0, 12), pady=12)

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(self, textvariable=self.status_var, padding=(12, 0, 12, 12)).pack(anchor="w")

    def _add_path_row(
        self,
        parent: ttk.Frame,
        label: str,
        var: tk.StringVar,
        row: int,
        *,
        is_file: bool,
        save_file: bool = False,
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(parent, textvariable=var, width=80).grid(row=row, column=1, sticky="we", pady=4, padx=8)

        def pick() -> None:
            if is_file:
                if save_file:
                    path = filedialog.asksaveasfilename(defaultextension=".csv")
                else:
                    path = filedialog.askopenfilename()
            else:
                path = filedialog.askdirectory()
            if path:
                var.set(path)

        ttk.Button(parent, text="Browse", command=pick).grid(row=row, column=2, sticky="e", pady=4)
        parent.columnconfigure(1, weight=1)

    def _add_entry_row(self, parent: ttk.Frame, label: str, var: tk.StringVar, row: int) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(parent, textvariable=var, width=20).grid(row=row, column=1, sticky="w", pady=4, padx=8)

    def run_scan(self) -> None:
        try:
            top = int(self.top_var.get())
            workers = max(1, int(self.workers_var.get()))
            limit = int(self.limit_var.get())
        except ValueError:
            messagebox.showerror("Invalid input", "Top, workers, and limit must be integers.")
            return

        self.scan_btn.configure(state=tk.DISABLED)
        self.status_var.set("Scanning...")
        self._clear_table()

        thread = threading.Thread(
            target=self._scan_worker,
            args=(top, workers, limit),
            daemon=True,
        )
        thread.start()

    def _scan_worker(self, top: int, workers: int, limit: int) -> None:
        try:
            symbols_file = self.symbols_file_var.get().strip()
            fixture_dir = self.fixture_dir_var.get().strip()
            output_csv = self.output_csv_var.get().strip() or "weekly_growth_scan.csv"

            if symbols_file:
                with open(symbols_file, "r", encoding="utf-8") as handle:
                    symbols = [line.strip().upper() for line in handle if line.strip()]
            else:
                symbols = scanner.load_us_symbols()

            if limit > 0:
                symbols = symbols[:limit]

            results = scanner.scan_symbols(symbols, workers=workers, fixture_dir=fixture_dir)
            scanner.write_csv(results, output_csv)

            top_results = results[:top]
            self.after(0, lambda: self._render_results(top_results, output_csv, len(results)))
        except Exception as exc:  # noqa: BLE001
            detail = f"{exc}\n\n{traceback.format_exc()}"
            self.after(0, lambda: self._handle_error(detail))

    def _clear_table(self) -> None:
        for row in self.table.get_children():
            self.table.delete(row)

    def _render_results(self, results: list[scanner.ScanResult], output_csv: str, total: int) -> None:
        self._clear_table()
        for item in results:
            self.table.insert(
                "",
                tk.END,
                values=(
                    item.symbol,
                    item.score,
                    f"{item.weekly_return_pct:.2f}%",
                    f"{item.rsi14:.2f}",
                    f"{item.vol_ratio:.2f}",
                    item.reasons,
                ),
            )

        self.scan_btn.configure(state=tk.NORMAL)
        self.status_var.set(f"Done. Found {total} candidates. CSV: {Path(output_csv).resolve()}")

    def _handle_error(self, detail: str) -> None:
        self.scan_btn.configure(state=tk.NORMAL)
        self.status_var.set("Scan failed")
        messagebox.showerror("Scan failed", detail)


if __name__ == "__main__":
    app = ScannerApp()
    app.mainloop()
