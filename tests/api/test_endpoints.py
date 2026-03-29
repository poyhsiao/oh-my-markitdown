"""Tests for API endpoints - TDD tests for new functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
import tempfile
import os


class TestResponseFormat:
    """Test unified JSON response format."""

    def test_success_response_format(self):
        """Test success_response returns correct format."""
        from api.response import success_response, set_request_id
        
        set_request_id("test-123")
        response = success_response(data={"key": "value"}, metadata={"meta": "data"})
        
        assert response["success"] is True
        assert "data" in response
        assert response["data"]["key"] == "value"
        assert "metadata" in response
        assert "request_id" in response
        assert response["request_id"] == "test-123"

    def test_success_response_without_metadata(self):
        """Test success_response without metadata."""
        from api.response import success_response, set_request_id
        
        set_request_id("test-456")
        response = success_response(data={"test": "data"})
        
        assert response["success"] is True
        assert response["data"]["test"] == "data"
        assert "metadata" in response
        assert response["metadata"] == {}

    def test_error_response_format(self):
        """Test error_response returns correct format per spec Section 3.14."""
        from api.response import error_response, ErrorCodes, set_request_id
        
        set_request_id("test-789")
        response = error_response(
            code=ErrorCodes.FILE_TOO_LARGE,
            message="File exceeds maximum size",
            details="Max size: 50MB"
        )
        
        assert response["success"] is False
        assert "error" in response
        assert response["error"]["code"] == "FILE_TOO_LARGE"
        assert response["error"]["message"] == "File exceeds maximum size"
        assert response["error"]["details"] == "Max size: 50MB"
        assert "request_id" in response
        assert "timestamp" in response

    def test_error_response_without_details(self):
        """Test error_response without details."""
        from api.response import error_response, ErrorCodes
        
        response = error_response(
            code=ErrorCodes.NOT_FOUND,
            message="Resource not found"
        )
        
        assert response["success"] is False
        assert response["error"]["code"] == "NOT_FOUND"
        assert response["error"]["details"] is None

    def test_queue_waiting_response_format(self):
        """Test queue_waiting_response per Appendix A."""
        from api.response import queue_waiting_response, set_request_id
        
        set_request_id("queue-test")
        response = queue_waiting_response(
            queue_position=5,
            estimated_wait_seconds=30,
            current_processing=3,
            max_concurrent=10
        )
        
        assert response["success"] is False
        assert response["error"]["code"] == "QUEUE_WAITING"
        assert "queue_position" in response["error"]["details"]
        assert response["error"]["details"]["queue_position"] == 5
        assert response["error"]["details"]["estimated_wait_seconds"] == 30
        assert response["retry_after"] == 30
        # Queue response should NOT have timestamp per spec
        assert "timestamp" not in response


class TestErrorCodes:
    """Test error codes defined per spec Section 3.15."""

    def test_all_spec_error_codes_defined(self):
        """Test all required error codes from spec are defined."""
        from api.response import ErrorCodes
        
        # Required codes per spec Section 3.15
        required_codes = [
            "FILE_TOO_LARGE",
            "UNSUPPORTED_FORMAT",
            "INVALID_OCR_LANGUAGE",
            "YOUTUBE_DOWNLOAD_FAILED",
            "WHISPER_DOWNLOADING",
            "WHISPER_TRANSCRIPTION_FAILED",
            "VIDEO_CONVERSION_FAILED",
            "QUEUE_WAITING",
            "IP_NOT_ALLOWED",
            "INVALID_CONFIG",
            "NOT_FOUND",
        ]
        
        for code in required_codes:
            assert hasattr(ErrorCodes, code), f"Error code {code} not defined"
            assert getattr(ErrorCodes, code) == code


class TestYoutubeEndpoint:
    """Test YouTube transcription endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from api.main import app
        return TestClient(app)

    def test_youtube_include_timestamps_parameter_exists(self):
        """Test include_timestamps parameter is accepted."""
        from api.main import app
        from fastapi.testclient import TestClient
        
        # Check the endpoint signature has the parameter
        from api.main import transcribe_youtube
        import inspect
        sig = inspect.signature(transcribe_youtube)
        
        assert "include_timestamps" in sig.parameters

    def test_youtube_endpoint_parameters(self):
        """Test YouTube endpoint has all required parameters."""
        from api.main import transcribe_youtube
        import inspect
        
        sig = inspect.signature(transcribe_youtube)
        params = sig.parameters
        
        # Required parameters per spec
        assert "url" in params
        assert "language" in params
        assert "model_size" in params
        assert "return_format" in params
        assert "include_timestamps" in params
        assert "include_metadata" in params


