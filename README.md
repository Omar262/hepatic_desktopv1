# HEPATIC™ — Advanced Liver Imaging

Windows desktop development application, rebranded from HEPAVISION. Version 0.3.0.

## Implemented in this build
- Import CT DICOM folders and group by Series Instance UID
- Sort slices using Image Position Patient / Image Orientation Patient when available
- Convert stored pixel values to HU using Rescale Slope and Rescale Intercept
- Axial viewing, slice navigation, Window/Level and CT presets
- Basic series metadata and JSON study summary
- **Exploratory HU candidate mask** (threshold-based only; not anatomical liver segmentation)
- **ONNX AI inference hook** for a user-supplied compatible 2D segmentation model
- Mask voxel-count volumetry using DICOM voxel spacing
- Export mask and source HU volume as compressed NPZ
- Generate and export a 3D surface mesh as STL from the current mask

## AI model requirements
No pretrained or clinically validated liver model is included. To run AI inference, provide an ONNX model with:
- Input: float32 `[1, 1, rows, columns]`
- Output: `[1, classes, rows, columns]` (class 0 background; non-zero classes are included) or `[1, 1, rows, columns]` (binary output)
- The current inference preprocessing clips HU to [-200, 300] and scales to [0, 1]. The model must have been trained with this exact preprocessing and compatible image dimensions. Fixed-shape models may fail if input dimensions differ.

The HU threshold feature is only a rough candidate mask and can include liver, vessels, spleen, muscle and other tissues. Its calculated volume must not be called liver volume. AI output also requires expert review and independent validation before any anatomical interpretation.

## 3D and volumetry notes
- Volume is calculated from mask voxel count multiplied by DICOM spacing, converted from mm³ to ml.
- STL export uses marching cubes and downsamples very large masks for memory management.
- Verify mesh orientation, scale, segmentation quality and anatomical correctness in a medical viewer.
- This release does not yet provide manual contour editing, true MPR, Couinaud segmentation, vascular tree extraction, tumor-specific models, virtual hepatectomy, FLR/GRWR clinical workflow, or validated reporting.

## Build a standalone Windows EXE
1. Extract this ZIP on Windows 10/11 64-bit.
2. Install Python 3.11 64-bit and enable PATH and Python Launcher.
3. Run `build_windows_exe.bat` and allow dependencies to install (internet required on build PC).
4. Run `dist\\HEPATIC\\HEPATIC.exe`.
5. Copy the entire `dist\\HEPATIC` folder to another PC, not only the EXE.

Python is not required on the target PC after building. Build and test the Windows executable on Windows; this Linux environment cannot verify a Windows binary.

## Safety and privacy
Research/development software only. Use anonymized test DICOM data. This is not a clinically validated medical device and must not be used for donor eligibility, graft selection or surgical decisions. A radiologist and transplant surgeon must review all outputs.
