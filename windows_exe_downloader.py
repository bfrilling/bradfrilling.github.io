#!/usr/bin/env python3
"""Windows EXE downloader app for WeeklyGrowthScanner.

Build on Windows:
    pyinstaller --noconfirm --clean --onefile --windowed \
      --name WeeklyGrowthScannerDownloader windows_exe_downloader.py
"""

from __future__ import annotations

import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from urllib.request import urlopen

# Replace this with your real hosted EXE URL (e.g. GitHub Releases asset URL)
DEFAULT_EXE_URL = "https://example.com/WeeklyGrowthScanner.exe"
DEFAULT_FILENAME = "WeeklyGrowthScanner.exe"


class DownloaderApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("WeeklyGrowthScanner EXE Downloader")
        self.geometry("720x240")

        downloads_dir = Path.home() / "Downloads" / DEFAULT_FILENAME

        self.url_var = tk.StringVar(value=DEFAULT_EXE_URL)
        self.output_var = tk.StringVar(value=str(downloads_dir))
        self.status_var = tk.StringVar(value="Ready")

        self._build_ui()

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=12)
        root.pack(fill=tk.BOTH, expand=True)

        ttk.Label(root, text="EXE URL").grid(row=0, column=0, sticky="w", pady=6)
        ttk.Entry(root, textvariable=self.url_var, width=80).grid(row=0, column=1, sticky="we", padx=8)

        ttk.Label(root, text="Save as").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Entry(root, textvariable=self.output_var, width=80).grid(row=1, column=1, sticky="we", padx=8)

        ttk.Button(root, text="Browse", command=self.pick_output).grid(row=1, column=2, sticky="e")

        btns = ttk.Frame(root)
        btns.grid(row=2, column=0, columnspan=3, sticky="w", pady=(10, 0))

        self.download_btn = ttk.Button(btns, text="Download EXE", command=self.download)
        self.download_btn.pack(side=tk.LEFT)

        self.open_folder_btn = ttk.Button(btns, text="Open Folder", command=self.open_folder, state=tk.DISABLED)
        self.open_folder_btn.pack(side=tk.LEFT, padx=(8, 0))

        ttk.Label(root, textvariable=self.status_var).grid(row=3, column=0, columnspan=3, sticky="w", pady=(16, 0))

        note = (
            "Tip: host your built EXE in GitHub Releases or another direct-download URL, "
            "then paste that URL here."
        )
        ttk.Label(root, text=note, foreground="#8a4f00").grid(row=4, column=0, columnspan=3, sticky="w", pady=(10, 0))

        root.columnconfigure(1, weight=1)

    def pick_output(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".exe", initialfile=DEFAULT_FILENAME)
        if path:
            self.output_var.set(path)

    def download(self) -> None:
        url = self.url_var.get().strip()
        output = self.output_var.get().strip()

        if not url.lower().startswith(("http://", "https://")):
            messagebox.showerror("Invalid URL", "Please provide a valid http(s) URL.")
            return
        if not output.lower().endswith(".exe"):
            messagebox.showerror("Invalid output file", "Output filename must end with .exe")
            return

        self.download_btn.configure(state=tk.DISABLED)
        self.open_folder_btn.configure(state=tk.DISABLED)
        self.status_var.set("Downloading...")

        threading.Thread(target=self._download_worker, args=(url, output), daemon=True).start()

    def _download_worker(self, url: str, output: str) -> None:
        try:
            out_path = Path(output)
            out_path.parent.mkdir(parents=True, exist_ok=True)

            with urlopen(url, timeout=60) as response:
                total = response.headers.get("Content-Length")
                total_size = int(total) if total and total.isdigit() else 0
                downloaded = 0

                with open(out_path, "wb") as handle:
                    while True:
                        chunk = response.read(1024 * 256)
                        if not chunk:
                            break
                        handle.write(chunk)
                        downloaded += len(chunk)
                        self.after(0, lambda d=downloaded, t=total_size: self._set_progress(d, t))

            self.after(0, lambda: self._done(str(out_path.resolve())))
        except Exception as exc:  # noqa: BLE001
            self.after(0, lambda: self._failed(str(exc)))

    def _set_progress(self, downloaded: int, total: int) -> None:
        if total > 0:
            pct = downloaded * 100 / total
            self.status_var.set(f"Downloading... {pct:.1f}% ({downloaded:,}/{total:,} bytes)")
        else:
            self.status_var.set(f"Downloading... {downloaded:,} bytes")

    def _done(self, out_file: str) -> None:
        self.status_var.set(f"Download complete: {out_file}")
        self.download_btn.configure(state=tk.NORMAL)
        self.open_folder_btn.configure(state=tk.NORMAL)
        messagebox.showinfo("Done", f"Saved EXE to:\n{out_file}")

    def _failed(self, error: str) -> None:
        self.download_btn.configure(state=tk.NORMAL)
        self.open_folder_btn.configure(state=tk.DISABLED)
        self.status_var.set("Download failed")
        messagebox.showerror("Download failed", error)

    def open_folder(self) -> None:
        out_path = Path(self.output_var.get().strip())
        folder = out_path.parent if out_path.parent.exists() else Path.home()
        try:
            os.startfile(str(folder))  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            messagebox.showinfo("Folder", str(folder))


if __name__ == "__main__":
    app = DownloaderApp()
    app.mainloop()
