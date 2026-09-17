from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger


class OnnxInferenceBackend:
    """AI / Deep Learning inference backend using ONNX Runtime (CUDA, DirectML, CPU)."""

    def __init__(self, preferred_provider: str | None = None) -> None:
        self._session: Any = None
        self._providers: list[str] = []
        self._model_path: Path | None = None
        self._input_names: list[str] = []
        self._output_names: list[str] = []
        self._ort: Any = None

        try:
            import onnxruntime as ort

            self._ort = ort
            available = ort.get_available_providers()
            # Prioritize providers: CUDA > DirectML > CPU
            priority = ["CUDAExecutionProvider", "DmlExecutionProvider", "CPUExecutionProvider"]
            self._providers = [p for p in priority if p in available]
            if preferred_provider and preferred_provider in available:
                self._providers.insert(0, preferred_provider)
        except ImportError:
            logger.info("ONNX Runtime not installed. ONNX inference backend disabled.")
        except Exception as e:
            logger.warning(f"Error checking ONNX Runtime providers: {e}")

    @property
    def name(self) -> str:
        return "ONNX"

    @property
    def is_available(self) -> bool:
        return self._ort is not None

    @property
    def is_loaded(self) -> bool:
        return self._session is not None

    def get_available_providers(self) -> list[str]:
        return list(self._providers)

    def load_model(self, model_path: str | Path) -> bool:
        if not self.is_available:
            logger.error("Cannot load ONNX model: onnxruntime not available.")
            return False

        path = Path(model_path)
        if not path.exists():
            logger.error(f"ONNX model file does not exist: {path}")
            return False

        try:
            self._session = self._ort.InferenceSession(str(path), providers=self._providers)
            self._input_names = [inp.name for inp in self._session.get_inputs()]
            self._output_names = [out.name for out in self._session.get_outputs()]
            self._model_path = path
            logger.info(
                f"Loaded ONNX model {path.name} with providers {self._session.get_providers()}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to load ONNX model {path}: {e}")
            self._session = None
            return False

    def infer(self, inputs: dict[str, np.ndarray] | np.ndarray) -> list[np.ndarray]:
        if not self.is_loaded or self._session is None:
            raise RuntimeError("No ONNX model loaded.")

        if isinstance(inputs, np.ndarray):
            if not self._input_names:
                raise RuntimeError("No model inputs defined.")
            feed = {self._input_names[0]: inputs}
        else:
            feed = inputs

        outputs = self._session.run(self._output_names, feed)
        return [np.asarray(out) for out in outputs]
