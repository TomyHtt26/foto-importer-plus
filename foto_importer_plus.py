import os
import shutil
import hashlib
import threading
import time
from datetime import datetime
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ExifTags


CONFIG_FILE = "foto_importer_plus_config.json"

SUPPORTED_EXT = {
    ".jpg", ".jpeg", ".png",
    ".cr2", ".cr3", ".nef", ".arw",
    ".rw2", ".orf", ".raf", ".dng",
    ".hif"
}

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


# ----------------- EXIF / Hash ----------------- #

def get_exif_data(path):
    try:
        with Image.open(path) as img:
            exif = img._getexif() or {}
            exif_data = {}
            for tag, value in exif.items():
                decoded = ExifTags.TAGS.get(tag, tag)
                exif_data[decoded] = value
            return exif_data
    except Exception:
        return {}


def get_capture_info(path):
    exif = get_exif_data(path)
    maker = exif.get("Make")
    model = exif.get("Model")
    dt_str = exif.get("DateTimeOriginal") or exif.get("DateTime")

    if isinstance(maker, bytes):
        maker = maker.decode(errors="ignore").strip()
    if isinstance(model, bytes):
        model = model.decode(errors="ignore").strip()

    # Fallback: Hersteller anhand der Endung raten
    ext = Path(path).suffix.lower()
    if not maker:
        if ext in {".arw", ".hif"}:
            maker = "Sony"
        elif ext in {".orf", ".jpg", ".jpeg"}:
            maker = "Olympus"
        else:
            maker = "Unknown"

    if not model:
        model = ""

    dt_obj = None
    if dt_str:
        for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                dt_obj = datetime.strptime(str(dt_str), fmt)
                break
            except Exception:
                continue

    if dt_obj is None:
        dt_obj = datetime.fromtimestamp(os.path.getmtime(path))

    return dt_obj, maker, model


def get_file_hash(path, chunk_size=1024 * 1024):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def build_target_path(dest_root, src_file):
    dt, maker, model = get_capture_info(src_file)
    year = dt.strftime("%Y")
    day_folder = dt.strftime("%Y-%m-%d")

    ext = Path(src_file).suffix.lower().lstrip(".").upper()
    if not ext:
        ext = "UNKNOWN"

    # Bereinigter Ordnername: OLYMPUS_CORPORATION → Olympus
    cleaned_maker = "Olympus" if "OLYMPUS" in maker.upper() else maker
    cleaned_maker = cleaned_maker.replace(" ", "_").replace(".", "_")
    rel_dir = Path(year) / day_folder / cleaned_maker / ext
    dest_dir = Path(dest_root) / rel_dir
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest_file = dest_dir / Path(src_file).name
    return dest_file, rel_dir



# ----------------- Haupt-App ----------------- #

