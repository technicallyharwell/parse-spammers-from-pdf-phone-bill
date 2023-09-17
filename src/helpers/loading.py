from src.helpers.extracting import CallDataExtractor


class CallDataLoader:
    def __init__(self, **kwargs):
        self.extractor: CallDataExtractor = kwargs.get('extractor', None)
        self.white_listed_numbers = kwargs.get('white_listed_numbers', None)
        self.keep_columns = ['Date', 'Time', 'Number']

        if self.extractor is None:
            raise RuntimeError("CallDataLoader requires a CallDataExtractor")

    def export(self):
        # filter out calls with duration > 1 minute
        self._filter_out_long_calls()
        # filter out calls with numbers in whitelist
        self._filter_whitelisted_numbers()
        # filter out undesired columns
        self._filter_out_undesired_columns()
        # export to csv
        # print(self.extractor.result_df.to_string())
        self._export_to_csv()

    def _filter_out_long_calls(self):
        self.extractor.result_df = self.extractor.result_df[
            self.extractor.result_df['Min.'] == 1
        ]

    def _filter_whitelisted_numbers(self):
        if self.white_listed_numbers is None:
            return
        self.extractor.result_df = self.extractor.result_df[
            ~self.extractor.result_df['Number'].isin(self.white_listed_numbers)
        ]

    def _filter_out_undesired_columns(self):
        self.extractor.result_df = self.extractor.result_df[self.keep_columns]

    def _export_to_csv(self):
        csv_filename = 'output/' + self.extractor.scanner.pdf_path.split('/')[-1].split('.')[0]
        csv_filename += '_' + self.extractor.scanner.search_number.replace('.', '_') + '.csv'
        self.extractor.result_df.to_csv(csv_filename, index=False)
