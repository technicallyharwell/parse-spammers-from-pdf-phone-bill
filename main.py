import os

from dotenv import load_dotenv

from src.helpers.scanning import DocumentScanner
from src.helpers.extracting import CallDataExtractor
from src.helpers.loading import CallDataLoader
from src.helpers.integrating import ExternalIntegrator

load_dotenv()

WHITELISTED_NUMBERS = list(os.getenv("WHITELISTED_NUMBERS").split(","))

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

    # Integrate the call data with carrier information
    integrator = ExternalIntegrator(
        api_key=os.getenv("NUMVERIFY_API_TOKEN"),
        nums=loader.extractor.result_df['Number'].tolist()
    )
    integrator.find_carriers()
    loader.export_carriers(carrier_list=integrator.df_num_accumulator)
