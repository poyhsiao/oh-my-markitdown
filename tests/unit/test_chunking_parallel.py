"""Unit tests for parallel chunking."""
import pytest
from unittest.mock import MagicMock, patch, call


class TestParallelChunking:
    @patch("api.chunking.cleanup_chunks")
    @patch("api.chunking.merge_transcription_results")
    @patch("api.chunking.transcribe_chunk")
    @patch("api.chunking.split_audio_into_chunks")
    def test_parallel_processing_calls_transcribe_for_each_chunk(
        self,
        mock_split,
        mock_transcribe_chunk,
        mock_merge,
        mock_cleanup,
    ):
        from api.chunking import transcribe_audio_parallel

        mock_chunk1 = MagicMock(
            chunk_id=0,
            start_time=0,
            end_time=60,
            file_path="/tmp/c1.wav",
            duration=60,
            overlap_with_previous=0,
        )
        mock_chunk2 = MagicMock(
            chunk_id=1,
            start_time=58,
            end_time=120,
            file_path="/tmp/c2.wav",
            duration=62,
            overlap_with_previous=2,
        )
        mock_split.return_value = [mock_chunk1, mock_chunk2]
        mock_transcribe_chunk.return_value = {"text": "test", "segments": [], "offset": 0}
        mock_merge.return_value = {"text": "merged", "segments": []}

        mock_model = MagicMock()

        result = transcribe_audio_parallel(
            audio_path="/tmp/test.wav",
            language="en",
            model=mock_model,
            beam_size=1,
            vad_filter=True,
            temperature=0.0,
            max_workers=2,
        )

        assert mock_transcribe_chunk.call_count == 2
        mock_merge.assert_called_once()
        mock_cleanup.assert_called_once()

    def test_max_workers_capped(self):
        from api.constants import MAX_MAX_WORKERS, MIN_MAX_WORKERS

        assert MAX_MAX_WORKERS >= 4
        assert MIN_MAX_WORKERS >= 1