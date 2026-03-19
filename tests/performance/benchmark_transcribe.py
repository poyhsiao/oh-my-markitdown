"""Performance benchmark tests for Whisper transcription."""

import pytest
import time
import os
from typing import Tuple

# Skip all tests if running in CI without audio files
pytestmark = pytest.mark.skipif(
    os.getenv("SKIP_PERFORMANCE_TESTS", "true").lower() == "true",
    reason="Performance tests disabled by default. Set SKIP_PERFORMANCE_TESTS=false to enable."
)


def calculate_wer(reference: str, hypothesis: str) -> float:
    """
    Calculate Word Error Rate (WER) between reference and hypothesis.
    
    Args:
        reference: Ground truth transcription
        hypothesis: Transcription to evaluate
        
    Returns:
        WER value (0.0 = perfect, 1.0 = completely wrong)
    """
    reference_words = reference.lower().split()
    hypothesis_words = hypothesis.lower().split()
    
    if not reference_words:
        return 0.0 if not hypothesis_words else 1.0
    
    # Simple Levenshtein distance
    d = [[0] * (len(hypothesis_words) + 1) for _ in range(len(reference_words) + 1)]
    
    for i in range(len(reference_words) + 1):
        d[i][0] = i
    for j in range(len(hypothesis_words) + 1):
        d[0][j] = j
    
    for i in range(1, len(reference_words) + 1):
        for j in range(1, len(hypothesis_words) + 1):
            if reference_words[i-1] == hypothesis_words[j-1]:
                d[i][j] = d[i-1][j-1]
            else:
                d[i][j] = min(
                    d[i-1][j] + 1,      # deletion
                    d[i][j-1] + 1,      # insertion
                    d[i-1][j-1] + 1     # substitution
                )
    
    return d[len(reference_words)][len(hypothesis_words)] / len(reference_words)


class TestTranscribeBenchmark:
    """Transcription performance benchmark tests."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures."""
        self.results = {}
        self.baseline_results = {
            "cpu_1min": {"max_ratio": 3.0},      # CPU: < 3x duration
            "cuda_1min": {"max_ratio": 1.0},     # CUDA: < 1x duration
            "mps_1min": {"max_ratio": 2.0},      # MPS: < 2x duration
        }
    
    @pytest.fixture
    def sample_audio_1min(self, tmp_path):
        """Generate or load a 1-minute sample audio file."""
        # This fixture should be replaced with actual test audio
        # For now, skip if no test audio available
        audio_path = os.path.join("tests", "fixtures", "sample_1min.wav")
        if not os.path.exists(audio_path):
            pytest.skip("Sample audio file not found")
        return audio_path
    
    def test_benchmark_cpu_1min(self, sample_audio_1min):
        """1 minute audio - CPU baseline benchmark."""
        from api.whisper_transcribe import transcribe_audio
        
        start = time.time()
        result, segments = transcribe_audio(
            sample_audio_1min,
            language="auto",
            model_size="base",
            device="cpu",
            compute_type="int8",
            cpu_threads=4
        )
        elapsed = time.time() - start
        
        # Duration is 60 seconds (1 minute)
        duration = 60
        ratio = elapsed / duration
        
        self.results["cpu_1min"] = {
            "elapsed": elapsed,
            "ratio": ratio,
            "text_length": len(result),
            "segments_count": len(segments)
        }
        
        # Assert: processing time should be < 3x audio duration
        assert elapsed < 180, f"CPU 1min took {elapsed}s (expected < 180s)"
        assert ratio < 3.0, f"CPU processing ratio {ratio:.2f}x (expected < 3.0x)"
        assert len(result) > 0, "Transcription should not be empty"
    
    def test_benchmark_cuda_1min(self, sample_audio_1min):
        """1 minute audio - CUDA benchmark."""
        import torch
        
        if not torch.cuda.is_available():
            pytest.skip("CUDA not available")
        
        from api.whisper_transcribe import transcribe_audio
        
        start = time.time()
        result, segments = transcribe_audio(
            sample_audio_1min,
            language="auto",
            model_size="base",
            device="cuda",
            compute_type="float16"
        )
        elapsed = time.time() - start
        
        duration = 60
        ratio = elapsed / duration
        
        self.results["cuda_1min"] = {
            "elapsed": elapsed,
            "ratio": ratio,
            "text_length": len(result),
            "segments_count": len(segments)
        }
        
        # Assert: CUDA processing should be < 1x audio duration
        assert elapsed < 60, f"CUDA 1min took {elapsed}s (expected < 60s)"
        assert ratio < 1.0, f"CUDA processing ratio {ratio:.2f}x (expected < 1.0x)"
    
    def test_benchmark_mps_1min(self, sample_audio_1min):
        """1 minute audio - MPS (Apple Silicon) benchmark."""
        import torch
        
        if not (hasattr(torch.backends, 'mps') and torch.backends.mps.is_available()):
            pytest.skip("MPS not available")
        
        from api.whisper_transcribe import transcribe_audio
        
        start = time.time()
        result, segments = transcribe_audio(
            sample_audio_1min,
            language="auto",
            model_size="base",
            device="mps",
            compute_type="float16"
        )
        elapsed = time.time() - start
        
        duration = 60
        ratio = elapsed / duration
        
        self.results["mps_1min"] = {
            "elapsed": elapsed,
            "ratio": ratio,
            "text_length": len(result),
            "segments_count": len(segments)
        }
        
        # Assert: MPS processing should be < 2x audio duration
        assert elapsed < 120, f"MPS 1min took {elapsed}s (expected < 120s)"
        assert ratio < 2.0, f"MPS processing ratio {ratio:.2f}x (expected < 2.0x)"
    
    def test_quality_cpu_vs_cuda(self, sample_audio_1min):
        """Compare transcription quality between CPU and CUDA."""
        import torch
        
        if not torch.cuda.is_available():
            pytest.skip("CUDA not available")
        
        from api.whisper_transcribe import transcribe_audio
        
        # CPU transcription
        cpu_result, _ = transcribe_audio(
            sample_audio_1min,
            language="auto",
            model_size="base",
            device="cpu",
            compute_type="int8"
        )
        
        # CUDA transcription
        cuda_result, _ = transcribe_audio(
            sample_audio_1min,
            language="auto",
            model_size="base",
            device="cuda",
            compute_type="float16"
        )
        
        # Calculate WER between CPU and CUDA results
        wer = calculate_wer(cpu_result, cuda_result)
        
        # Assert: WER should be < 5% (quality degradation should be minimal)
        assert wer < 0.05, f"WER between CPU and CUDA: {wer:.2%} (expected < 5%)"


