from tenacity import retry, stop_after_attempt, wait_exponential
from typing import Callable, TypeVar, Any

T = TypeVar('T')

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4))
def with_retry(fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    return fn(*args, **kwargs)
