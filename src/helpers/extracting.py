import numpy as np
import pandas as pd

from tabula import read_pdf
from src.helpers.scanning import DocumentScanner


class CallDataExtractor:
    def __init__(self, **kwargs):
        """
        CallDataExtractor is responsible for extracting the tables of
        call data from each valid PDF page and concatenating them to a
        single dataframe. The dataframe is stored in the result_df property.
        Args:
            **kwargs:
        """
        self.scanner: DocumentScanner = kwargs.get('document_scanner', None)
        # result_df is progressively generated as pages are iterated
        self.result_df = None
        self.df_accumulator = list()
        self.gradient_adjustment = 0.01

        if self.scanner is None:
            raise RuntimeError("CallDataExtractor requires a DocumentScanner")

    def extract(self):
        """
        extract is the main method of this class, and has branching logic
        to handle cases for the first page, last page, and middle pages.

        RuntimeError raised if any condition which prevents a df from being
        created is encountered.
        Returns:

        """
        for page in self.scanner.valid_pages:
            if page == self.scanner.start_page:
                # first pages can be hairy depending on position where data begins
                if self.scanner.start_page_key_index == 3:  # call data exists in first section
                    self.df_accumulator.append(self._simple_extract(page))
                else:
                    self.df_accumulator.append(self._complex_extract(page))
            elif page == self.scanner.end_page:
                # call data on last pages should be the first section on the page
                try:
                    df = self._last_page_extract(page)
                    self.df_accumulator.append(df)
                except ValueError:
                    raise RuntimeError(f"Unable to extract call data from last page {page}\n"
                                       f"Please raise an issue on GitHub with the following data:\n"
                                       f"\tstart_page: {self.scanner.start_page}\n"
                                       f"\tend_page: {self.scanner.end_page}\n"
                                       f"\tstart_page_key_index: {self.scanner.start_page_key_index}\n"
                                       f"\tend_page_key_index: {self.scanner.end_page_key_index}\n"
                                       f"\tvalid_pages: {self.scanner.valid_pages}\n")
            else:
                # middle pages are the easiest to extract -> first section on the page
                df = self._simple_extract(page)
                self.df_accumulator.append(df)

        if len(self.df_accumulator) == 0:
            raise RuntimeError(f"Did not accumulate any dataframes during extraction\n")
        self.result_df = pd.concat(self.df_accumulator, ignore_index=True)
        self.result_df = self.result_df.dropna(thresh=6)

    def _simple_extract(self, page):
        """
        Utilizes the guess arg to try automatic parsing
        Args:
            page:

        Returns:

        """
        df = read_pdf(self.scanner.pdf_path, pages=page, guess=True)
        if all(item in list(df[0].columns) for item in ["Date", "Time", "Number"]):
            return df[0]
        else:
            raise ValueError(f"Unable to extract call data from page {page}")

    def _last_page_extract(self, page):
        """
        For extracting the last page, first a simple extract is attempted.
        If simple extract fails, the top/bottom window to search is
        approximated before trying an area extract.
        Args:
            page:

        Returns:

        """
        try:
            return self._simple_extract(page)
        except ValueError:
            area_args = self.__calculate_area_float_list(0.0)
            # the 3.0 is a magic number compensating for the header of new pages
            approx_bottom = float((3.0 + (self.scanner.end_page_key_index * 0.18)) * 72)
            area_args[0] = float(3.0 * 72)
            area_args[2] = min(approx_bottom, 792.0)
            df = read_pdf(self.scanner.pdf_path, pages=page, area=area_args)
            if all(item in list(df[0].columns) for item in ["Date", "Time", "Number"]):
                return df[0]
            else:
                raise ValueError(f"Unable to extract call data from page {page}")

    def _complex_extract(self, page):
        """
        Inspired by gradient descent algorithm, this method will guess where
        the call data exists for pages with multiple sections. The guess is
        based on the ratio of the start_key_index and the total_rows, and
        updated by gradient_adjustment by checking the search_key indices.

        Extra logic is implemented to handle the edge case where only small
        amounts of call data exist for the search_number, e.g. start == end.
        In this case, a bottom limit needs to be applied to the area arg.
        Args:
            page:

        Returns:

        """
        init_df = read_pdf(self.scanner.pdf_path, pages=page, guess=False)
        total_rows = init_df[0].shape[0]
        call_data_indices = list(np.where(init_df[0].iloc[:, 0].str.contains('Date Time Number', na=False))[0])
        possible_indices = [i for i in call_data_indices if i >= self.scanner.start_page_key_index]
        vert_slider = float(self.scanner.start_page_key_index / total_rows)
        area_args = self.__calculate_area_float_list(vert_slider)

        df = read_pdf(self.scanner.pdf_path, pages=page, area=area_args)
        if all(item in list(df[0].columns) for item in ["Date", "Time", "Number"]):
            return df[0]

        # first guess was wrong, so we need to adjust the area
        # this loop could become infinite, so we set a max number of iterations
        max_iterations = 500
        curr_iter = 0
        while curr_iter < max_iterations:
            new_indices = list(np.where(df[0].iloc[:, 0].str.contains('Date', na=False))[0])
            if len(new_indices) < len(possible_indices):
                # guess went too far, need to -- vertical_slider
                vert_slider -= self.gradient_adjustment
            else:
                # guess didn't go far enough, need to ++ vertical_slider
                vert_slider += self.gradient_adjustment
            area_args = self.__calculate_area_float_list(vert_slider)
            df = read_pdf(self.scanner.pdf_path, pages=page, area=area_args)
            if any(item in list(df[0].columns) for item in ["Date", "Time", "Number"]):
                # top of call data found, edge case exists where another data section exists below
                if df[0]["Number"].isnull().any() and self.scanner.start_page == self.scanner.end_page:
                    # take the diff b/t start key index and end key index to approx rows between sections
                    row_diff = self.scanner.end_page_key_index - self.scanner.start_page_key_index
                    # each row is ~0.18 inch tall, the bottom argument is area_args[2]
                    bottom_differential = row_diff * 0.18 * 72 + 0.50 * 72    # add extra 1/2 inch
                    bottom = min(area_args[0] + bottom_differential, 792.0)  # 792 is the max height of a letter
                    area_args[2] = bottom
                    df = read_pdf(self.scanner.pdf_path, pages=page, area=area_args)
                    if all(item in list(df[0].columns) for item in ["Date", "Time", "Number"]):
                        return df[0]

                else:
                    df[0] = df[0].dropna(thresh=3)
                    return df[0]
            curr_iter += 1

        if max_iterations == curr_iter:
            raise RuntimeError(f"Hit max_iterations limit within _complex_extract() for page {page}\n"
                               f"Please raise an issue on GitHub with the following data:\n"
                               f"\tstart_page: {self.scanner.start_page}\n"
                               f"\tend_page: {self.scanner.end_page}\n"
                               f"\tstart_page_key_index: {self.scanner.start_page_key_index}\n"
                               f"\tend_page_key_index: {self.scanner.end_page_key_index}\n"
                               f"\tvalid_pages: {self.scanner.valid_pages}\n"
                               f"\ttotal_rows: {total_rows}\n"
                               f"\tpossible_indices: {possible_indices}\n"
                               f"\tnew_indices: {new_indices}\n")

    @staticmethod
    def __calculate_area_float_list(vertical_slider: float):
        """
        A standard letter has dimensions 8.5"x11" and the PDF spec
        measures in points, where 1 point = 1/72 inch. So a standard
        letter is (72*8.5) x (72*11) ; vertical_slider drives how
        much of the page is included in the area calculation.

        The area= arg of read_pdf expects a list of floats representing
        top, left, bottom, right
        Args:
            vertical_slider:

        Returns:

        """
        return [float(vertical_slider * 11 * 72),
                0.0,
                11.0 * 72,
                8.5 * 72]