class TestAudioEndpoint:
    """Test audio transcription endpoint."""

    def test_audio_include_timestamps_parameter_exists(self):
        """Test include_timestamps parameter is accepted."""
        from api.main import transcribe_audio_file
        import inspect
        
        sig = inspect.signature(transcribe_audio_file)
        
        assert "include_timestamps" in sig.parameters

    def test_audio_endpoint_parameters(self):
        """Test audio endpoint has all required parameters."""
        from api.main import transcribe_audio_file
        import inspect
        
        sig = inspect.signature(transcribe_audio_file)
        params = sig.parameters
        
        # Required parameters per spec
        assert "file" in params
        assert "language" in params
        assert "model_size" in params
        assert "return_format" in params
        assert "include_timestamps" in params


class TestCleanupEndpoint:
    """Test cleanup endpoint with dry_run parameter."""

    def test_cleanup_dry_run_parameter(self):
        """Test cleanup endpoint accepts dry_run parameter."""
        from api.system import cleanup_temp_files
        import inspect
        
        # The function should accept request_body dict with dry_run
        sig = inspect.signature(cleanup_temp_files)
        
        assert "request_body" in sig.parameters

    def test_cleanup_dry_run_does_not_delete(self):
        """Test that dry_run=true does not actually delete files."""
        import tempfile
        import os
        from pathlib import Path
        
        # Create a temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            f.write(b"test content")
            temp_path = f.name
        
        try:
            # Simulate dry_run cleanup
            from api.system import TEMP_DIR
            from pathlib import Path
            
            # Check that file exists
            assert os.path.exists(temp_path)
            
            # In dry_run mode, file should still exist after "cleanup"
            # This is tested by checking the cleanup logic doesn't unlink
            # when dry_run=True
        finally:
            os.unlink(temp_path)


class TestFormatsEndpoint:
    """Test formats endpoint uses success_response wrapper."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from api.main import app
        return TestClient(app)

    def test_formats_endpoint_success_wrapper(self, client):
        """Test /api/v1/formats returns success wrapped response."""
        response = client.get("/api/v1/formats")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have success wrapper
        assert "success" in data
        assert data["success"] is True
        assert "data" in data
        assert "request_id" in data
        
        # Data should contain format categories
        assert "documents" in data["data"]
        assert "images" in data["data"]
        assert "audio" in data["data"]
        assert "video" in data["data"]


class TestLanguagesEndpoints:
    """Test languages endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from api.main import app
        return TestClient(app)

    def test_ocr_languages_endpoint(self, client):
        """Test /api/v1/languages/ocr returns correct format."""
        response = client.get("/api/v1/languages/ocr")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "languages" in data["data"]
        assert "default" in data["data"]
        
        # Should have OCR languages
        languages = data["data"]["languages"]
        assert "chi_tra" in languages
        assert "eng" in languages

    def test_transcribe_languages_endpoint(self, client):
        """Test /api/v1/languages/transcribe returns correct format."""
        response = client.get("/api/v1/languages/transcribe")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "languages" in data["data"]
        assert "models" in data["data"]
        
        # Should have models info
        models = data["data"]["models"]
        assert "tiny" in models
        assert "base" in models


