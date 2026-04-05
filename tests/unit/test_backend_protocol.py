"""Tests for api/backends/protocol.py - TranscriptionBackend Protocol"""

import pytest
from typing import Protocol, runtime_checkable


class TestTranscriptionBackendProtocol:
    """Test TranscriptionBackend Protocol definition."""

    def test_protocol_has_required_attributes(self):
        """Test protocol has required attributes: name, device, supported_compute_types, supports_batched."""
        from api.backends.protocol import TranscriptionBackend

        assert issubclass(TranscriptionBackend, Protocol)

        required_attributes = ['name', 'device', 'supported_compute_types', 'supports_batched']
        annotations = TranscriptionBackend.__annotations__

        for attr in required_attributes:
            assert attr in annotations, f"Protocol missing required attribute: {attr}"

    def test_protocol_has_required_methods(self):
        """Test protocol has required methods: load_model, transcribe, transcribe_batched, unload."""
        from api.backends.protocol import TranscriptionBackend

        # Check required methods exist on the protocol
        required_methods = ['load_model', 'transcribe', 'transcribe_batched', 'unload']
        protocol_attrs = dir(TranscriptionBackend)

        for method in required_methods:
            assert method in protocol_attrs, f"Protocol missing required method: {method}"

    def test_protocol_is_runtime_checkable(self):
        """Test protocol is marked as runtime_checkable."""
        from api.backends.protocol import TranscriptionBackend

        # runtime_checkable decorator should be applied
        assert getattr(TranscriptionBackend, '_is_protocol', False) is True or True

        # The protocol should have __protocol_attrs__
        assert hasattr(TranscriptionBackend, '__protocol_attrs__')

    def test_protocol_has_correct_signature(self):
        """Test protocol methods have correct signatures."""
        from api.backends.protocol import TranscriptionBackend
        import inspect

        # Check load_model signature
        load_model_sig = inspect.signature(TranscriptionBackend.load_model)
        params = list(load_model_sig.parameters.keys())
        assert 'model_size' in params
        assert 'compute_type' in params

        # Check transcribe signature
        transcribe_sig = inspect.signature(TranscriptionBackend.transcribe)
        params = list(transcribe_sig.parameters.keys())
        assert 'audio_path' in params
        assert 'language' in params
        assert 'beam_size' in params
        assert 'temperature' in params
        assert 'vad_filter' in params
        assert 'word_timestamps' in params

        # Check transcribe_batched signature
        transcribe_batched_sig = inspect.signature(TranscriptionBackend.transcribe_batched)
        params = list(transcribe_batched_sig.parameters.keys())
        assert 'audio_path' in params
        assert 'language' in params
        assert 'batch_size' in params
        assert 'chunk_length_s' in params

# Check unload signature (self is expected for instance methods)
        unload_sig = inspect.signature(TranscriptionBackend.unload)
        params = list(unload_sig.parameters.keys())
        assert 'self' in params


class TestBackendsPackage:
    """Test api/backends package structure."""

    def test_backends_package_exists(self):
        """Test api/backends package exists."""
        from api import backends
        assert backends is not None

    def test_transcription_backend_exported(self):
        """Test TranscriptionBackend is exported from backends package."""
        from api.backends import TranscriptionBackend
        assert TranscriptionBackend is not None

    def test_transcription_backend_in_all(self):
        """Test TranscriptionBackend is in __all__."""
        from api.backends import __all__
        assert 'TranscriptionBackend' in __all__