from pathlib import Path
import pandas as pd

from .config import settings


class GuardrailError(Exception):
    pass


def enforce_file_size(path: Path) -> None:
    mb = path.stat().st_size / (1024 * 1024)
    if mb > settings.MAX_FILE_MB:
        raise GuardrailError(
            f"File {path.name} is {mb:.1f}MB; limit is {settings.MAX_FILE_MB}MB."
        )


def enforce_row_limit(df: pd.DataFrame) -> pd.DataFrame:
    if len(df) > settings.MAX_ROWS:
        return df.sample(n=settings.MAX_ROWS, random_state=42).reset_index(drop=True)
    return df


def check_token_budget(total_tokens: int) -> None:
    if total_tokens > settings.MAX_TOKENS_PER_RUN:
        raise GuardrailError(
            f"Token budget exceeded: {total_tokens} > {settings.MAX_TOKENS_PER_RUN}"
        )
