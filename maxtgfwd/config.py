from argparse import ArgumentParser
from dataclasses import dataclass

from fuente import config_loader
from fuente.sources.argparse import ArgParseSource
from fuente.sources.env import EnvSource
from fuente.sources.yaml import YamlSource


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
    "--auth_token",
    "--max-token",
    required=False
)
arg_parser.add_argument(
    "--auth_device",
    "--max-device",
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
    ArgParseSource(parser=arg_parser),
    config=Config,
)

_config = None


def load_config():
    global _config
    _config = app_config_loader.load()


def get_config():
    if not _config:
        raise ValueError("Config not loaded")
    return _config
