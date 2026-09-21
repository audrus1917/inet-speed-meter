"""Основная логика измерения скорости загрузки."""

from collections.abc import Callable
from dataclasses import dataclass, field
from http.client import HTTPException
from time import perf_counter
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

DEFAULT_REQUEST_COUNT = 10
DEFAULT_TIMEOUT = 20.0
CHUNK_SIZE = 64 * 1024
USER_AGENT = "internet-speed-meter/0.1.0"

MEASUREMENT_ERROR_CODE = 1
KEYBOARD_INTERRUPT_CODE = 130


class MeasurementError(RuntimeError):
    """Ошибка, из-за которой измерение невозможно завершить."""


@dataclass(frozen=True, slots=True)
class Measurement:
    """Итоговые показатели серии запросов."""

    request_count: int
    total_bytes: int
    total_seconds: float
    error_counts: dict[str, int] = field(default_factory=dict)
    successful_seconds: float | None = None

    @property
    def successful_request_count(self) -> int:
        """Вернуть количество успешно завершённых запросов."""

        return self.request_count - sum(self.error_counts.values())

    @property
    def average_request_seconds(self) -> float:
        """Вернуть среднее время одного запроса в секундах."""

        return self.total_seconds / self.request_count

    @property
    def downloaded_megabytes(self) -> float:
        """Вернуть объём скачанных данных в десятичных мегабайтах."""

        return self.total_bytes / 1_000_000

    @property
    def megabytes_per_second(self) -> float:
        """Вернуть среднюю скорость в десятичных мегабайтах в секунду."""

        download_seconds = (
            self.total_seconds
            if self.successful_seconds is None
            else self.successful_seconds
        )
        if download_seconds <= 0:
            return 0.0
        return self.downloaded_megabytes / download_seconds


def validate_address(address: str) -> None:
    """Проверить, что адрес является абсолютным HTTP(S)-адресом."""

    parsed = urlparse(address)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("адрес должен быть абсолютным URL со схемой http или https")


def download(address: str, timeout: float) -> int:
    """Скачать ресурс целиком и вернуть фактическое число полученных байтов."""

    request = Request(address, headers={"User-Agent": USER_AGENT})
    downloaded = 0
    with urlopen(request, timeout=timeout) as response:
        while chunk := response.read(CHUNK_SIZE):
            downloaded += len(chunk)
    return downloaded


def classify_error(error: Exception) -> str:
    """Вернуть стабильный код сетевой ошибки без деталей исключения."""

    if isinstance(error, HTTPError):
        return f"HTTP {error.code}"
    if isinstance(error, TimeoutError):
        return "TIMEOUT"
    if isinstance(error, URLError) and isinstance(error.reason, TimeoutError):
        return "TIMEOUT"
    return "NETWORK"


def measure_speed(
    address: str,
    *,
    request_count: int = DEFAULT_REQUEST_COUNT,
    timeout: float = DEFAULT_TIMEOUT,
    downloader: Callable[[str, float], int] = download,
    clock: Callable[[], float] = perf_counter,
) -> Measurement:
    """Последовательно скачать ресурс и вычислить итоговые показатели."""

    validate_address(address)
    if request_count <= 0:
        raise ValueError("количество запросов должно быть положительным")
    if timeout <= 0:
        raise ValueError("тайм-аут должен быть положительным")

    total_bytes = 0
    total_seconds = 0.0
    successful_seconds = 0.0
    error_counts: dict[str, int] = {}

    for _ in range(request_count):
        started_at = clock()
        request_succeeded = False
        try:
            total_bytes += downloader(address, timeout)
            request_succeeded = True
        except (HTTPError, URLError, HTTPException, TimeoutError, OSError) as error:
            error_code = classify_error(error)
            error_counts[error_code] = error_counts.get(error_code, 0) + 1
        finally:
            request_seconds = clock() - started_at
            total_seconds += request_seconds
            if request_succeeded:
                successful_seconds += request_seconds

    if total_seconds <= 0:
        raise MeasurementError("время измерения должно быть больше нуля")

    return Measurement(
        request_count=request_count,
        total_bytes=total_bytes,
        total_seconds=total_seconds,
        error_counts=error_counts,
        successful_seconds=successful_seconds,
    )