class TestModelSelectionBenchmark:
    """Model selection performance tests."""
    
    def test_model_selection_tiny_vs_base(self, sample_audio_1min):
        """Compare processing time between tiny and base models."""
        pytest.skip("Requires sample audio file")
        
        from api.whisper_transcribe import transcribe_audio
        
        # Tiny model
        start = time.time()
        tiny_result, _ = transcribe_audio(
            sample_audio_1min,
            model_size="tiny",
            device="cpu"
        )
        tiny_time = time.time() - start
        
        # Base model
        start = time.time()
        base_result, _ = transcribe_audio(
            sample_audio_1min,
            model_size="base",
            device="cpu"
        )
        base_time = time.time() - start
        
        # Tiny should be faster
        assert tiny_time < base_time, "Tiny model should be faster than base"
        
        # But base might be more accurate (longer text)
        # This depends on the audio content


class TestVADBenchmark:
    """VAD parameter optimization tests."""
    
    def test_vad_optimized_vs_default(self, sample_audio_1min):
        """Compare optimized VAD parameters vs default."""
        pytest.skip("Requires sample audio file")
        
        from api.whisper_transcribe import transcribe_audio
        
        # Default VAD (500ms silence)
        start = time.time()
        default_result, _ = transcribe_audio(
            sample_audio_1min,
            model_size="base",
            vad_enabled=True,
            vad_params={"min_silence_duration_ms": 500}
        )
        default_time = time.time() - start
        
        # Optimized VAD (300ms silence)
        start = time.time()
        optimized_result, _ = transcribe_audio(
            sample_audio_1min,
            model_size="base",
            vad_enabled=True,
            vad_params={"min_silence_duration_ms": 300}
        )
        optimized_time = time.time() - start
        
        # Optimized should be faster (10-20% improvement expected)
        improvement = (default_time - optimized_time) / default_time
        
        # Log results
        print(f"\nVAD Optimization:")
        print(f"  Default: {default_time:.2f}s")
        print(f"  Optimized: {optimized_time:.2f}s")
        print(f"  Improvement: {improvement:.1%}")
        
        # Quality should not degrade significantly
        wer = calculate_wer(default_result, optimized_result)
        assert wer < 0.05, f"VAD optimization caused {wer:.1%} WER (expected < 5%)"


# Utility function to generate benchmark report
def generate_benchmark_report(results: dict) -> str:
    """Generate a benchmark report from test results."""
    report = ["# Transcription Benchmark Report", ""]
    
    for test_name, data in results.items():
        report.append(f"## {test_name}")
        report.append(f"- Elapsed: {data.get('elapsed', 'N/A'):.2f}s")
        report.append(f"- Ratio: {data.get('ratio', 'N/A'):.2f}x")
        report.append(f"- Text length: {data.get('text_length', 'N/A')}")
        report.append(f"- Segments: {data.get('segments_count', 'N/A')}")
        report.append("")
    
    return "\n".join(report)