"""Тесты консольного интерфейса."""

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from speed_meter.cli import main
from speed_meter.core import Measurement, MeasurementError


class CliTests(unittest.TestCase):
    def test_rejects_request_count(self) -> None:
        """Неположительное количество запросов отклоняется."""

        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            main(["https://example.com/file", "--requests", "0"])

        self.assertEqual(error.exception.code, 2)

    @patch("speed_meter.cli.measure_speed")
    def test_sets_request_count(self, measure_mock) -> None:
        """Количество запросов передаётся из командной строки."""

        measure_mock.return_value = Measurement(3, 3_000_000, 3.0)

        with redirect_stdout(io.StringIO()):
            exit_code = main(["https://example.com/file", "--requests", "3"])

        self.assertEqual(exit_code, 0)
        measure_mock.assert_called_once_with(
            "https://example.com/file",
            request_count=3,
            timeout=20.0,
        )

    @patch("speed_meter.cli.measure_speed")
    def test_prints_measurement(self, measure_mock) -> None:
        """Успешный запуск печатает все требуемые показатели."""

        measure_mock.return_value = Measurement(
            10,
            20_000_000,
            5.0,
            {"HTTP 429": 2, "TIMEOUT": 1},
            successful_seconds=4.0,
        )
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main(["https://example.com/file"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Выполнено запросов: 10", output.getvalue())
        self.assertIn("Успешных запросов: 7", output.getvalue())
        self.assertIn("HTTP 429: 2", output.getvalue())
        self.assertIn("TIMEOUT: 1", output.getvalue())
        self.assertIn("Среднее время запроса: 0.500 с", output.getvalue())
        self.assertIn("Скачано данных: 20.00 МБ", output.getvalue())
        self.assertIn("Средняя скорость: 5.00 МБ/с", output.getvalue())

    @patch("speed_meter.cli.measure_speed")
    def test_reports_error(self, measure_mock) -> None:
        """Ошибка измерения возвращает ненулевой код и попадает в stderr."""

        measure_mock.side_effect = MeasurementError("сеть недоступна")
        errors = io.StringIO()

        with redirect_stderr(errors):
            exit_code = main(["https://example.com/file"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Ошибка: сеть недоступна", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
