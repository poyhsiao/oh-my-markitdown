"""TranscriptionService — orchestration layer for multi-device transcription.

This service coordinates:
1. Device detection (DeviceDetector)
2. Strategy auto-configuration (TranscriptionStrategy)
3. Backend selection and model loading
4. Chunking engine dispatch (batched vs parallel)
5. Result formatting
"""
from api.device_detector import DeviceDetector


class TranscriptionService:
    """Orchestrates transcription across all devices and backends."""

    def __init__(self):
        self._detector = DeviceDetector()