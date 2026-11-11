import os
from typing import Any
from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict, YamlConfigSettingsSource

from nacsos_data.util.conf import OpenAlexConfig, DatabaseConfig


class AttributionConfig(BaseModel):
    """Attribution decisions read from the committed YAML file."""

    models: list[str]
    grid: str
    scenario: str
    obs_start_year: int  # first year of the observed series and of the variability estimate
    start_year: int  # first year of model trend windows
    first_end_year: int
    latest_year: int
    min_hist_nat: int  # minimum number of hist-nat runs for a model to be used
    n_samples: int  # resampled piControl segments per model and end year
    seed: int  # seed of the per-sample seeds
    splice_baseline_start: int  # baseline aligning paired scenario runs with all historical runs
    splice_baseline_end: int


class ScoringConfig(BaseModel):
    """Per-study attribution scoring decisions for the exports, read from the committed YAML file."""

    weight: str = 'population'  # cells column the shares are weighted by: 'population' (WorldPop persons) or 'area' (km²)
    threshold: float = 0.5  # a paper counts as attributable when its share reaches this


class Settings(BaseSettings):
    DB: DatabaseConfig = DatabaseConfig()  # NACSOS-core database
    OPENALEX: OpenAlexConfig = OpenAlexConfig()  # OpenAlex (solr/api) config

    LOG_CONF_FILE: str = 'config/logging.toml'
    LOGGING_CONF: dict[str, Any] | None = None

    PROJECT_ID: str = '52f62f17-cefb-4152-bcca-2fcb77541e83'  # Climate and Health Literature Landscape
    MAJOR_SCHEME_ORIG: str = '7dd7ac85-f472-4d95-ae63-a41de368ad95'  # Original annotations
    MAJOR_SCHEME_NEW: str = 'fbb0d34b-3232-48ab-9d9d-78164692e4e9'  # Climate and health major categories
    IMPACTS_SCHEME: list[str] = [
        '9cadee95-14c2-4790-b39f-7125f1f63346',  # Health impacts of climate change version 2
        'a8aba098-44e3-471a-87de-3d1a07c2b7ba',  # Health impacts of climate change (soon to be archived and translated/relabelled into 2)
    ]
    IMPORTS: list[str] = [
        '5b18344c-6c30-40ba-92ad-48a2136efe6b',  # oa climate health v4
    ]

    # Root of the (git-ignored) data tree synced via rsync (see Documentation/DataRetrieval.md)
    DATA_ROOT: Path = Path('data')

    # Committed attribution decisions, read from config/attribution.yaml (see Documentation/Attribution.md)
    ATTRIBUTION: AttributionConfig
    SCORING: ScoringConfig = ScoringConfig()

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_prefix='NACSOS_',
        env_nested_delimiter='__',
        extra='allow',
        yaml_file='config/attribution.yaml',
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Source order: attribution YAML, init, environment, env file, secrets
        return (YamlConfigSettingsSource(settings_cls), init_settings, env_settings, dotenv_settings, file_secret_settings)


def load_settings(conf_file: Path | str | None = None) -> Settings:
    if conf_file is None:
        conf_file = os.environ.get('CH_CONFIG', 'config/default.env')
    if not Path(conf_file).is_file():
        raise FileNotFoundError(f'Configuration file not found: {conf_file}')
    return Settings(_env_file=conf_file, _env_file_encoding='utf-8')
