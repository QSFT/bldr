import argparse
import json
import logging

from abc import abstractmethod, ABC
from pathlib import Path
from typing import Any, Dict, IO, List, Optional, Sequence, Tuple


class ConfigLoaderError(Exception):
    pass


class ConfigLoader(ABC):
    def __init__(self, paths: List[Path]):
        self.paths = paths
        self.config = None

    def copy(self) -> 'ConfigLoader':
        return type(self)(list(self.paths))

    def load_config_file(self, path: Path) -> Dict:
        with path.open() as config_file:
            config = self.parse(config_file)
        return config

    def load(self) -> Dict[str, Any]:
        retval: Dict[str, Any] = {}
        for path in self.paths:
            try:
                config = self.load_config_file(path)
            except IOError:
                continue

            for key, value in config.items():
                if value is None:
                    if key in retval:
                        retval.pop(key)
                else:
                    retval[key] = value

        return retval

    @abstractmethod
    def parse(self, file_object: IO[str]) -> Dict[str, Any]:
        pass


class JSONConfigLoader(ConfigLoader):
    def parse(self, file_object: IO[str]) -> Dict[str, Any]:
        return json.load(file_object)


def parse_action(action: argparse.Action, args: Optional[Sequence[str]] = None) -> Tuple[argparse.Namespace, List[str]]:
    parser = argparse.ArgumentParser(add_help=False)
    parser._add_action(action)
    namespace, argv = parser.parse_known_args(args)
    return (namespace, argv)


class SubParsers:
    def __init__(self, config_loader, subparsers, required=True):
        self.config_loader = config_loader
        self.subparsers = subparsers
        self.subparsers.required = required

    def add_parser(self, *args, **kwargs):
        kwargs = kwargs.copy()
        kwargs["config_loader"] = self.config_loader
        parser = self.subparsers.add_parser(*args, **kwargs)
        return parser


class ArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args: Any, **kwargs: Any):
        self.config_loader = kwargs.pop("config_loader", None)
        self.logger = logging.getLogger(__name__)

        super().__init__(*args, **kwargs)

    def parse_known_args(self, args: Optional[Sequence[str]] = None, namespace: argparse.Namespace = None) -> Tuple[argparse.Namespace, List[str]]:
        if self.config_loader:
            self.set_defaults_from_config(args)
        return super().parse_known_args(args, namespace=None)

    def set_defaults_from_config(self, args: Optional[Sequence[str]] = None) -> None:
        # make a copy here as we may adjust the paths attribute below
        loader = self.config_loader.copy()

        config = loader.load()

        self.set_defaults(**config)
