"""Инструмент для измерения скорости загрузки по HTTP."""

from speed_meter.core import Measurement, MeasurementError, measure_speed

__all__ = ["Measurement", "MeasurementError", "measure_speed"]
