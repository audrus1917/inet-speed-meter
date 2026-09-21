"""Тесты консольного интерфейса."""

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from speed_meter.cli import main
from speed_meter.core import Measurement, MeasurementError


class CliTests(unittest.TestCase):
    @patch("speed_meter.cli.measure_speed")
    def test_prints_measurement(self, measure_mock) -> None:
        """Успешный запуск печатает все требуемые показатели."""

        measure_mock.return_value = Measurement(10, 20_000_000, 5.0)
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main(["https://example.com/file"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Выполнено запросов: 10", output.getvalue())
        self.assertIn("Среднее время запроса: 0.500 с", output.getvalue())
        self.assertIn("Скачано данных: 20.00 МБ", output.getvalue())
        self.assertIn("Средняя скорость: 4.00 МБ/с", output.getvalue())

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
