import importlib
import pkgutil

from app import modules


def import_models() -> None:
    for info in pkgutil.iter_modules(modules.__path__, modules.__name__ + "."):
        if not info.ispkg:
            continue
        name = f"{info.name}.models"
        try:
            importlib.import_module(name)
        except ModuleNotFoundError as exc:
            if exc.name != name:
                raise
