"""Medical imaging role boundary.

Structured EMR data (FHIR -> terminology normalization -> rule engine -> ONNX risk model) and
medical imaging (DICOM/NIfTI -> MONAI -> segmentation/imaging AI -> ONNX/TensorRT -> 3D Patient
Digital Twin) are deliberately two separate pipelines. This app implements the first one fully.

This module is a placeholder for the second one. There is no PACS/DICOM connection, no MONAI
integration, and no real segmentation pipeline in this repository -- and per the frontend's
AnatomyImagingPanel, no synthetic lesion is ever generated just because an image exists. Wiring a
real one in means: a DICOM/NIfTI reader, a MONAI inference pipeline producing an actual
segmentation mask, and a marching-cubes (or equivalent) mesh export consumed by the SAME
`AnatomyImagingPanel` segmentation section that currently reports "no segmentation data" -- not a
new, separate 3D view.
"""

STATUS = {
    'configured': False,
    'pipeline': 'DICOM/NIfTI -> MONAI -> segmentation -> marching cubes -> 3D mesh',
    'reason': 'No PACS/DICOM source, MONAI runtime, or segmentation model is wired into this deployment.',
}


def health():
    return {'component': 'imaging_pipeline', 'status': 'not_configured', **STATUS}
