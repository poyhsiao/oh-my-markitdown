"""Unit tests for ocr_client module."""

import pytest
from unittest.mock import MagicMock, patch
from PIL import Image

from api.ocr_client import (
    ocr_image,
    ocr_image_object,
    ocr_pdf,
    validate_ocr_languages,
    UnsupportedLanguageError,
    OCRError,
)


class TestValidateOcrLanguages:
    """Tests for validate_ocr_languages function."""

    def test_valid_single_language(self):
        validate_ocr_languages("eng")

    def test_valid_multiple_languages(self):
        validate_ocr_languages("chi_tra+eng+jpn")

    def test_invalid_language(self):
        with pytest.raises(UnsupportedLanguageError) as exc_info:
            validate_ocr_languages("invalid_lang")

        assert "invalid_lang" in str(exc_info.value)

    def test_mixed_valid_invalid(self):
        with pytest.raises(UnsupportedLanguageError) as exc_info:
            validate_ocr_languages("eng+invalid_lang")

        assert "invalid_lang" in str(exc_info.value)


class TestOcrImage:
    """Tests for ocr_image function."""

    @patch("api.ocr_client.pytesseract.image_to_string")
    @patch("PIL.Image.open")
    @patch("os.path.exists")
    def test_ocr_success(self, mock_exists, mock_open, mock_ocr, tmp_path):
        mock_exists.return_value = True
        mock_open.return_value = MagicMock()
        mock_ocr.return_value = "Recognized text\n"

        result = ocr_image(str(tmp_path / "test.png"), "chi_tra+eng")

        assert result == "Recognized text"
        mock_ocr.assert_called_once()

    def test_ocr_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            ocr_image("/nonexistent/image.png")

    @patch("api.ocr_client.pytesseract.image_to_string")
    @patch("PIL.Image.open")
    @patch("os.path.exists")
    def test_ocr_tesseract_error(self, mock_exists, mock_open, mock_ocr, tmp_path):
        import pytesseract
        mock_exists.return_value = True
        mock_open.return_value = MagicMock()
        mock_ocr.side_effect = pytesseract.TesseractError(-1, "OCR failed")

        with pytest.raises(OCRError, match="OCR processing failed"):
            ocr_image(str(tmp_path / "test.png"))


class TestOcrImageObject:
    """Tests for ocr_image_object function."""

    @patch("api.ocr_client.pytesseract.image_to_string")
    def test_ocr_pil_image(self, mock_ocr):
        mock_image = MagicMock(spec=Image.Image)
        mock_ocr.return_value = "Test text"

        result = ocr_image_object(mock_image, "eng")

        assert result == "Test text"
        mock_ocr.assert_called_once_with(mock_image, lang="eng")


class TestOcrPdf:
    """Tests for ocr_pdf function."""

    @patch("api.ocr_client.ocr_image")
    @patch("fitz.open")
    @patch("os.path.exists")
    def test_ocr_pdf_with_text(self, mock_exists, mock_fitz_open, mock_ocr):
        mock_exists.return_value = True

        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Existing text in PDF that is longer than 50 characters threshold"
        mock_doc.__len__ = lambda self: 1
        mock_doc.__iter__ = lambda self: iter([mock_page])
        mock_doc.load_page.return_value = mock_page
        mock_doc.close = MagicMock()
        mock_fitz_open.return_value = mock_doc

        result = ocr_pdf("/path/to/document.pdf")

        assert "Existing text in PDF" in result

    @patch("api.ocr_client.ocr_image")
    @patch("fitz.open")
    @patch("tempfile.mktemp")
    @patch("os.path.exists")
    @patch("os.unlink")
    def test_ocr_scanned_pdf(
        self, mock_unlink, mock_exists, mock_mktemp,
        mock_fitz_open, mock_ocr
    ):
        mock_mktemp.return_value = "/tmp/test_page.png"
        mock_exists.return_value = True
        mock_ocr.return_value = "OCR extracted text"

        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = ""
        mock_pixmap = MagicMock()
        mock_page.get_pixmap.return_value = mock_pixmap
        mock_doc.__len__ = lambda self: 1
        mock_doc.__iter__ = lambda self: iter([mock_page])
        mock_doc.load_page.return_value = mock_page
        mock_doc.close = MagicMock()
        mock_fitz_open.return_value = mock_doc

        result = ocr_pdf("/path/to/scanned.pdf")

        assert "OCR extracted text" in result

    def test_ocr_pdf_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            ocr_pdf("/nonexistent/document.pdf")