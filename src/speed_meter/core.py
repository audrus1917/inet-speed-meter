"""Основная логика измерения скорости загрузки."""

from collections.abc import Callable
from dataclasses import dataclass
from http.client import HTTPException
from time import perf_counter
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

REQUEST_COUNT = 10
CHUNK_SIZE = 64 * 1024
USER_AGENT = "internet-speed-meter/0.1.0"


class MeasurementError(RuntimeError):
    """Ошибка, из-за которой измерение невозможно завершить."""


@dataclass(frozen=True, slots=True)
class Measurement:
    """Итоговые показатели серии запросов."""

    request_count: int
    total_bytes: int
    total_seconds: float

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

        return self.downloaded_megabytes / self.total_seconds


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


def measure_speed(
    address: str,
    *,
    request_count: int = REQUEST_COUNT,
    timeout: float = 30.0,
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

    for request_number in range(1, request_count + 1):
        started_at = clock()
        try:
            total_bytes += downloader(address, timeout)
        except (HTTPError, URLError, HTTPException, TimeoutError, OSError) as error:
            raise MeasurementError(
                f"запрос {request_number} из {request_count} "
                f"завершился ошибкой: {error}"
            ) from error
        total_seconds += clock() - started_at

    if total_seconds <= 0:
        raise MeasurementError("время измерения должно быть больше нуля")

    return Measurement(
        request_count=request_count,
        total_bytes=total_bytes,
        total_seconds=total_seconds,
    )
