import numpy as np

from tabula import read_pdf


class DocumentScanner:
    """
    DocumentScanner is responsible for scanning the PDF page by page
    and providing configuration read from env vars which is consumed
    later via composition
    """

    def __init__(self, **kwargs):
        """
        DocumentScanner primarily is used to find the start and end pages
        of call data for a given search_number. If start/end pages are not
        found, a RuntimeError is raised.
        Args:
            **kwargs:
        """
        # pass these required args from env vars
        try:
            self.pdf_path: str = kwargs.get('pdf_path')
            self.search_number: str = kwargs.get('search_number')
            self.search_key: str = kwargs.get('search_string')
            self.section_header_rows: int = int(kwargs.get('section_header_rows'))
        except Exception as e:
            raise RuntimeError(f"Unable to instantiate DocumentScanner\n"
                               f"\tPlease check your .env file\n"
                               f"\tAnd the instantiation of this class.\n"
                               f"\texception raised was: \n\t\t{e}")

        # will default if not specified
        self.max_pages: int = int(kwargs.get('max_pages', 100))
        self.rows_between_sections: int = int(kwargs.get('rows_between_sections', 5))

        # these properties are set and consumed during runtime
        self.start_page_key_index: int | None = None
        self.start_page: int | None = None
        self.end_page: int | None = None
        # end_page_key_index can be used for optimization on multi-record pages
        self.end_page_key_index: int | None = None
        self.valid_pages: list = list()

        # validate that the required args are present
        self.__validate_constructor_args()

    def find_start_page(self):
        """
        find_start_page is responsible for finding the page number
        where the search_number call data begins. After calling this
        method, start_page property will be set, or be None if no
        start page was found.

        Returns:
            None
        """
        for curr_page in range(1, self.max_pages):
            df = read_pdf(self.pdf_path, pages=curr_page, guess=False)
            key_indices = self._find_key_indices_in_df(df)
            if len(key_indices) > 0:
                for k in key_indices:
                    df_slice = self._slice_header_around_key_index(df, k)
                    if self._is_search_number_in_slice(df_slice):
                        self.start_page_key_index = k
                        self.start_page = curr_page
                        self.valid_pages.append(curr_page)
                        return

        # if start page is not found, raise an error
        if self.start_page is None:
            raise RuntimeError("Unable to identify the start page")

    def find_end_page(self):
        """
        Basically this method will walk all pages until max_pages,
        looking for the search_key and validating if the search_number
        is still within the slice. If search_key is not found on the page,
        it is assumed that all call data has been walked.

        The end_page_key_index is captured as a property for optimization
        purposes when extracting call data from multi-record pages.
        Returns:

        """
        for curr_page in range(self.start_page, self.max_pages):
            if curr_page not in self.valid_pages:
                self.valid_pages.append(curr_page)
            df = read_pdf(self.pdf_path, pages=curr_page, guess=False)
            key_indices = self._find_key_indices_in_df(df)
            if len(key_indices) > 0:
                # edge case where all call data is on one page
                if curr_page == self.start_page:
                    for i in range(len(key_indices)):
                        df_slice = self._slice_header_around_key_index(df, key_indices[i])
                        if (self._is_search_number_in_slice(df_slice) and
                                i < len(key_indices) - 1):
                            self.end_page = curr_page
                            self.end_page_key_index = key_indices[i+1] - self.rows_between_sections
                            return
                else:
                    for k in key_indices:
                        df_slice = self._slice_header_around_key_index(df, k)
                        if not self._is_search_number_in_slice(df_slice):
                            self.end_page = curr_page
                            self.end_page_key_index = k - self.rows_between_sections
                            return
            else:
                # edge case of last number, seen all call data
                self.valid_pages.remove(curr_page)
                self.end_page = curr_page - 1
                self.end_page_key_index = int(11/0.18)      # 11 inches / 0.18 inches per row
                return

        # if end page is not found, raise an error
        if self.end_page is None:
            raise RuntimeError("Unable to identify the end page")

    def _is_search_number_in_slice(self, df_slice):
        return df_slice.iloc[:, 0].str.match(self.search_number).any()

    def _slice_header_around_key_index(self, df, key_index):
        """
        Slice the section_header_rows before the key_index
        from the dataframe. Used to validate if the call data
        section belongs to the search_number
        Args:
            df: dataframe of a single PDF page
            key_index: row index where search_key was found

        Returns:
            dataframe slice of section_header_rows before key_index
        """
        return df[0][key_index - self.section_header_rows:key_index + 1]

    def _find_key_indices_in_df(self, df) -> list:
        """
        Find the row indices of search_key in the dataframe
        Args:
            df: a dataframe of a single PDF page

        Returns:
            list of row indices where search_key is found, else empty list
        """
        search_key_indices: list = list(np.where(df[0].iloc[:, 0].str.contains(
            self.search_key, na=False))[0])
        return search_key_indices

    def __validate_constructor_args(self):
        required_keys_not_none = [
            self.pdf_path,
            self.search_number,
            self.search_key,
            self.section_header_rows,
            self.max_pages
        ]
        for k in required_keys_not_none:
            if k is None:
                raise ValueError(f"Required constructor arg {k} is None\n"
                                 f"\tPlease check your .env file\n"
                                 f"\tAnd the instantiation of this class.")
