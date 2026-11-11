from __future__ import annotations

"""Exploratory AI/3D/volumetry tools for HEPATIC.

The ONNX contract is intentionally explicit: a 2D slice model accepting
float32 [1, 1, rows, columns] and returning either [1, classes, rows, columns]
(logits/probabilities) or [1, 1, rows, columns] (binary probability/logit).
No pretrained clinical model or weights are bundled.
"""

from pathlib import Path
import numpy as np

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog,
    QMessageBox, QDoubleSpinBox, QSpinBox, QFormLayout, QGroupBox
)


def dicom_volume(items):
    """Return HU volume [z,y,x], spacing (z,y,x) in mm and first dataset."""
    slices = [np.asarray(_hu(ds), dtype=np.float32) for ds, _ in items]
    volume = np.stack(slices, axis=0)
    ds0 = items[0][0]
    ps = getattr(ds0, 'PixelSpacing', [1.0, 1.0])
    sy, sx = float(ps[0]), float(ps[1])
    z_positions = []
    for ds, _ in items:
        try:
            z_positions.append(float(ds.ImagePositionPatient[2]))
        except Exception:
            z_positions = []
            break
    if len(z_positions) > 1:
        diffs = np.abs(np.diff(z_positions))
        diffs = diffs[diffs > 1e-4]
        sz = float(np.median(diffs)) if len(diffs) else float(getattr(ds0, 'SliceThickness', 1.0))
    else:
        sz = float(getattr(ds0, 'SpacingBetweenSlices', getattr(ds0, 'SliceThickness', 1.0)))
    return volume, (sz, sy, sx), ds0


def _hu(ds):
    a = ds.pixel_array.astype(np.float32)
    return a * float(getattr(ds, 'RescaleSlope', 1.0)) + float(getattr(ds, 'RescaleIntercept', 0.0))


