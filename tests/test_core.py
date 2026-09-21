"""Тесты основной логики измерения."""

import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from speed_meter.core import (
    MeasurementError,
    download,
    measure_speed,
    validate_address,
)


class CoreTests(unittest.TestCase):
    @patch("speed_meter.core.urlopen")
    def test_counts_downloaded_bytes(self, urlopen_mock) -> None:
        """Загрузчик считает фактически прочитанные байты."""

        response = urlopen_mock.return_value.__enter__.return_value
        response.read.side_effect = [b"first", b"second", b""]

        result = download("https://example.com/file", timeout=5)

        self.assertEqual(result, 11)
        self.assertEqual(response.read.call_count, 3)

    def test_runs_ten_requests(self) -> None:
        """Измерение выполняет ровно десять последовательных загрузок."""

        calls: list[tuple[str, float]] = []
        timestamps = iter(float(value) for value in range(20))

        def downloader(address: str, timeout: float) -> int:
            calls.append((address, timeout))
            return 500_000

        result = measure_speed(
            "https://example.com/image.jpg",
            timeout=5,
            downloader=downloader,
            clock=lambda: next(timestamps),
        )

        self.assertEqual(len(calls), 10)
        self.assertEqual(result.request_count, 10)
        self.assertEqual(result.total_bytes, 5_000_000)
        self.assertEqual(result.total_seconds, 10)
        self.assertEqual(result.average_request_seconds, 1)
        self.assertEqual(result.downloaded_megabytes, 5)
        self.assertEqual(result.megabytes_per_second, 0.5)

    def test_rejects_invalid_address(self) -> None:
        """Относительные и неподдерживаемые адреса отклоняются."""

        invalid_addresses = ["example.com/file", "ftp://example.com/file", ""]

        for address in invalid_addresses:
            with self.subTest(address=address), self.assertRaises(ValueError):
                validate_address(address)

    def test_counts_request_errors(self) -> None:
        """Ошибки группируются по коду без остановки серии."""

        call_count = 0

        def downloader(address: str, timeout: float) -> int:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise HTTPError(address, 403, "Forbidden", None, None)
            if call_count == 2:
                raise HTTPError(address, 429, "Too Many Requests", None, None)
            if call_count == 3:
                raise TimeoutError("timed out")
            if call_count == 4:
                raise URLError("connection refused")
            return 1_000_000

        timestamps = iter(float(value) for value in range(10))
        result = measure_speed(
            "https://example.com/file",
            request_count=5,
            downloader=downloader,
            clock=lambda: next(timestamps),
        )

        self.assertEqual(call_count, 5)
        self.assertEqual(result.successful_request_count, 1)
        self.assertEqual(
            result.error_counts,
            {"HTTP 403": 1, "HTTP 429": 1, "TIMEOUT": 1, "NETWORK": 1},
        )
        self.assertEqual(result.successful_seconds, 1)
        self.assertEqual(result.megabytes_per_second, 1)

    def test_zero_speed_without_success(self) -> None:
        """При отсутствии успешных запросов скорость равна нулю."""

        def downloader(address: str, timeout: float) -> int:
            raise TimeoutError("timed out")

        timestamps = iter([0.0, 1.0])
        result = measure_speed(
            "https://example.com/file",
            request_count=1,
            downloader=downloader,
            clock=lambda: next(timestamps),
        )

        self.assertEqual(result.megabytes_per_second, 0)

    def test_rejects_zero_duration(self) -> None:
        """Нулевая длительность не приводит к делению на ноль."""

        with self.assertRaisesRegex(MeasurementError, "больше нуля"):
            measure_speed(
                "https://example.com/file",
                request_count=1,
                downloader=lambda address, timeout: 100,
                clock=lambda: 1.0,
            )


if __name__ == "__main__":
    unittest.main()
