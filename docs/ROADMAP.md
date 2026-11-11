# HEPATIC development roadmap

## Current 0.3.0
- CT DICOM import and axial viewer
- HU candidate mask (exploratory, not liver segmentation)
- ONNX inference integration point for a compatible externally trained model
- Voxel-count volumetry for the resulting mask
- STL surface export

## Next engineering milestones
1. Add mask overlay and manual slice-by-slice editing.
2. Integrate a validated liver segmentation model and dataset-specific preprocessing.
3. Add true multiplanar reconstruction and interactive 3D rendering.
4. Train/validate right/left lobe and Couinaud segment models.
5. Add separate portal vein, hepatic vein and hepatic artery segmentation.
6. Add tumor segmentation, virtual resection and FLR/GRWR calculation with clinical oversight.
7. Perform multi-vendor, multi-center external validation and usability testing.

Each AI task requires its own annotated dataset, locked test set, metrics and clinical review. A generic liver mask model cannot be assumed to identify lobes, Couinaud segments or vessels.