class LiverToolsDialog(QDialog):
    def __init__(self, items, parent=None):
        super().__init__(parent)
        self.setWindowTitle('HEPATIC | AI • 3D • Liver Volumetry')
        self.resize(620, 470)
        self.items = items
        self.mask = None
        self.volume = None
        self.spacing = None
        self.model_path = None
        self._build()
        self.setStyleSheet('''
          QDialog,QWidget { background:#0b1930; color:#edf4ff; font-family:Segoe UI; }
          QGroupBox { border:1px solid #31506c; margin-top:10px; padding:10px; }
          QGroupBox::title { color:#e5bd69; }
          QPushButton { background:#17466b; border:1px solid #39759a; padding:8px; border-radius:5px; }
          QPushButton:hover { background:#21618e; }
          QLabel#metric { color:#f0c66d; font-size:17px; font-weight:700; }
        ''')

    def _build(self):
        root = QVBoxLayout(self)
        title = QLabel('HEPATIC™  |  LIVER ANALYSIS WORKSPACE')
        title.setStyleSheet('font-size:18px;font-weight:700;color:#e7bd68;')
        root.addWidget(title)
        info = QLabel('Generate a preliminary HU candidate mask or run a compatible, locally supplied ONNX segmentation model. Review every mask before using measurements.')
        info.setWordWrap(True)
        root.addWidget(info)

        prep = QGroupBox('1. Exploratory HU candidate mask')
        form = QFormLayout(prep)
        self.hu_low = QDoubleSpinBox(); self.hu_low.setRange(-1000, 3000); self.hu_low.setValue(40)
        self.hu_high = QDoubleSpinBox(); self.hu_high.setRange(-1000, 3000); self.hu_high.setValue(180)
        form.addRow('Lower HU', self.hu_low)
        form.addRow('Upper HU', self.hu_high)
        btn = QPushButton('Create HU candidate mask')
        btn.clicked.connect(self.create_threshold_mask)
        form.addRow(btn)
        root.addWidget(prep)

        ai = QGroupBox('2. AI segmentation (ONNX model)')
        row = QHBoxLayout(ai)
        self.model_label = QLabel('No model selected')
        self.model_label.setWordWrap(True)
        choose = QPushButton('Choose ONNX model…')
        choose.clicked.connect(self.choose_model)
        run = QPushButton('Run AI segmentation')
        run.clicked.connect(self.run_ai)
        row.addWidget(self.model_label, 1); row.addWidget(choose); row.addWidget(run)
        root.addWidget(ai)

        results = QGroupBox('3. Volumetry & 3D export')
        r = QVBoxLayout(results)
        self.metrics = QLabel('No segmentation mask available')
        self.metrics.setObjectName('metric')
        self.metrics.setWordWrap(True)
        r.addWidget(self.metrics)
        buttons = QHBoxLayout()
        save = QPushButton('Save mask (.npz)'); save.clicked.connect(self.save_mask)
        stl = QPushButton('Export 3D surface (.stl)'); stl.clicked.connect(self.export_stl)
        buttons.addWidget(save); buttons.addWidget(stl)
        r.addLayout(buttons)
        root.addWidget(results)

        warning = QLabel('RESEARCH / DEVELOPMENT ONLY • HU thresholding is not liver segmentation. ONNX results depend entirely on the selected model, its training data and its validation. This tool is not for donor selection or surgical decisions.')
        warning.setWordWrap(True)
        warning.setStyleSheet('color:#ffcc80;font-size:11px;padding:6px;')
        root.addWidget(warning)

    def _update_metrics(self, method):
        if self.mask is None:
            return
        voxel_ml = float(np.prod(self.spacing)) / 1000.0
        count = int(np.count_nonzero(self.mask))
        ml = count * voxel_ml
        self.metrics.setText(f'Method: {method}\nMask voxels: {count:,}\nVoxel volume: {voxel_ml:.5f} ml\nEstimated mask volume: {ml:,.1f} ml\nDimensions (Z×Y×X): {self.mask.shape}')

    def create_threshold_mask(self):
        try:
            vol, spacing, _ = dicom_volume(self.items)
            lo, hi = self.hu_low.value(), self.hu_high.value()
            if lo >= hi:
                raise ValueError('Lower HU must be less than Upper HU.')
            self.volume, self.spacing = vol, spacing
            self.mask = (vol >= lo) & (vol <= hi)
            self._update_metrics('HU threshold candidate (NOT AI / NOT anatomical liver mask)')
            QMessageBox.information(self, 'Candidate mask created', 'A threshold-based candidate mask was created. It may include vessels, spleen, muscle or other tissues. It is not a validated liver segmentation.')
        except Exception as exc:
            QMessageBox.critical(self, 'Mask error', str(exc))

    def choose_model(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Select compatible ONNX model', '', 'ONNX model (*.onnx)')
        if path:
            self.model_path = path
            self.model_label.setText(Path(path).name)

    def run_ai(self):
        if not self.model_path:
            QMessageBox.information(self, 'Model required', 'Select a trained ONNX model first. No pretrained liver transplant model is bundled with HEPATIC.')
            return
        try:
            import onnxruntime as ort
            vol, spacing, _ = dicom_volume(self.items)
            session = ort.InferenceSession(self.model_path, providers=['CPUExecutionProvider'])
            inp = session.get_inputs()[0]
            if len(inp.shape) != 4:
                raise ValueError('Expected a 2D slice model input shaped [1, 1, rows, columns].')
            name = inp.name
            out_name = session.get_outputs()[0].name
            # Stable liver-window normalization; model-specific preprocessing may differ.
            x = np.clip(vol, -200, 300)
            x = ((x + 200.0) / 500.0).astype(np.float32)
            pred = np.zeros(vol.shape, dtype=np.uint8)
            for z in range(x.shape[0]):
                result = session.run([out_name], {name: x[z][None, None, :, :]})[0]
                result = np.asarray(result)
                if result.ndim != 4 or result.shape[0] != 1:
                    raise ValueError('Model output must be [1, classes, rows, columns] or [1, 1, rows, columns].')
                if result.shape[-2:] != vol.shape[1:]:
                    raise ValueError('Model output image dimensions must match the input slice dimensions.')
                if result.shape[1] == 1:
                    plane = result[0, 0]
                    pred[z] = (plane > 0.5 if plane.min() >= 0 and plane.max() <= 1 else plane > 0).astype(np.uint8)
                else:
                    pred[z] = np.argmax(result[0], axis=0).astype(np.uint8)
            # For multi-class models, class 1 is treated as target by documented convention.
            self.volume, self.spacing, self.mask = vol, spacing, pred > 0
            self._update_metrics('User-supplied ONNX AI model (all non-background classes)')
            QMessageBox.information(self, 'AI inference complete', 'Inference finished. Review the mask carefully. Confirm model class mapping, preprocessing and validation before interpreting the volume.')
        except ImportError:
            QMessageBox.critical(self, 'Missing dependency', 'ONNX Runtime is not installed. Rebuild using the updated requirements.txt.')
        except Exception as exc:
            QMessageBox.critical(self, 'AI inference failed', str(exc))

    def save_mask(self):
        if self.mask is None:
            QMessageBox.information(self, 'No mask', 'Create or run a segmentation first.')
            return
        path, _ = QFileDialog.getSaveFileName(self, 'Save segmentation mask', 'hepatic_mask.npz', 'NumPy archive (*.npz)')
        if not path: return
        np.savez_compressed(path, mask=self.mask.astype(np.uint8), spacing_zyx=np.asarray(self.spacing), hu_volume=self.volume)
        QMessageBox.information(self, 'Saved', f'Mask and source HU volume saved:\n{path}')

    def export_stl(self):
        if self.mask is None:
            QMessageBox.information(self, 'No mask', 'Create or run a segmentation first.')
            return
        if not np.any(self.mask):
            QMessageBox.warning(self, 'Empty mask', 'The current mask is empty.')
            return
        path, _ = QFileDialog.getSaveFileName(self, 'Export 3D surface', 'hepatic_surface.stl', 'STL mesh (*.stl)')
        if not path: return
        try:
            from skimage.measure import marching_cubes
            import trimesh
            # Downsample very large masks to reduce peak memory and mesh size.
            step = max(1, int(np.ceil(max(self.mask.shape) / 384)))
            sampled = self.mask[::step, ::step, ::step].astype(np.uint8)
            if min(sampled.shape) < 2:
                raise ValueError('Volume is too small to create a surface.')
            verts, faces, _, _ = marching_cubes(sampled, level=0.5)
            scale = np.asarray(self.spacing, dtype=float) * step
            verts = verts * scale[None, :]
            mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=True)
            mesh.export(path)
            QMessageBox.information(self, '3D surface exported', f'STL surface saved:\n{path}\n\nNote: mesh orientation follows the voxel array axes; verify orientation and scale in a medical viewer.')
        except ImportError:
            QMessageBox.critical(self, 'Missing dependency', 'Install scikit-image and trimesh by rebuilding with the updated requirements.txt.')
        except Exception as exc:
            QMessageBox.critical(self, '3D export failed', str(exc))