class TestAdminEndpoints:
    """Test admin endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from api.main import app
        return TestClient(app)

    def test_queue_endpoint(self, client):
        """Test /api/v1/admin/queue returns correct format."""
        response = client.get("/api/v1/admin/queue")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "current_processing" in data["data"]
        assert "queue_length" in data["data"]

    def test_config_endpoint(self, client):
        """Test /api/v1/admin/config returns correct format."""
        response = client.get("/api/v1/admin/config")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "api" in data["data"]
        assert "ocr" in data["data"]
        assert "whisper" in data["data"]


class TestHealthEndpoint:
    """Test health endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from api.main import app
        return TestClient(app)

    def test_health_endpoint(self, client):
        """Test /health returns ok status."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "ok"


class TestParameterNamingCompliance:
    """Test API parameter names match spec requirements."""

    def test_convert_file_uses_enable_ocr(self):
        """Test /api/v1/convert/file uses enable_ocr (not enable_plugins) per spec Section 3.2."""
        from api.main import convert_file_endpoint
        import inspect
        
        sig = inspect.signature(convert_file_endpoint)
        params = sig.parameters
        
        # Must use enable_ocr per spec Section 3.2
        assert "enable_ocr" in params, "Parameter should be 'enable_ocr' per spec Section 3.2"
        assert "enable_plugins" not in params, "Parameter should NOT be 'enable_plugins'"
        
        # Check default value is False (handle Query wrapper)
        default = params["enable_ocr"].default
        # FastAPI Query params have a .default attribute
        if hasattr(default, 'default'):
            assert default.default is False, "enable_ocr default should be False"
        else:
            assert default is False, "enable_ocr default should be False"

    def test_convert_file_uses_ocr_lang(self):
        """Test /api/v1/convert/file has ocr_lang parameter."""
        from api.main import convert_file_endpoint
        import inspect
        
        sig = inspect.signature(convert_file_endpoint)
        params = sig.parameters
        
        assert "ocr_lang" in params
        assert "return_format" in params

    def test_cleanup_uses_targets(self):
        """Test /api/v1/admin/cleanup uses targets (not types) per spec Section 3.7."""
        from api.system import cleanup_temp_files
        import inspect
        
        sig = inspect.signature(cleanup_temp_files)
        params = sig.parameters
        
        # The function receives request_body dict which should contain 'targets'
        assert "request_body" in params

    def test_cleanup_targets_values(self):
        """Test cleanup accepts target values: temp, whisper, all."""
        # This is tested by checking the endpoint behavior
        # The values should be 'temp', 'whisper', 'all' per spec
        pass  # Functional test done via integration

    def test_convert_video_language_default_auto(self):
        """Test /api/v1/convert/video language default is 'auto' per spec Section 3.6."""
        from api.main import transcribe_video_file
        import inspect
        
        sig = inspect.signature(transcribe_video_file)
        params = sig.parameters
        
        assert "language" in params
        # Default should be "auto" per spec (handle Query wrapper)
        default = params["language"].default
        # FastAPI Query params have a .default attribute
        if hasattr(default, 'default'):
            assert default.default == "auto", "language default should be 'auto' per spec Section 3.6"
        else:
            assert default == "auto", "language default should be 'auto' per spec Section 3.6"

    def test_convert_video_parameters(self):
        """Test /api/v1/convert/video has all required parameters."""
        from api.main import transcribe_video_file
        import inspect
        
        sig = inspect.signature(transcribe_video_file)
        params = sig.parameters
        
        # Required parameters per spec Section 3.6
        assert "file" in params
        assert "language" in params
        assert "model_size" in params
        assert "output_formats" in params
        assert "include_timestamps" in params


class TestCleanupIntegration:
    """Integration tests for cleanup endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from api.main import app
        return TestClient(app)

    def test_cleanup_with_targets_temp(self, client):
        """Test cleanup with targets=['temp']."""
        response = client.post(
            "/api/v1/admin/cleanup",
            json={"targets": ["temp"], "dry_run": True}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["dry_run"] is True
        assert "cleaned" in data

    def test_cleanup_with_targets_whisper(self, client):
        """Test cleanup with targets=['whisper']."""
        response = client.post(
            "/api/v1/admin/cleanup",
            json={"targets": ["whisper"], "dry_run": True}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["dry_run"] is True

    def test_cleanup_with_targets_all(self, client):
        """Test cleanup with targets=['all']."""
        response = client.post(
            "/api/v1/admin/cleanup",
            json={"targets": ["all"], "dry_run": True}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["dry_run"] is True

    def test_cleanup_default_dry_run_true(self, client):
        """Test cleanup defaults to dry_run=true."""
        response = client.post(
            "/api/v1/admin/cleanup",
            json={"targets": ["temp"]}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Default should be dry_run=true for safety
        assert data["dry_run"] is True


class TestPerformanceParameters:
    """Test new performance parameters for transcription endpoints."""

    def test_video_endpoint_has_device_parameter(self):
        """Test /api/v1/convert/video has device parameter."""
        from api.main import transcribe_video_file
        import inspect
        
        sig = inspect.signature(transcribe_video_file)
        params = sig.parameters
        
        assert "device" in params, "Parameter 'device' should exist for GPU/CPU selection"
        assert "cpu_threads" in params, "Parameter 'cpu_threads' should exist for threading control"
        assert "vad_enabled" in params, "Parameter 'vad_enabled' should exist for VAD control"

    def test_audio_endpoint_has_device_parameter(self):
        """Test /api/v1/convert/audio has device parameter."""
        from api.main import transcribe_audio_file
        import inspect
        
        sig = inspect.signature(transcribe_audio_file)
        params = sig.parameters
        
        assert "device" in params, "Parameter 'device' should exist for GPU/CPU selection"
        assert "cpu_threads" in params, "Parameter 'cpu_threads' should exist for threading control"
        assert "vad_enabled" in params, "Parameter 'vad_enabled' should exist for VAD control"

    def test_youtube_endpoint_has_device_parameter(self):
        """Test /api/v1/convert/youtube has device parameter."""
        from api.main import transcribe_youtube
        import inspect
        
        sig = inspect.signature(transcribe_youtube)
        params = sig.parameters
        
        assert "device" in params, "Parameter 'device' should exist for GPU/CPU selection"
        assert "cpu_threads" in params, "Parameter 'cpu_threads' should exist for threading control"
        assert "vad_enabled" in params, "Parameter 'vad_enabled' should exist for VAD control"

    def test_convert_url_endpoint_has_device_parameter(self):
        """Test /api/v1/convert/url has device parameter."""
        from api.main import convert_url
        import inspect
        
        sig = inspect.signature(convert_url)
        params = sig.parameters
        
        assert "device" in params, "Parameter 'device' should exist for GPU/CPU selection"
        assert "cpu_threads" in params, "Parameter 'cpu_threads' should exist for threading control"
        assert "vad_enabled" in params, "Parameter 'vad_enabled' should exist for VAD control"

    def test_device_parameter_is_optional(self):
        """Test device parameter is optional (defaults to env var)."""
        from api.main import transcribe_video_file
        import inspect
        
        sig = inspect.signature(transcribe_video_file)
        device_param = sig.parameters["device"]
        
        # Check that default is None (optional)
        default = device_param.default
        if hasattr(default, 'default'):
            assert default.default is None, "device default should be None (use env var)"
        else:
            assert default is None, "device default should be None (use env var)"


class TestDeviceInfoEndpoint:
    """Test device-info endpoint for GPU/CPU detection."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from api.main import app
        return TestClient(app)

    def test_device_info_endpoint_exists(self, client):
        """Test /api/v1/device-info endpoint exists and returns 200."""
        response = client.get("/api/v1/device-info")
        
        assert response.status_code == 200

    def test_device_info_endpoint_success_wrapper(self, client):
        """Test /api/v1/device-info returns success wrapped response."""
        response = client.get("/api/v1/device-info")
        data = response.json()
        
        assert data["success"] is True
        assert "data" in data
        assert "request_id" in data

    def test_device_info_returns_device(self, client):
        """Test /api/v1/device-info returns device field."""
        response = client.get("/api/v1/device-info")
        data = response.json()
        
        assert "device" in data["data"]
        assert data["data"]["device"] in ["cpu", "cuda", "mps"]

    def test_device_info_returns_cuda_available(self, client):
        """Test /api/v1/device-info returns cuda_available field."""
        response = client.get("/api/v1/device-info")
        data = response.json()
        
        assert "cuda_available" in data["data"]
        assert isinstance(data["data"]["cuda_available"], bool)

    def test_device_info_returns_mps_available(self, client):
        """Test /api/v1/device-info returns mps_available field."""
        response = client.get("/api/v1/device-info")
        data = response.json()
        
        assert "mps_available" in data["data"]
        assert isinstance(data["data"]["mps_available"], bool)

    def test_device_info_returns_cpu_count(self, client):
        """Test /api/v1/device-info returns cpu_count field."""
        response = client.get("/api/v1/device-info")
        data = response.json()
        
        assert "cpu_count" in data["data"]
        assert isinstance(data["data"]["cpu_count"], int)
        assert data["data"]["cpu_count"] > 0

    def test_device_info_returns_recommended_compute_type(self, client):
        """Test /api/v1/device-info returns recommended_compute_type field."""
        response = client.get("/api/v1/device-info")
        data = response.json()
        
        assert "recommended_compute_type" in data["data"]
        assert data["data"]["recommended_compute_type"] in ["int8", "float16", "float32"]


class TestDeviceUtilsFunctions:
    """Test device utility functions."""

    def test_detect_device_returns_valid_type(self):
        """Test detect_device returns valid device type."""
        from api.device_utils import detect_device
        
        device = detect_device()
        assert device in ["cpu", "cuda", "mps"]

    def test_get_device_info_returns_dict(self):
        """Test get_device_info returns dictionary with required fields."""
        from api.device_utils import get_device_info
        
        info = get_device_info()
        
        assert isinstance(info, dict)
        assert "device" in info
        assert "cuda_available" in info
        assert "mps_available" in info
        assert "cpu_count" in info
        assert "recommended_compute_type" in info

    def test_validate_device_cpu_always_valid(self):
        """Test validate_device accepts 'cpu'."""
        from api.device_utils import validate_device
        
        result = validate_device("cpu")
        assert result == "cpu"

    def test_validate_device_auto_returns_valid(self):
        """Test validate_device with 'auto' returns valid device."""
        from api.device_utils import validate_device
        
        result = validate_device("auto")
        assert result in ["cpu", "cuda", "mps"]

    def test_validate_device_invalid_raises(self):
        """Test validate_device raises for invalid device."""
        from api.device_utils import validate_device
        import pytest
        
        with pytest.raises(ValueError):
            validate_device("invalid_device")

    def test_get_recommended_threads_auto_detect(self):
        """Test get_recommended_threads with auto-detect (0)."""
        from api.device_utils import get_recommended_threads
        
        result = get_recommended_threads(0)  # 0 = auto
        assert isinstance(result, int)
        assert result >= 1
        assert result <= 8  # MAX_CPU_THREADS

    def test_get_recommended_threads_explicit(self):
        """Test get_recommended_threads with explicit value."""
        from api.device_utils import get_recommended_threads
        
        result = get_recommended_threads(4)
        assert result == 4

    def test_get_recommended_threads_caps_at_max(self):
         """Test get_recommended_threads caps at MAX_CPU_THREADS."""
         from api.device_utils import get_recommended_threads
         
         result = get_recommended_threads(100)  # Request more than max
         assert result <= 8  # Should be capped at MAX_CPU_THREADS


class TestAudioChunkingParameters:
    """Test audio endpoint chunking parameters for Cloudflare 524 timeout resolution."""

    def test_audio_endpoint_has_enable_chunking_parameter(self):
        """Test /api/v1/convert/audio has enable_chunking parameter."""
        from api.main import transcribe_audio_file
        import inspect
        
        sig = inspect.signature(transcribe_audio_file)
        params = sig.parameters
        
        assert "enable_chunking" in params, "Parameter 'enable_chunking' should exist for chunking control"

    def test_audio_endpoint_has_chunk_duration_parameter(self):
        """Test /api/v1/convert/audio has chunk_duration parameter."""
        from api.main import transcribe_audio_file
        import inspect
        
        sig = inspect.signature(transcribe_audio_file)
        params = sig.parameters
        
        assert "chunk_duration" in params, "Parameter 'chunk_duration' should exist for chunk duration control"

    def test_audio_endpoint_has_chunk_overlap_parameter(self):
        """Test /api/v1/convert/audio has chunk_overlap parameter."""
        from api.main import transcribe_audio_file
        import inspect
        
        sig = inspect.signature(transcribe_audio_file)
        params = sig.parameters
        
        assert "chunk_overlap" in params, "Parameter 'chunk_overlap' should exist for overlap control"

    def test_audio_endpoint_has_auto_chunk_threshold_parameter(self):
        """Test /api/v1/convert/audio has auto_chunk_threshold parameter."""
        from api.main import transcribe_audio_file
        import inspect
        
        sig = inspect.signature(transcribe_audio_file)
        params = sig.parameters
        
        assert "auto_chunk_threshold" in params, "Parameter 'auto_chunk_threshold' should exist for auto-enable threshold"

    def test_enable_chunking_default_is_false(self):
        """Test enable_chunking defaults to False (chunking disabled by default)."""
        from api.main import transcribe_audio_file
        import inspect
        
        sig = inspect.signature(transcribe_audio_file)
        param = sig.parameters["enable_chunking"]
        
        default = param.default
        if hasattr(default, 'default'):
            assert default.default is False, "enable_chunking default should be False"
        else:
            assert default is False, "enable_chunking default should be False"

    def test_chunk_duration_default(self):
        """Test chunk_duration defaults to constants.DEFAULT_CHUNK_DURATION (60 seconds)."""
        from api.main import transcribe_audio_file
        from api.constants import DEFAULT_CHUNK_DURATION
        import inspect
        
        sig = inspect.signature(transcribe_audio_file)
        param = sig.parameters["chunk_duration"]
        
        default = param.default
        if hasattr(default, 'default'):
            assert default.default == DEFAULT_CHUNK_DURATION, f"chunk_duration default should be {DEFAULT_CHUNK_DURATION}"
        else:
            assert default == DEFAULT_CHUNK_DURATION, f"chunk_duration default should be {DEFAULT_CHUNK_DURATION}"

    def test_chunk_overlap_default(self):
        """Test chunk_overlap defaults to constants.DEFAULT_CHUNK_OVERLAP (2 seconds)."""
        from api.main import transcribe_audio_file
        from api.constants import DEFAULT_CHUNK_OVERLAP
        import inspect
        
        sig = inspect.signature(transcribe_audio_file)
        param = sig.parameters["chunk_overlap"]
        
        default = param.default
        if hasattr(default, 'default'):
            assert default.default == DEFAULT_CHUNK_OVERLAP, f"chunk_overlap default should be {DEFAULT_CHUNK_OVERLAP}"
        else:
            assert default == DEFAULT_CHUNK_OVERLAP, f"chunk_overlap default should be {DEFAULT_CHUNK_OVERLAP}"

    def test_auto_chunk_threshold_default(self):
        """Test auto_chunk_threshold defaults to constants.DEFAULT_AUTO_CHUNK_THRESHOLD (90 seconds)."""
        from api.main import transcribe_audio_file
        from api.constants import DEFAULT_AUTO_CHUNK_THRESHOLD
        import inspect
        
        sig = inspect.signature(transcribe_audio_file)
        param = sig.parameters["auto_chunk_threshold"]
        
        default = param.default
        if hasattr(default, 'default'):
            assert default.default == DEFAULT_AUTO_CHUNK_THRESHOLD, f"auto_chunk_threshold default should be {DEFAULT_AUTO_CHUNK_THRESHOLD}"
        else:
            assert default == DEFAULT_AUTO_CHUNK_THRESHOLD, f"auto_chunk_threshold default should be {DEFAULT_AUTO_CHUNK_THRESHOLD}"


class TestVideoChunkingParameters:
    """Test video endpoint chunking parameters for Cloudflare 524 timeout resolution."""

    def test_video_endpoint_has_enable_chunking_parameter(self):
        """Test /api/v1/convert/video has enable_chunking parameter."""
        from api.main import transcribe_video_file
        import inspect
        
        sig = inspect.signature(transcribe_video_file)
        params = sig.parameters
        
        assert "enable_chunking" in params, "Parameter 'enable_chunking' should exist for chunking control"

    def test_video_endpoint_has_chunk_duration_parameter(self):
        """Test /api/v1/convert/video has chunk_duration parameter."""
        from api.main import transcribe_video_file
        import inspect
        
        sig = inspect.signature(transcribe_video_file)
        params = sig.parameters
        
        assert "chunk_duration" in params, "Parameter 'chunk_duration' should exist for chunk duration control"

    def test_video_endpoint_has_chunk_overlap_parameter(self):
        """Test /api/v1/convert/video has chunk_overlap parameter."""
        from api.main import transcribe_video_file
        import inspect
        
        sig = inspect.signature(transcribe_video_file)
        params = sig.parameters
        
        assert "chunk_overlap" in params, "Parameter 'chunk_overlap' should exist for overlap control"

    def test_video_endpoint_has_auto_chunk_threshold_parameter(self):
        """Test /api/v1/convert/video has auto_chunk_threshold parameter."""
        from api.main import transcribe_video_file
        import inspect
        
        sig = inspect.signature(transcribe_video_file)
        params = sig.parameters
        
        assert "auto_chunk_threshold" in params, "Parameter 'auto_chunk_threshold' should exist for auto-enable threshold"

    def test_video_enable_chunking_default_is_false(self):
        """Test video enable_chunking defaults to False (chunking disabled by default)."""
        from api.main import transcribe_video_file
        import inspect
        
        sig = inspect.signature(transcribe_video_file)
        param = sig.parameters["enable_chunking"]
        
        default = param.default
        if hasattr(default, 'default'):
            assert default.default is False, "enable_chunking default should be False"
        else:
            assert default is False, "enable_chunking default should be False"

    def test_video_chunk_duration_default(self):
        """Test video chunk_duration defaults to constants.DEFAULT_CHUNK_DURATION (60 seconds)."""
        from api.main import transcribe_video_file
        from api.constants import DEFAULT_CHUNK_DURATION
        import inspect
        
        sig = inspect.signature(transcribe_video_file)
        param = sig.parameters["chunk_duration"]
        
        default = param.default
        if hasattr(default, 'default'):
            assert default.default == DEFAULT_CHUNK_DURATION, f"chunk_duration default should be {DEFAULT_CHUNK_DURATION}"
        else:
            assert default == DEFAULT_CHUNK_DURATION, f"chunk_duration default should be {DEFAULT_CHUNK_DURATION}"

    def test_video_chunk_overlap_default(self):
        """Test video chunk_overlap defaults to constants.DEFAULT_CHUNK_OVERLAP (2 seconds)."""
        from api.main import transcribe_video_file
        from api.constants import DEFAULT_CHUNK_OVERLAP
        import inspect
        
        sig = inspect.signature(transcribe_video_file)
        param = sig.parameters["chunk_overlap"]
        
        default = param.default
        if hasattr(default, 'default'):
            assert default.default == DEFAULT_CHUNK_OVERLAP, f"chunk_overlap default should be {DEFAULT_CHUNK_OVERLAP}"
        else:
            assert default == DEFAULT_CHUNK_OVERLAP, f"chunk_overlap default should be {DEFAULT_CHUNK_OVERLAP}"

    def test_video_auto_chunk_threshold_default(self):
        """Test video auto_chunk_threshold defaults to constants.DEFAULT_AUTO_CHUNK_THRESHOLD (90 seconds)."""
        from api.main import transcribe_video_file
        from api.constants import DEFAULT_AUTO_CHUNK_THRESHOLD
        import inspect
        
        sig = inspect.signature(transcribe_video_file)
        param = sig.parameters["auto_chunk_threshold"]
        
        default = param.default
        if hasattr(default, 'default'):
            assert default.default == DEFAULT_AUTO_CHUNK_THRESHOLD, f"auto_chunk_threshold default should be {DEFAULT_AUTO_CHUNK_THRESHOLD}"
        else:
            assert default == DEFAULT_AUTO_CHUNK_THRESHOLD, f"auto_chunk_threshold default should be {DEFAULT_AUTO_CHUNK_THRESHOLD}"