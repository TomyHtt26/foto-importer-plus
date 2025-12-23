# Foto-Importer Plus

Ein benutzerfreundliches Python-GUI-Tool zum Sortieren und Kopieren von Fotos nach Datum (z. B. nach Jahr/Monat) und optional nach Kamera-Modell.

---

## 📌 Was macht das Tool?

Foto-Importer Plus hilft dir dabei, Fotos aus einem Quellordner (z. B. Kamera-SD-Karte) automatisch in ein strukturiertes Zielverzeichnis zu kopieren:

- Ordnerstruktur: `Ziel/2025/01_Januar/` (oder `2025/01/`)
- Optionale Untergliederung nach Kamera-Modell
- Vorschau der zu kopierenden Dateien
- Überschreiben / Überspringen / Duplikate erkennen
- Einfache Bedienung über eine moderne GUI


## 🛠️ Technologie & Abhängigkeiten

- Python 3.8+
- GUI: `customtkinter`
- Bildmetadaten: `Pillow` (für EXIF-Datum)
- Für die EXE: `pyinstaller`

---

## 📦 Installation & Nutzung

### 1. Voraussetzungen

- Python 3.8 oder neuer installiert
- Optional: `pip` (meistens dabei)

### 2. Projekt klonen

git clone https://github.com/TomyHtt26/foto-importer-plus.git
cd foto-importer-plus

text

### 3. Abhängigkeiten installieren

pip install pillow customtkinter

text

### 4. Tool starten

python foto_importer_plus.py

text

---

## 🧩 EXE-Datei (Windows)

Die fertige EXE-Datei wird automatisch über GitHub Actions gebaut und steht als Artefakt unter „Actions“ zum Download bereit.

---

## 📁 Projektstruktur

foto-importer-plus/
├── foto_importer_plus.py # Haupt-Script
├── .github/
│ └── workflows/
│ └── build_exe.yml # GitHub Actions Workflow
└── README.md # Diese Datei

text

---

## 📄 Lizenz

Dieses Projekt steht unter der MIT-Lizenz. Details siehe `LICENSE`-Datei.

---

## 📬 Kontakt & Feedback

Bei Fragen, Verbesserungsvorschlägen oder Bugs kannst du gerne ein Issue im Repository öffnen.

---

## 🙏 Danksagung

- Dank an die Entwickler von `customtkinter` und `Pillow` für die großartigen Bibliotheken.
- Inspiration aus der Praxis: viele Fotos, viele Ordner, endlich ein Tool, das das automatisiert.