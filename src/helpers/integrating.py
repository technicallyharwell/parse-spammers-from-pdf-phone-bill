import requests
import time


class ExternalIntegrator:
    def __init__(self, **kwargs):
        self.api_key: str | None = kwargs.get('api_key', None)
        self.list_of_nums: list = kwargs.get('nums', None)

        self.list_of_nums = [num.replace(".", "") for num in self.list_of_nums]
        self.list_of_nums = [num.replace("-", "") for num in self.list_of_nums]

        self.api_url: str = 'http://apilayer.net/api/validate?access_key=' + self.api_key + '&number=1'
        self.max_fails_threshold: int = 3
        self.total_fails: int = 0
        self.max_retry_threshold: int = 5
        self.retry_backoff_factor: int = 2
        self.rate_limit_wait_time_seconds: int = 1
        self.df_num_accumulator = list()

    def find_carriers(self) -> None:
        """
        The public interface for finding the carrier for a given phone number
        """
        for num in self.list_of_nums:
            self._find_carrier_for_number(num)
            print(f"Found carrier for {num}, sleeping for rate limit...")
            time.sleep(self.rate_limit_wait_time_seconds)

    def _send_get_request(self, number: str) -> requests.Response:
        """
        sends the get request for a single number and returns the API response
        Args:
            number: the phone number to lookup

        Returns:
            the response object from the request
        """
        resp = requests.get(self.api_url + number)
        return resp

    def _find_carrier_for_number(self, num):
        """
        finds the carrier for a given phone number
        Args:
            num: the formatted phone number to find the carrier for

        Returns:

        """
        if self.total_fails >= self.max_fails_threshold:
            raise RuntimeError("Too many external API failures, exiting\n"
                               "Please check your API key and the API status")
        attempts = 0
        while attempts < self.max_retry_threshold:
            resp = self._send_get_request(num)
            carrier = self.__process_response(resp)
            if carrier is None:
                attempts += 1
                print(f"Failed to find carrier for {num}, sleeping and retrying...")
                time.sleep(self.rate_limit_wait_time_seconds * self.retry_backoff_factor ** attempts)
                continue
            else:
                self.df_num_accumulator.append(carrier)
                break
        if attempts == self.max_retry_threshold:
            self.total_fails += 1
            print(f"Failed to find carrier for {num} after {attempts} attempts, skipping...")
            self.df_num_accumulator.append("Null")

    @staticmethod
    def __process_response(resp: requests.Response) -> str | None:
        """
        processes the response from the API
        Args:
            resp: the response object from the API

        Returns:
            the carrier name if found, None otherwise
        """
        if resp.status_code != 200:
            return None
        carrier = resp.json()['carrier']
        if carrier is None or len(carrier) == 0:
            return "Null"
        return carrier
