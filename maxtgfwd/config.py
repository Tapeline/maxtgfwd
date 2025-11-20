from argparse import ArgumentParser
from dataclasses import dataclass

from adaptix import P, Retort
from fuente import config_loader
from fuente.merger.base import Merger
from fuente.merger.simple import UseFirst
from fuente.merger_provider import merge
from fuente.sources.argparse import ArgParseSource
from fuente.sources.env import EnvSource
from fuente.sources.flat import FlatSource, FlatSourceLoader
from fuente.sources.yaml import YamlSource


class NonPatchingArgSource(ArgParseSource):
    def _make_loader(
        self,
        loading_retort: Retort,
        dumping_retort: Retort,
        config_type: type
    ) -> FlatSourceLoader:
        return FlatSource._make_loader(
            self, loading_retort, dumping_retort, config_type
        )

    def _gen_key(self, prefix: str, path: list[str]):
        return prefix + "__".join(x.lower() for x in path)


class UseLastNotNone[T](Merger):
    def _merge(self, name: str, x: T, y: T) -> T:
        return y or x


arg_parser = ArgumentParser(prog="maxtgfwd")
arg_parser.add_argument(
    "mode",
    default="run",
    choices=["run", "auth"]
)
arg_parser.add_argument(
    "--phone",
    default=None,
    required=False
)
arg_parser.add_argument(
    "--tg-token",
    "--tg_token",
    default=None,
    required=False
)
arg_parser.add_argument(
    "--auth__token",
    "--max-token",
    default=None,
    required=False
)
arg_parser.add_argument(
    "--auth__device",
    "--max-device",
    default=None,
    required=False
)


@dataclass
class CollectorConfig:
    sources: list[int]
    sinks: list[int]


@dataclass
class MaxAuth:
    device: str
    token: str


@dataclass
class Config:
    owner_handle: str
    tg_token: str
    auth: MaxAuth
    collectors: list[CollectorConfig]
    healthcheck_period_s: int = 30


app_config_loader = config_loader(
    YamlSource("config.yml"),
    EnvSource(prefix="MAXTGFWD_", sep="__"),
    NonPatchingArgSource(parser=arg_parser, sep="__"),
    config=Config,
    recipe=[
        merge(P[Config].tg_token, UseLastNotNone()),
        merge(P[Config].auth.token, UseLastNotNone()),
        merge(P[Config].auth.device, UseLastNotNone()),
    ]
)

_config = None


def load_config():
    global _config
    _config = app_config_loader.load()


def get_config():
    if not _config:
        raise ValueError("Config not loaded")
    return _config
