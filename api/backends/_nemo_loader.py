"""Lazy nemo ASR model loader — resolves only when load_model() is called."""
from __future__ import annotations

import importlib


def _get_asr_model():
    import nemo.collections.asr as nemo_asr

    return nemo_asr.models.ASRModel
