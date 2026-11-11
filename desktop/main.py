from __future__ import annotations
import sys, json
from pathlib import Path
from collections import defaultdict

import numpy as np
import pydicom
from pydicom.errors import InvalidDicomError
from PIL import Image

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFileDialog, QListWidget, QSlider, QSpinBox, QDoubleSpinBox,
    QMessageBox, QSplitter, QGroupBox, QFormLayout
)
from desktop.liver_tools import LiverToolsDialog

APP_NAME = "HEPATIC"
APP_VERSION = "0.3.0"

def _slice_projection(ds):
    try:
        ipp = np.asarray(ds.ImagePositionPatient, dtype=float)
        iop = np.asarray(ds.ImageOrientationPatient, dtype=float)
        normal = np.cross(iop[:3], iop[3:])
        return float(np.dot(ipp, normal))
    except Exception:
        try:
            return float(ds.InstanceNumber)
        except Exception:
            return 0.0

def load_dicom_folder(folder: str):
    groups = defaultdict(list)
    for path in Path(folder).rglob("*"):
        if not path.is_file():
            continue
        try:
            ds = pydicom.dcmread(str(path), force=False)
            if "PixelData" not in ds:
                continue
            modality = str(getattr(ds, "Modality", ""))
            if modality and modality != "CT":
                continue
            uid = str(getattr(ds, "SeriesInstanceUID", "unknown"))
            groups[uid].append((ds, str(path)))
        except (InvalidDicomError, PermissionError, OSError, ValueError):
            continue
    result = {}
    for uid, items in groups.items():
        items.sort(key=lambda x: _slice_projection(x[0]))
        result[uid] = items
    return result

def to_hu(ds):
    pixels = ds.pixel_array.astype(np.float32)
    slope = float(getattr(ds, "RescaleSlope", 1.0))
    intercept = float(getattr(ds, "RescaleIntercept", 0.0))
    return pixels * slope + intercept

