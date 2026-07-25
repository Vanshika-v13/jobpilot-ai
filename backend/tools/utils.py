import asyncio
import random

async def random_delay(min_seconds: float = 2.0, max_seconds: float = 5.0) -> float:
    """
    Introduces a random sleep delay between min_seconds and max_seconds
    to humanize browser request timing and prevent IP rate-limiting.
    """
    delay = random.uniform(min_seconds, max_seconds)
    await asyncio.sleep(delay)
    return delay
