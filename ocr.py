"""Read 6-digit fleet numbers with Tesseract OCR, using several image variants."""
import re
import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageOps


def extract_fleet_numbers(photo):
    image = ImageOps.exif_transpose(Image.open(photo)).convert('RGB')
    arr = np.array(image)
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    height, width = gray.shape
    # Bound image size to keep processing practical on a hosted Streamlit server.
    scale = min(1.5, 1400 / max(width, height))
    gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC)
    boosted = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    variants = [boosted, cv2.threshold(boosted, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]]
    scores = {}
    for variant in variants:
        for psm in (6, 11):
            try:
                output = pytesseract.image_to_string(variant, config=f'--psm {psm} -c tessedit_char_whitelist=0123456789')
            except pytesseract.TesseractNotFoundError as exc:
                raise RuntimeError('Tesseract OCR is not installed on the server. See README.md.') from exc
            for number in re.findall(r'(?<!\d)\d{6}(?!\d)', output):
                scores[number] = scores.get(number, 0) + 1
    return sorted(scores, key=lambda num: (-scores[num], num))
