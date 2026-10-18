# VanTrack — campervan cleaning & earnings tracker

A phone-friendly Streamlit app that reads 6-digit fleet stickers from images, logs campervan cleans, and splits the A$30 cleaning fee equally among the people who worked on the job.

## Run locally

1. Install Python 3.10+ and Tesseract OCR.
   - Ubuntu: `sudo apt update && sudo apt install tesseract-ocr`
   - macOS (Homebrew): `brew install tesseract`
2. Open a terminal inside `campervan_tracker`.
3. Create a Python virtual environment: `python3 -m venv .venv` and activate it (`source .venv/bin/activate` on macOS/Linux).
4. Install Python packages: `pip install -r requirements.txt`.
5. Start: `streamlit run app.py`.
6. Open the displayed URL. On the same local network you can use the computer's LAN IP from your phone, but browser camera access generally requires HTTPS or localhost. Use **Upload photo** from your phone if the camera widget is blocked.

## Using it

1. Open Scan & Log, take/upload a picture, and press **Detect fleet number**.
2. Verify or manually edit the six-digit result. OCR can be imperfect.
3. Enter the total number of cleaners **including yourself**. 1 person = A$30. 2 people = A$15 each. 3 people = A$10 each.
4. Save the cleaning; see the Dashboard, Vehicles, Earnings, and History pages.
5. In History, mark jobs paid when you receive money, or export CSV.

## Hosting & storage

- `packages.txt` is for environments such as Streamlit Community Cloud that support installing system packages. Your application also requires the Python packages in `requirements.txt`.
- The SQLite file is at `data/campervans.db`. Back it up if running locally.
- **Important:** Streamlit Community Cloud's local filesystem is not durable across restarts/redeployments. Do not treat its SQLite file as permanent storage. For production, move data to a persistent hosted PostgreSQL database (e.g. Supabase) and add authentication.
- The app does not permanently store submitted images; it saves the fleet number and job information.
- No login is included in this local MVP. Don't expose it publicly without adding access control.

## Notes

- One vehicle row per fleet number; multiple cleaning jobs can reference it.
- Share amounts are stored as whole cents (half-up rounding), and may not sum to exactly the total for awkward splits, such as A$30 ÷ 7. For 1, 2, 3, 4, 5, 6 etc. where the division is exact, this doesn't matter.
- A cleaning job can be deleted from History if entered in error.
