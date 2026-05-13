from sundarr.app.sources.base import BaseSource
from sundarr.app.sources.seedhub import SeedHubSource


def get_registered_sources() -> list[BaseSource]:
    return [SeedHubSource()]