class FotoImporter(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Foto Importer Plus")
        self.geometry("900x700")
        self.minsize(800, 600)

        self.config_data = self.load_config()
        self.paused = False
        self.cancelled = False

        self.create_widgets()

    # ---- Config ---- #

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                import json
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_config(self):
        self.config_data["last_source"] = self.source_entry.get()
        self.config_data["last_dest1"] = self.dest1_entry.get()
        self.config_data["last_dest2"] = self.dest2_entry.get()
        self.config_data["dest2_enabled"] = self.dest2_enabled.get()
        try:
            import json
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config_data, f, indent=2)
        except Exception:
            pass

    # ---- GUI ---- #

    def create_widgets(self):
        nb = ctk.CTkTabview(self)
        nb.pack(fill="both", expand=True, padx=10, pady=10)

        import_tab = nb.add("Import")

        self.create_import_tab(import_tab)

    # ---- Import-Tab ---- #

    def create_import_tab(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Pfade
        path_frame = ctk.CTkFrame(frame)
        path_frame.pack(fill="x", pady=10)

        # Quelle
        ctk.CTkLabel(path_frame, text="Quellordner (SD-Karte):").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.source_entry = ctk.CTkEntry(path_frame, width=500)
        self.source_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.source_entry.insert(0, self.config_data.get("last_source", ""))

        src_btn = ctk.CTkButton(path_frame, text="Wählen…", command=self.select_source)
        src_btn.grid(row=0, column=2, padx=10, pady=10)

        # Ziel 1 (lokal)
        ctk.CTkLabel(path_frame, text="Zielordner 1 (lokal):").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.dest1_entry = ctk.CTkEntry(path_frame, width=500)
        self.dest1_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        self.dest1_entry.insert(0, self.config_data.get("last_dest1", ""))

        dst1_btn = ctk.CTkButton(path_frame, text="Wählen…", command=self.select_dest1)
        dst1_btn.grid(row=1, column=2, padx=10, pady=10)

        # Ziel 2 (optional, z.B. NAS)
        self.dest2_enabled = tk.BooleanVar(value=self.config_data.get("dest2_enabled", False))
        dest2_check = ctk.CTkCheckBox(
            path_frame, text="Zweites Ziel aktivieren", variable=self.dest2_enabled
        )
        dest2_check.grid(row=2, column=0, padx=10, pady=10, sticky="w")

        self.dest2_entry = ctk.CTkEntry(path_frame, width=500)
        self.dest2_entry.grid(row=2, column=1, padx=10, pady=10, sticky="ew")
        self.dest2_entry.insert(0, self.config_data.get("last_dest2", ""))

        dst2_btn = ctk.CTkButton(path_frame, text="Wählen…", command=self.select_dest2)
        dst2_btn.grid(row=2, column=2, padx=10, pady=10)

        path_frame.columnconfigure(1, weight=1)

        # Buttons
        btn_frame = ctk.CTkFrame(frame)
        btn_frame.pack(fill="x", pady=10)

        self.preview_btn = ctk.CTkButton(btn_frame, text="Vorschau", command=self.preview_scan, fg_color="orange")
        self.preview_btn.pack(side="left", padx=10, pady=10)

        self.start_btn = ctk.CTkButton(btn_frame, text="Kopieren starten", command=self.start_copy, fg_color="green")
        self.start_btn.pack(side="left", padx=10, pady=10)

        self.pause_btn = ctk.CTkButton(btn_frame, text="Pause", command=self.toggle_pause, state="disabled")
        self.pause_btn.pack(side="left", padx=10, pady=10)

        self.cancel_btn = ctk.CTkButton(btn_frame, text="Abbrechen", command=self.cancel_copy, state="disabled", fg_color="red")
        self.cancel_btn.pack(side="right", padx=10, pady=10)

        # Progress
        prog_frame = ctk.CTkFrame(frame)
        prog_frame.pack(fill="x", pady=10)

        self.progress = ctk.CTkProgressBar(prog_frame)
        self.progress.pack(fill="x", padx=10, pady=10)
        self.progress.set(0)

        self.status_label = ctk.CTkLabel(prog_frame, text="Bereit")
        self.status_label.pack(padx=10, pady=5)

        # Log
        log_frame = ctk.CTkFrame(frame)
        log_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(log_frame, text="Protokoll:").pack(anchor="w", padx=10, pady=5)
        self.log_text = ctk.CTkTextbox(log_frame)
        self.log_text.pack(fill="both", expand=True, padx=10, pady=5)
        self.append_log("Programm gestartet.")

    def append_log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{ts}] {msg}\n")
        self.log_text.see("end")
        self.update_idletasks()

    # ---- Pfadwahl ---- #

    def select_source(self):
        folder = filedialog.askdirectory(initialdir=self.source_entry.get() or "/")
        if folder:
            self.source_entry.delete(0, "end")
            self.source_entry.insert(0, folder)

    def select_dest1(self):
        folder = filedialog.askdirectory(initialdir=self.dest1_entry.get() or "/")
        if folder:
            self.dest1_entry.delete(0, "end")
            self.dest1_entry.insert(0, folder)

    def select_dest2(self):
        folder = filedialog.askdirectory(initialdir=self.dest2_entry.get() or "/")
        if folder:
            self.dest2_entry.delete(0, "end")
            self.dest2_entry.insert(0, folder)

    # ---- Vorschau ---- #

    def preview_scan(self):
        src = self.source_entry.get().strip()
        dst1 = self.dest1_entry.get().strip()
        if not os.path.isdir(src):
            messagebox.showerror("Fehler", "Quellordner ist ungültig.")
            return
        if not dst1:
            messagebox.showerror("Fehler", "Bitte Zielordner 1 wählen.")
            return

        files = []
        for root, _, fnames in os.walk(src):
            for name in fnames:
                if Path(name).suffix.lower() in SUPPORTED_EXT:
                    files.append(str(Path(root) / name))

        if not files:
            messagebox.showinfo("Info", "Keine unterstützten Bilddateien gefunden.")
            return

        top = ctk.CTkToplevel(self)
        top.title("Vorschau (max. 100 Dateien)")
        top.geometry("900x400")

        tree = ttk.Treeview(top)
        tree.pack(fill="both", expand=True, padx=10, pady=10)

        tree["columns"] = ("Quelle", "Ziel1", "Kamera", "Datum")
        tree.heading("#0", text="Dateiname")
        tree.heading("Quelle", text="Quelle")
        tree.heading("Ziel1", text="Zielstruktur 1")
        tree.heading("Kamera", text="Kamera")
        tree.heading("Datum", text="Datum")

        for f in files[:100]:
            dt, maker, model = get_capture_info(f)
            dest1, rel1 = build_target_path(dst1, f)
            tree.insert(
                "",
                "end",
                text=Path(f).name,
                values=(f, str(rel1), f"{maker} {model}", dt.strftime("%Y-%m-%d %H:%M"))
            )

    # ---- Kopierlogik (2 Ziele, getrennte Duplikatprüfung) ---- #

    def start_copy(self):
        src = self.source_entry.get().strip()
        dst1 = self.dest1_entry.get().strip()
        dst2 = self.dest2_entry.get().strip() if self.dest2_enabled.get() else None

        if not os.path.isdir(src):
            messagebox.showerror("Fehler", "Quellordner ist ungültig.")
            return
        if not dst1:
            messagebox.showerror("Fehler", "Bitte Zielordner 1 wählen.")
            return

        Path(dst1).mkdir(parents=True, exist_ok=True)
        if dst2:
            Path(dst2).mkdir(parents=True, exist_ok=True)

        self.save_config()

        self.paused = False
        self.cancelled = False
        self.start_btn.configure(state="disabled")
        self.pause_btn.configure(state="normal")
        self.cancel_btn.configure(state="normal")
        self.progress.set(0)
        self.append_log("Kopiervorgang gestartet.")

        t = threading.Thread(target=self.copy_worker, args=(src, dst1, dst2), daemon=True)
        t.start()

    def copy_worker(self, src, dst1, dst2):
        # Quelldateien sammeln
        files = []
        for root, _, fnames in os.walk(src):
            for name in fnames:
                if Path(name).suffix.lower() in SUPPORTED_EXT:
                    files.append(str(Path(root) / name))

        if not files:
            self.after(0, lambda: messagebox.showinfo("Info", "Keine Dateien zu kopieren."))
            self.after(0, self.reset_buttons)
            return

        total = len(files)
        copied1 = copied2 = skipped1 = skipped2 = errored = 0

        # Zielindex 1
        self.after(0, lambda: self.status_label.configure(text="Baue Duplikat-Index für Ziel 1 auf..."))
        target_index1 = {}
        if os.path.isdir(dst1):
            for root, _, fnames in os.walk(dst1):
                for name in fnames:
                    if Path(name).suffix.lower() in SUPPORTED_EXT:
                        full = Path(root) / name
                        try:
                            size = os.path.getsize(full)
                            key = (name.lower(), size)
                            target_index1.setdefault(key, []).append(str(full))
                        except Exception:
                            continue

        # Zielindex 2
        target_index2 = {}
        if dst2 and os.path.isdir(dst2):
            self.after(0, lambda: self.status_label.configure(text="Baue Duplikat-Index für Ziel 2 auf..."))
            for root, _, fnames in os.walk(dst2):
                for name in fnames:
                    if Path(name).suffix.lower() in SUPPORTED_EXT:
                        full = Path(root) / name
                        try:
                            size = os.path.getsize(full)
                            key = (name.lower(), size)
                            target_index2.setdefault(key, []).append(str(full))
                        except Exception:
                            continue

        # Kopierschleife
        for idx, f in enumerate(files, start=1):
            if self.cancelled:
                break

            while self.paused:
                time.sleep(0.1)

            try:
                size_src = os.path.getsize(f)
                name_src = Path(f).name
                key = (name_src.lower(), size_src)
            except Exception:
                errored += 1
                self.after(0, lambda ff=f: self.append_log(f"Fehler beim Lesen von Größe/Name: {ff}"))
                continue

            # ---------- Ziel 1 prüfen ----------
            is_duplicate1 = False
            candidates1 = target_index1.get(key, [])

            hash_src = None

            if candidates1:
                try:
                    hash_src = get_file_hash(f)
                    for cand in candidates1:
                        try:
                            if get_file_hash(cand) == hash_src:
                                is_duplicate1 = True
                                break
                        except Exception:
                            continue
                except Exception:
                    is_duplicate1 = False

            # ---------- Ziel 2 prüfen ----------
            is_duplicate2 = False
            candidates2 = target_index2.get(key, []) if dst2 else []

            if dst2 and candidates2:
                try:
                    if hash_src is None:
                        hash_src = get_file_hash(f)
                    for cand in candidates2:
                        try:
                            if get_file_hash(cand) == hash_src:
                                is_duplicate2 = True
                                break
                        except Exception:
                            continue
                except Exception:
                    is_duplicate2 = False

            # ---------- Kopieren nach Ziel 1 ----------
            if is_duplicate1:
                skipped1 += 1
                self.after(0, lambda ff=f: self.append_log(f"Übersprungen in Ziel 1 (Duplikat): {ff}"))
            else:
                try:
                    dest1_file, rel1 = build_target_path(dst1, f)
                    base1 = dest1_file
                    counter1 = 1
                    while dest1_file.exists():
                        dest1_file = base1.with_stem(base1.stem + f"_{counter1}")
                        counter1 += 1

                    shutil.copy2(f, dest1_file)

                    try:
                        size_new1 = os.path.getsize(dest1_file)
                        key_new1 = (dest1_file.name.lower(), size_new1)
                        target_index1.setdefault(key_new1, []).append(str(dest1_file))
                    except Exception:
                        pass

                    copied1 += 1
                    self.after(0, lambda ff=f, rr=rel1: self.append_log(f"Kopiert nach Ziel 1 → {rr}: {ff}"))
                except Exception as e:
                    errored += 1
                    self.after(0, lambda ff=f, ee=e: self.append_log(f"Fehler beim Kopieren nach Ziel 1 {ff}: {ee}"))

            # ---------- Kopieren nach Ziel 2 ----------
            if dst2:
                if is_duplicate2:
                    skipped2 += 1
                    self.after(0, lambda ff=f: self.append_log(f"Übersprungen in Ziel 2 (Duplikat): {ff}"))
                else:
                    try:
                        dest2_file, rel2 = build_target_path(dst2, f)
                        base2 = dest2_file
                        counter2 = 1
                        while dest2_file.exists():
                            dest2_file = base2.with_stem(base2.stem + f"_{counter2}")
                            counter2 += 1

                        shutil.copy2(f, dest2_file)

                        try:
                            size_new2 = os.path.getsize(dest2_file)
                            key_new2 = (dest2_file.name.lower(), size_new2)
                            target_index2.setdefault(key_new2, []).append(str(dest2_file))
                        except Exception:
                            pass

                        copied2 += 1
                        self.after(0, lambda ff=f, rr=rel2: self.append_log(f"Kopiert nach Ziel 2 → {rr}: {ff}"))
                    except Exception as e:
                        errored += 1
                        self.after(0, lambda ff=f, ee=e: self.append_log(f"Fehler beim Kopieren nach Ziel 2 {ff}: {ee}"))

            # ---------- Fortschritt ----------
            self.after(0, lambda i=idx, t=total, c1=copied1, s1=skipped1, c2=copied2, s2=skipped2:
                       (self.progress.set(i / t),
                        self.status_label.configure(
                            text=f"{i}/{t} | Ziel1 Kopiert: {c1} / Übersprungen: {s1} | "
                                 f"Ziel2 Kopiert: {c2} / Übersprungen: {s2}"
                        )))

        self.after(0, lambda: self.finish_copy(copied1 + copied2, skipped1 + skipped2, errored))

    def toggle_pause(self):
        self.paused = not self.paused
        self.pause_btn.configure(text="Fortsetzen" if self.paused else "Pause")

    def cancel_copy(self):
        self.cancelled = True
        self.paused = False

    def finish_copy(self, copied, skipped, errored):
        self.append_log(f"Fertig. Kopiert: {copied}, Übersprungen: {skipped}, Fehler: {errored}")
        messagebox.showinfo("Fertig", f"Kopiert: {copied}\nÜbersprungen: {skipped}\nFehler: {errored}")
        self.reset_buttons()

    def reset_buttons(self):
        self.start_btn.configure(state="normal")
        self.pause_btn.configure(state="disabled")
        self.cancel_btn.configure(state="disabled")
        self.status_label.configure(text="Bereit")
        self.progress.set(0)


if __name__ == "__main__":
    app = FotoImporter()
    app.mainloop()
