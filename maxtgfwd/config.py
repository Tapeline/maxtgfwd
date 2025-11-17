from dataclasses import dataclass
from pathlib import Path

from fuente import config_loader
from fuente.sources.env import EnvSource
from fuente.sources.yaml import YamlSource

session_file = Path(".maxsession")


@dataclass
class CollectorConfig:
    sources: list[int]
    sinks: list[int]


@dataclass
class Config:
    owner_handle: str
    tg_token: str
    auth_phone_number: str
    collectors: list[CollectorConfig]


app_config_loader = config_loader(
    YamlSource("config.yml"),
    EnvSource(prefix="MAXTGFWD_", sep="__"),
    config=Config,
)

config = app_config_loader.load()
