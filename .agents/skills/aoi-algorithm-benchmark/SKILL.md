---
name: aoi-algorithm-benchmark
description: >-
  Benchmark and validate AOI algorithms against golden test samples.
  Use when comparing Python algorithm outputs with legacy C# OpenCvSharp results,
  verifying measurement precision tolerances, or evaluating CPU vs GPU execution times.
---

# AOI Algorithm Benchmark & Validation Skill

This skill provides step-by-step procedures to verify the correctness and performance of Python AOI algorithms against baseline C# measurements.

## Workflow

1. **Verify Golden Sample Dataset**:
   - Check if sample test images exist under `tests/fixtures/images/` or `AoiMeasureTool/` sample paths.
   - Inspect baseline results (corner coordinates, rotated rect angle, measured distances in pixels/mm, and A/B/NG judgements).

2. **Run Precision Equivalence Test**:
   - Execute pytest on `tests/test_algorithms/`.
   - Measure delta: `abs(python_distance - csharp_distance)`.
   - Required tolerance: `delta < 0.001 mm` (sub-pixel accurate).

3. **Run Performance Benchmark**:
   - Execute benchmark script measuring:
     - Preprocessing latency (Binarization, Dual-threshold, Morphology) on CPU vs GPU.
     - Reference corner search latency.
     - Measurement line edge-finding latency.
     - Total end-to-end processing time per frame (target: `< 15ms` for 60FPS throughput).
