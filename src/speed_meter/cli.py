"""Консольный интерфейс замерителя скорости."""

import argparse
import sys
from collections.abc import Sequence

from speed_meter.core import REQUEST_COUNT, MeasurementError, measure_speed


def build_parser() -> argparse.ArgumentParser:
    """Создать парсер аргументов командной строки."""

    parser = argparse.ArgumentParser(
        description=(
            f"Последовательно скачать ресурс {REQUEST_COUNT} раз и рассчитать "
            "среднюю скорость."
        )
    )
    parser.add_argument("address", help="URL файла для скачивания")
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        metavar="SECONDS",
        help="тайм-аут каждого запроса в секундах (по умолчанию: 30)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Запустить измерение и вернуть код завершения процесса."""

    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = measure_speed(args.address, timeout=args.timeout)
    except (ValueError, MeasurementError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nИзмерение прервано пользователем.", file=sys.stderr)
        return 130

    print(f"Выполнено запросов: {result.request_count}")
    print(f"Среднее время запроса: {result.average_request_seconds:.3f} с")
    print(f"Скачано данных: {result.downloaded_megabytes:.2f} МБ")
    print(f"Средняя скорость: {result.megabytes_per_second:.2f} МБ/с")
    return 0
