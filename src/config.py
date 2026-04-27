import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Settings:
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    MODEL_PLANNER: str = os.getenv("MODEL_PLANNER", "claude-opus-4-5-20250929")
    MODEL_PLAN_REVIEWER: str = os.getenv("MODEL_PLAN_REVIEWER", "gpt-4o")
    MODEL_EXECUTOR: str = os.getenv("MODEL_EXECUTOR", "claude-sonnet-4-5-20250929")
    MODEL_NARRATOR: str = os.getenv("MODEL_NARRATOR", "claude-sonnet-4-5-20250929")
    MODEL_OUTPUT_REVIEWER: str = os.getenv("MODEL_OUTPUT_REVIEWER", "gpt-4o")
    MODEL_OUTPUT_REFINER: str = os.getenv(
        "MODEL_OUTPUT_REFINER", "claude-sonnet-4-5-20250929"
    )

    MAX_ROWS: int = int(os.getenv("MAX_ROWS", "1000000"))
    MAX_FILE_MB: int = int(os.getenv("MAX_FILE_MB", "100"))
    MAX_TOKENS_PER_RUN: int = int(os.getenv("MAX_TOKENS_PER_RUN", "200000"))
    MAX_PLAN_ROUNDS: int = int(os.getenv("MAX_PLAN_ROUNDS", "2"))
    MAX_OUTPUT_ROUNDS: int = int(os.getenv("MAX_OUTPUT_ROUNDS", "2"))
    MAX_EXECUTOR_STEPS: int = int(os.getenv("MAX_EXECUTOR_STEPS", "20"))

    RUNS_DIR: Path = Path(os.getenv("RUNS_DIR", "runs"))

    @classmethod
    def run_dir(cls, run_id: str) -> Path:
        d = cls.RUNS_DIR / run_id
        (d / "charts").mkdir(parents=True, exist_ok=True)
        (d / "uploads").mkdir(parents=True, exist_ok=True)
        return d


settings = Settings()
