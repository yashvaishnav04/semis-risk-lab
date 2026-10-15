import io
import zipfile
from datetime import date

import requests
import yfinance as yf

TICKERS = ["NVDA", "AMD", "AVGO", "QCOM", "INTC", "MU", "TSM", "ASML", "SNPS", "CDNS"]
BENCHMARKS = ["SOXX", "SPY"]
START_DATE = "2016-01-01"
FACTORS_URL = (
    "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
    "F-F_Research_Data_Factors_daily_CSV.zip"
)


def extract_prices():
    # auto_adjust=True so prices are already adjusted for splits and dividends
    # Always download the full history, because adjusted prices get restated over time
    return yf.download(
        TICKERS + BENCHMARKS,
        start=START_DATE,
        end=date.today().isoformat(),
        auto_adjust=True,
    )


def extract_factors():
    # timeout so the pipeline fails instead of hanging if the site stops responding
    response = requests.get(FACTORS_URL, timeout=30)
    # Stop here with a clear error if the download failed, instead of parsing junk later
    response.raise_for_status()

    # The download is a zip file, so open it in memory and read the one CSV inside
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        csv_name = zf.namelist()[0]
        # Return the text as is; cleaning belongs in the transform stage
        return zf.read(csv_name).decode("utf-8")


def main():
    prices = extract_prices()
    factors_text = extract_factors()

    print("Prices shape:", prices.shape)
    print("Factors text (first 300 characters):")
    print(factors_text[:300])


if __name__ == "__main__":
    main()
