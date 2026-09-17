---
name: aoi-cuda-profiler
description: >-
  Inspect GPU environment, verify CUDA/CuPy installation, monitor RTX 3090 VRAM usage,
  and profile kernel execution latency for AOI image processing pipelines.
  Use when testing GPU support or diagnosing memory leaks / frame drops.
---

# AOI CUDA & GPU Profiler Skill

This skill provides procedures to diagnose GPU acceleration readiness and profile latency for high-speed AOI inspection.

## Key Diagnosis Commands

1. **Check Hardware & Driver**:
   - Run `nvidia-smi` to verify GPU driver version, CUDA support, temperature, and VRAM availability.
2. **Check Python CUDA Bindings**:
   - Check if `cupy` is installed and matches the CUDA version (e.g. `cupy-cuda12x`).
   - Check if `torch.cuda.is_available()` or `cv2.cuda.getCudaEnabledDeviceCount() > 0`.
3. **Memory & Latency Profiling**:
   - Profile memory transfer latency: Host to Device (H2D) vs Device to Host (D2H).
   - Measure pinned memory performance for continuous frame ingestion from industrial cameras.
