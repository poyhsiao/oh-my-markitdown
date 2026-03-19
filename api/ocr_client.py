"""OCR client module using pytesseract SDK.

Provides OCR functionality for images and PDFs with multi-language support.
"""

import os
import tempfile
from typing import Optional

import pytesseract
from PIL import Image

from api.constants import OCR_LANGUAGES, DEFAULT_OCR_LANG


class OCRError(Exception):
    """OCR processing failed."""
    pass


class UnsupportedLanguageError(OCRError):
    """OCR language not supported."""
    pass


def validate_ocr_languages(ocr_lang: str) -> None:
    """Validate OCR language parameter.

    Args:
        ocr_lang: Language string (e.g., "chi_tra+eng")

    Raises:
        UnsupportedLanguageError: Contains unsupported language
    """
    langs = ocr_lang.split("+")
    invalid_langs = [lang for lang in langs if lang not in OCR_LANGUAGES]

    if invalid_langs:
        raise UnsupportedLanguageError(
            f"Unsupported OCR language(s): {', '.join(invalid_langs)}. "
            f"Supported: {', '.join(sorted(OCR_LANGUAGES))}"
        )


def ocr_image(
    image_path: str,
    ocr_lang: str = DEFAULT_OCR_LANG,
) -> str:
    """Perform OCR on an image file.

    Args:
        image_path: Image file path
        ocr_lang: OCR language (e.g., "chi_tra+eng")

    Returns:
        OCR recognized text

    Raises:
        OCRError: OCR processing failed
        FileNotFoundError: Image file not found
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")

    validate_ocr_languages(ocr_lang)

    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image, lang=ocr_lang)
        return text.strip()

    except pytesseract.TesseractError as e:
        raise OCRError(f"OCR processing failed: {e}") from e
    except Exception as e:
        raise OCRError(f"OCR processing failed: {e}") from e


def ocr_image_object(
    image: Image.Image,
    ocr_lang: str = DEFAULT_OCR_LANG,
) -> str:
    """Perform OCR on a PIL Image object.

    Args:
        image: PIL Image object
        ocr_lang: OCR language

    Returns:
        OCR recognized text

    Raises:
        OCRError: OCR processing failed
    """
    validate_ocr_languages(ocr_lang)

    try:
        text = pytesseract.image_to_string(image, lang=ocr_lang)
        return text.strip()

    except pytesseract.TesseractError as e:
        raise OCRError(f"OCR processing failed: {e}") from e
    except Exception as e:
        raise OCRError(f"OCR processing failed: {e}") from e


def ocr_pdf(
    pdf_path: str,
    ocr_lang: str = DEFAULT_OCR_LANG,
    *,
    zoom: float = 3.0,
    min_text_length: int = 50,
) -> str:
    """Perform OCR on a PDF file (for scanned PDFs).

    Detects if PDF is scanned (no extractable text) and performs OCR
    on rendered page images.

    Args:
        pdf_path: PDF file path
        ocr_lang: OCR language
        zoom: Render zoom factor (default: 3x for better OCR accuracy)
        min_text_length: Minimum text length threshold to consider page as scanned

    Returns:
        OCR recognized text (pages separated by newlines)

    Raises:
        OCRError: OCR processing failed
        FileNotFoundError: PDF file not found
    """
    import fitz

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    validate_ocr_languages(ocr_lang)

    try:
        doc = fitz.open(pdf_path)
        ocr_results = []

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)

            text = page.get_text()

            if len(text.strip()) >= min_text_length:
                ocr_results.append(text.strip())
            else:
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)

                temp_img = tempfile.mktemp(suffix=".png")
                pix.save(temp_img)

                try:
                    page_text = ocr_image(temp_img, ocr_lang)
                    ocr_results.append(page_text)
                finally:
                    if os.path.exists(temp_img):
                        os.unlink(temp_img)

        doc.close()
        return "\n\n".join(ocr_results)

    except fitz.FileDataError as e:
        raise OCRError(f"Failed to open PDF: {e}") from e
    except Exception as e:
        raise OCRError(f"PDF OCR processing failed: {e}") from e


def ocr_pdf_pages(
    pdf_path: str,
    ocr_lang: str = DEFAULT_OCR_LANG,
    *,
    zoom: float = 3.0,
) -> list[dict]:
    """Perform OCR on each page of a PDF file.

    Args:
        pdf_path: PDF file path
        ocr_lang: OCR language
        zoom: Render zoom factor

    Returns:
        List of dicts with page number and OCR text
    """
    import fitz

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    validate_ocr_languages(ocr_lang)

    try:
        doc = fitz.open(pdf_path)
        results = []

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)

            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)

            temp_img = tempfile.mktemp(suffix=".png")
            pix.save(temp_img)

            try:
                page_text = ocr_image(temp_img, ocr_lang)
                results.append({
                    "page": page_num + 1,
                    "text": page_text,
                })
            finally:
                if os.path.exists(temp_img):
                    os.unlink(temp_img)

        doc.close()
        return results

    except Exception as e:
        raise OCRError(f"PDF page OCR failed: {e}") from e


def get_tesseract_languages() -> list[str]:
    """Get list of installed Tesseract language packs.

    Returns:
        Sorted list of installed language codes
    """
    try:
        langs = pytesseract.get_languages()
        return sorted(langs)
    except Exception:
        return []


def is_tesseract_available() -> bool:
    """Check if Tesseract is available.

    Returns:
        True if Tesseract is correctly installed
    """
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False