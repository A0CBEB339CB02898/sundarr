from sundarr.app.sources.base import SourceModel
from sundarr.app.sources.seedhub import SeedHubSource


def get_registered_sources() -> list[SourceModel]:
    seedhub = SeedHubSource()
    return [
        SourceModel(
            id=seedhub.id,
            name=seedhub.name,
            description=seedhub.description,
            search_function=seedhub.search,
        )
    ]
