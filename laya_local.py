"""Build a Laya Router that loads checkpoints from a local folder (offline).

The folder is a copy of the Hugging Face repo `convaiinnovations/laya`, which bundles
all three checkpoints:

    <LAYA_MODEL_DIR>/model.safetensors                  english
    <LAYA_MODEL_DIR>/multilingual/model.safetensors     multilingual (100+ languages)
    <LAYA_MODEL_DIR>/typed-decisions/model.safetensors  typed-decisions

Set LAYA_MODEL_DIR to that folder. If it is unset, ./models/laya is used.
"""
import os
from pathlib import Path

# Never reach out to the Hugging Face Hub: everything comes from disk.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

from laya import Router  # noqa: E402

DEFAULT_DIR = Path(__file__).resolve().parent / "models" / "laya"


def model_dir() -> str:
    path = Path(os.environ.get("LAYA_MODEL_DIR", DEFAULT_DIR)).resolve()
    if not (path / "multilingual" / "model.safetensors").is_file():
        raise FileNotFoundError(
            f"Laya checkpoints not found in {path}. "
            "Set LAYA_MODEL_DIR to the unzipped 'laya' folder."
        )
    return str(path)


def local_router(**kwargs) -> Router:
    """Router whose english / multilingual / typed-decisions entries point at local files."""
    root = model_dir()
    models = {
        "multilingual": (root, "multilingual"),
    }
    # The english and typed-decisions checkpoints are optional: ship only multilingual
    # and English text is answered by the multilingual checkpoint too.
    if (Path(root) / "model.safetensors").is_file():
        models["english"] = (root, None)
    else:
        models["english"] = (root, "multilingual")
    if (Path(root) / "typed-decisions" / "model.safetensors").is_file():
        models["typed-decisions"] = (root, "typed-decisions")
    return Router(models=models, **kwargs)
