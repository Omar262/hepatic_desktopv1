# HEPAVISION Complete Platform Architecture

## Design principles
- CPU-first and memory-aware for the initial Windows 10 / 8 GB development workstation.
- Modular boundaries: DICOM ingestion, image review, segmentation, quantitative analysis, visualization, reporting, and web access.
- Prefer established medical-imaging engines over reimplementing validated algorithms.
- Keep research/prototype outputs separate from clinically approved outputs.

## Logical architecture

```text
                  HEPAVISION Desktop (PySide6)
                              |
                   Application / Study Layer
                              |
       +----------------------+-----------------------+
       |                      |                       |
 DICOM Ingestion         Review Engine          Project/Report
 (pydicom now;           (2D now; MPR             (JSON now;
 Orthanc later)           next; 3D later)          PDF next)
       |                      |                       |
       +----------------------+-----------------------+
                              |
                    Processing Adapters
             +----------------+----------------+
             |                |                |
         3D Slicer         MONAI Label       VTK/SimpleITK
       segmentation       AI assistance     image/3D tools
             |
         Quantification
   Liver / lobes / Couinaud / tumor / vessels / FLR
                              |
                  Interoperability Services
               DICOM / DICOMweb / NIfTI / STL
                              |
                 Orthanc + OHIF Web Viewer
```

## Module contracts
1. `dicom_ingest`: scan, validate, group by Study/Series UID, geometrically sort slices, preserve metadata.
2. `image_review`: HU conversion, orientation-aware display, MPR, measurements, window/level.
3. `segmentation`: manual editing first; assisted model integration only after validation.
4. `quantification`: voxel volume from spacing and mask; report per-label volumes with units.
5. `vascular`: vessel segmentation and centerline/branch visualization; not included in v0.2.
6. `surgical_planning`: resection planes and FLR calculations; requires validated segmentation and explicit functional liver assumptions.
7. `web`: Orthanc DICOM server + DICOMweb + OHIF, secured behind authentication/TLS.
8. `reporting`: structured measurements, provenance, software/model versions, PDF export.

## Low-resource deployment profile
- Do not load all series into RAM simultaneously.
- Load selected series only; cache current slice and a small neighborhood.
- Use CPU-only inference initially; do not ship large AI models in the base installer.
- Make 3D reconstruction an on-demand operation.
- Recommend 16 GB RAM for routine larger studies; 32 GB for heavier 3D/AI workflows.
- Keep Orthanc/Web services optional and local-only by default.

## Data correctness requirements
- HU = stored pixel value × RescaleSlope + RescaleIntercept (handle per-slice values).
- Sort by projection of ImagePositionPatient onto slice normal derived from ImageOrientationPatient; do not sort by filename.
- Respect PixelSpacing, orientation, position, and actual inter-slice geometry.
- Separate contrast phases/series; never merge different SeriesInstanceUIDs.
- Handle Enhanced CT multi-frame separately (future adapter).
- Reject or flag inconsistent geometry and missing metadata.
- Never assume SliceThickness equals actual slice spacing.

## Clinical validation gates
No segmentation, lobe volume, Couinaud, vessel, tumor, or FLR result should be labeled clinically validated until compared with expert-reviewed reference cases, documented acceptance criteria, inter-/intra-observer variability, and independent testing. FLR is a planning metric, not a standalone determination of surgical eligibility.
