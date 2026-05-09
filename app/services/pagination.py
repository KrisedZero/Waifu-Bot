from math import ceil
from typing import Sequence, TypeVar, Tuple, List

T = TypeVar("T")


def paginate(items: Sequence[T], page: int, page_size: int) -> tuple[list[T], int, int]:
    if page_size <= 0:
        raise ValueError("page_size must be > 0")

    total_items = len(items)
    total_pages = max(1, ceil(total_items / page_size))

    page = max(1, min(page, total_pages))

    start = (page - 1) * page_size
    end = start + page_size

    return list(items[start:end]), page, total_pages