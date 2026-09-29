import numpy as np
import pymupdf
from rapidocr_onnxruntime import RapidOCR


ocr_engine = RapidOCR()


def ocr_pdf_page(page) -> str:
    """Convert a PDF page to an image and extract text using OCR."""

    pixmap = page.get_pixmap(
        matrix=pymupdf.Matrix(2, 2),
        alpha=False
    )

    image = np.frombuffer(
        pixmap.samples,
        dtype=np.uint8
    )

    image = image.reshape(
        pixmap.height,
        pixmap.width,
        pixmap.n
    )

    result, _ = ocr_engine(image)

    if result is None:
        return ""

    texts = []

    for item in result:
        if len(item) >= 2:
            texts.append(str(item[1]))

    return "\n".join(texts)