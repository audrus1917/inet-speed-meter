"""Консольный интерфейс замерителя скорости."""

import argparse
import sys
from collections.abc import Sequence

from speed_meter.core import (
    DEFAULT_REQUEST_COUNT,
    DEFAULT_TIMEOUT,
    KEYBOARD_INTERRUPT_CODE,
    MEASUREMENT_ERROR_CODE,
    MeasurementError,
    measure_speed,
)


def positive_int(value: str) -> int:
    """Преобразовать строку в положительное целое число."""

    try:
        result = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("значение должно быть целым числом") from error
    if result <= 0:
        raise argparse.ArgumentTypeError("значение должно быть больше нуля")
    return result


def build_parser() -> argparse.ArgumentParser:
    """Создать парсер аргументов командной строки."""

    parser = argparse.ArgumentParser(
        description=(
            "Последовательно скачать ресурс несколько раз и рассчитать "
            "среднюю скорость."
        )
    )
    parser.add_argument("address", help="URL файла для скачивания")
    parser.add_argument(
        "-n",
        "--requests",
        type=positive_int,
        default=DEFAULT_REQUEST_COUNT,
        metavar="COUNT",
        help=f"количество запросов (по умолчанию: {DEFAULT_REQUEST_COUNT})",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        metavar="SECONDS",
        help=f"тайм-аут каждого запроса в секундах (по умолчанию: {DEFAULT_TIMEOUT:g})",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Запустить измерение и вернуть код завершения процесса."""

    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = measure_speed(
            args.address,
            request_count=args.requests,
            timeout=args.timeout,
        )
    except (ValueError, MeasurementError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return MEASUREMENT_ERROR_CODE
    except KeyboardInterrupt:
        print("\nИзмерение прервано пользователем.", file=sys.stderr)
        return KEYBOARD_INTERRUPT_CODE

    print(f"Выполнено запросов: {result.request_count}")
    print(f"Успешных запросов: {result.successful_request_count}")
    if result.error_counts:
        print("Ошибки по кодам:")
        for error_code, count in sorted(result.error_counts.items()):
            print(f"  {error_code}: {count}")
    else:
        print("Ошибок: 0")
    print(f"Среднее время запроса: {result.average_request_seconds:.3f} с")
    print(f"Скачано данных: {result.downloaded_megabytes:.2f} МБ")
    print(f"Средняя скорость: {result.megabytes_per_second:.2f} МБ/с")
    return 0
