import os

from dotenv import load_dotenv

from src.helpers.scanning import DocumentScanner
from src.helpers.extracting import CallDataExtractor
from src.helpers.loading import CallDataLoader

load_dotenv()

WHITELISTED_NUMBERS = list(os.getenv("WHITELISTED_NUMBERS").split(",")) or None

if __name__ == "__main__":
    # Establish the search space
    scanner = DocumentScanner(
        pdf_path=os.getenv("PDF_PATH"),
        search_number=os.getenv("SEARCH_NUMBER"),
        search_string=os.getenv("SEARCH_KEY"),
        max_pages=os.getenv("MAX_SEARCH_PAGES", 100),
        section_header_rows=os.getenv("SECTION_HEADER_ROWS")
    )
    scanner.find_start_page()
    scanner.find_end_page()
    # print(scanner.valid_pages)

    # Extract the call data
    extractor = CallDataExtractor(
        document_scanner=scanner
    )
    extractor.extract()
    # print(extractor.result_df.to_string())

    # Load and export the call data
    loader = CallDataLoader(
        extractor=extractor,
        white_listed_numbers=WHITELISTED_NUMBERS
    )
    loader.export()