def window_image(hu, center, width):
    width = max(float(width), 1.0)
    low, high = center - width / 2.0, center + width / 2.0
    scaled = np.clip((hu - low) / (high - low), 0, 1)
    return (scaled * 255).astype(np.uint8)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} — Advanced Liver Imaging | v{APP_VERSION}")
        self.resize(1250, 780)
        self.series = {}
        self.current_items = []
        self.current_index = 0
        self.current_hu = None
        self.study_folder = None
        self._build_ui()
        self._style()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)

        header = QHBoxLayout()
        brand = QLabel("HEPATIC™")
        brand.setObjectName("brand")
        subtitle = QLabel("ADVANCED LIVER IMAGING  •  SEE BEYOND THE IMAGE")
        subtitle.setObjectName("subtitle")
        header.addWidget(brand)
        header.addWidget(subtitle)
        header.addStretch()
        self.import_btn = QPushButton("Import DICOM Folder")
        self.import_btn.clicked.connect(self.import_folder)
        header.addWidget(self.import_btn)
        outer.addLayout(header)

        split = QSplitter(Qt.Horizontal)
        outer.addWidget(split, 1)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("STUDY / SERIES"))
        self.series_list = QListWidget()
        self.series_list.currentRowChanged.connect(self.select_series)
        left_layout.addWidget(self.series_list, 1)
        self.meta = QLabel("No study loaded")
        self.meta.setWordWrap(True)
        left_layout.addWidget(self.meta)
        split.addWidget(left)

        center = QWidget()
        c_layout = QVBoxLayout(center)
        self.image_label = QLabel("Import an anonymized CT DICOM folder to begin")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(500, 500)
        self.image_label.setObjectName("viewer")
        c_layout.addWidget(self.image_label, 1)

        nav = QHBoxLayout()
        nav.addWidget(QLabel("Slice"))
        self.slice_slider = QSlider(Qt.Horizontal)
        self.slice_slider.valueChanged.connect(self.show_slice)
        nav.addWidget(self.slice_slider, 1)
        self.slice_count = QLabel("0 / 0")
        nav.addWidget(self.slice_count)
        c_layout.addLayout(nav)
        split.addWidget(center)

        right = QWidget()
        r_layout = QVBoxLayout(right)
        controls = QGroupBox("DISPLAY")
        form = QFormLayout(controls)
        self.ww = QSpinBox(); self.ww.setRange(1, 4000); self.ww.setValue(350)
        self.wl = QSpinBox(); self.wl.setRange(-1000, 3000); self.wl.setValue(50)
        self.ww.valueChanged.connect(self.show_slice)
        self.wl.valueChanged.connect(self.show_slice)
        form.addRow("Window Width", self.ww)
        form.addRow("Window Level", self.wl)
        r_layout.addWidget(controls)
        presets = QGroupBox("CT PRESETS")
        p = QVBoxLayout(presets)
        for name, center, width in [
            ("Soft Tissue", 50, 350), ("Liver", 70, 150),
            ("Lung", -600, 1500), ("Bone", 400, 1800)
        ]:
            b = QPushButton(name)
            b.clicked.connect(lambda checked=False, c=center, w=width: self.set_preset(c, w))
            p.addWidget(b)
        r_layout.addWidget(presets)
        analysis_btn = QPushButton("AI / 3D / Liver Volumetry")
        analysis_btn.clicked.connect(self.open_liver_tools)
        r_layout.addWidget(analysis_btn)
        export_btn = QPushButton("Save Study Summary")
        export_btn.clicked.connect(self.save_summary)
        r_layout.addWidget(export_btn)
        r_layout.addStretch()
        split.addWidget(right)
        split.setSizes([240, 760, 230])

    def _style(self):
        self.setStyleSheet("""
        QMainWindow, QWidget { background:#101c29; color:#e8f0f6; font-family:Segoe UI; }
        QLabel#brand { color:#d8b56d; font-size:25px; font-weight:700; letter-spacing:3px; }
        QLabel#subtitle { color:#8fb8ca; font-size:10px; padding-left:12px; }
        QLabel#viewer { background:#05090e; border:1px solid #294356; color:#9ab1c0; }
        QPushButton { background:#1c3d52; border:1px solid #42647a; padding:8px; border-radius:5px; }
        QPushButton:hover { background:#28536c; }
        QListWidget, QSpinBox { background:#142536; border:1px solid #294356; padding:5px; }
        QGroupBox { border:1px solid #294356; margin-top:10px; padding:8px; }
        QGroupBox::title { color:#d8b56d; }
        QSlider::groove:horizontal { height:5px; background:#294356; }
        QSlider::handle:horizontal { background:#d8b56d; width:13px; margin:-5px 0; border-radius:6px; }
        """)

    def import_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select DICOM folder")
        if not folder:
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.series = load_dicom_folder(folder)
            self.study_folder = folder
            self.series_list.clear()
            for uid, items in self.series.items():
                ds = items[0][0]
                desc = str(getattr(ds, "SeriesDescription", "Unnamed series"))
                self.series_list.addItem(f"{desc}  |  {len(items)} slices")
            if self.series:
                self.series_list.setCurrentRow(0)
            else:
                QMessageBox.warning(self, "No CT series", "No readable CT DICOM image series were found.")
        except Exception as exc:
            QMessageBox.critical(self, "Import error", str(exc))
        finally:
            QApplication.restoreOverrideCursor()

    def select_series(self, row):
        if row < 0 or row >= len(self.series):
            return
        uid = list(self.series.keys())[row]
        self.current_items = self.series[uid]
        self.current_index = 0
        self.slice_slider.blockSignals(True)
        self.slice_slider.setRange(0, max(0, len(self.current_items)-1))
        self.slice_slider.setValue(0)
        self.slice_slider.blockSignals(False)
        ds = self.current_items[0][0]
        self.meta.setText(
            f"Modality: {getattr(ds,'Modality','—')}\n"
            f"Manufacturer: {getattr(ds,'Manufacturer','—')}\n"
            f"Model: {getattr(ds,'ManufacturerModelName','—')}\n"
            f"Rows × Columns: {getattr(ds,'Rows','—')} × {getattr(ds,'Columns','—')}\n"
            f"Pixel spacing: {getattr(ds,'PixelSpacing','—')}\n"
            f"Slice count: {len(self.current_items)}"
        )
        self.show_slice(0)

    def set_preset(self, center, width):
        self.wl.setValue(center)
        self.ww.setValue(width)

    def show_slice(self, value=None):
        if not self.current_items:
            return
        idx = self.slice_slider.value()
        self.current_index = idx
        ds = self.current_items[idx][0]
        try:
            hu = to_hu(ds)
            self.current_hu = hu
            img = window_image(hu, self.wl.value(), self.ww.value())
            h, w = img.shape
            qimg = QImage(img.data, w, h, w, QImage.Format_Grayscale8).copy()
            pix = QPixmap.fromImage(qimg).scaled(
                self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.image_label.setPixmap(pix)
            self.slice_count.setText(f"{idx+1} / {len(self.current_items)}")
        except Exception as exc:
            self.image_label.setText(f"Unable to render this slice:\n{exc}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.current_items:
            self.show_slice(self.current_index)

    def open_liver_tools(self):
        if not self.current_items:
            QMessageBox.information(self, "No study", "Import a CT DICOM series first.")
            return
        dlg = LiverToolsDialog(self.current_items, self)
        dlg.exec()

    def save_summary(self):
        if not self.current_items:
            QMessageBox.information(self, "No study", "Import a DICOM study first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save study summary", "hepatic_study.json", "JSON (*.json)")
        if not path:
            return
        ds = self.current_items[0][0]
        summary = {
            "application": APP_NAME, "version": APP_VERSION,
            "source_folder": self.study_folder,
            "modality": str(getattr(ds, "Modality", "")),
            "manufacturer": str(getattr(ds, "Manufacturer", "")),
            "series_description": str(getattr(ds, "SeriesDescription", "")),
            "slice_count": len(self.current_items),
            "note": "Development summary only; not a diagnostic report."
        }
        Path(path).write_text(json.dumps(summary, indent=2), encoding="utf-8")
        QMessageBox.information(self, "Saved", f"Summary saved:\n{path}")

def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
