from datetime import timedelta, datetime

import requests

FREQMODE_TO_BACKEND = {
    1: "AC2",
    2: "AC1",
    8: "AC2",
    13: "AC1",
    14: "AC2",
    17: "AC2",
    19: "AC1",
    21: "AC1",
    22: "AC2",
    23: "AC1",
    24: "AC1",
    25: "AC1",
    29: "AC1",
    102: "AC2",
    113: "AC2",
    119: "AC2",
    121: "AC2",
}


class ScanIDs:
    """Class for generating scanids"""

    FIRST_DAY = '2001-08-04'
    ONE_DAY = timedelta(days=1)

    def __init__(self, odin_api_root):
        self.odin_api_root = odin_api_root

    @staticmethod
    def generate_from_file(filename):
        """Generate scan ids from a file"""
        with open(filename) as inp:
            for line in inp:
                line = line.strip()
                if line:
                    yield int(line)

    def generate_vds(self, freqmode):
        """Generate all scan ids in the vds dataset"""
        backend = FREQMODE_TO_BACKEND[freqmode]
        resp = requests.get(
            self.odin_api_root + (
                '/v4/vds/{backend}/{freqmode}/allscans'.format(
                    backend=backend, freqmode=freqmode)))
        for info in resp.json()['VDS']:
            yield info['Info']['ScanID']

    def generate_all(self, freqmode, start_day=None, end_day=None):
        """Generate all scan ids for a freqmode between two dates,
        but only ids that have ecmf data available.

        Args:
          freqmode (int): The freqmode.
          start_day (str): Start day (%Y-%m-%d), inclusive.
          end_day (str): End day (%Y-%m-%d), exclusive.

        Yields:
          scanid (int): The scan id.
        """
        start_day = datetime.strptime(
            start_day or self.FIRST_DAY, '%Y-%m-%d')
        latest_available = self.get_latest_ecmf_day()
        if not end_day:
            end_day = latest_available
        else:
            end_day = min(end_day, latest_available)
        end_day = datetime.strptime(end_day, '%Y-%m-%d')
        days = self.generate_days_with_scans(start_day, end_day, freqmode)
        for _, url, _ in days:
            for scanid in self.get_scan_ids_from_log(url):
                yield scanid

    @staticmethod
    def get_scan_ids_from_log(url):
        """Return list of scan ids found in url"""
        resp = requests.get(url)
        return [scan['ScanID'] for scan in resp.json()['Data']]

    def get_latest_ecmf_day(self):
        resp = requests.get(
            self.odin_api_root + '/v5/config_data/latest_ecmf_file')
        return resp.json()['Date']

    def generate_days_with_scans(self, start_day, end_day, freqmode,
                                 step_size=365):
        """Generate all days between two dates with scans in the specified
        freqmode.

        Args:
          start_day (datetime): Start from this day (inclusive).
          end_day (datetime): End with this day (exclusive).

        Yields:
          str: Day (%Y-%m-%d).
        """
        while start_day < end_day:
            resp = requests.get(
                self.odin_api_root + (
                    '/v5/period_info/{year}/{month:0>2}/{day:0>2}/'
                    '?length={nrdays}').format(
                        year=start_day.year, month=start_day.month,
                        day=start_day.day, nrdays=step_size))
            assert resp.status_code == 200
            data = resp.json()
            days = [
                (day['Date'], day['URL'], day['NumScan'])
                for day in data['Data']
                if day['FreqMode'] == freqmode and
                datetime.strptime(day['Date'], '%Y-%m-%d')
                < end_day
            ]
            for day in sorted(days):
                yield day
            start_day = datetime.strptime(
                data['PeriodEnd'], '%Y-%m-%d') + self.ONE_DAY
