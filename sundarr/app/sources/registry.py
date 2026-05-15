from sundarr.app.sources.base import SourceModel
from sundarr.app.sources.seedhub import SeedHubSource


def get_builtin_sources() -> list[SourceModel]:
    seedhub = SeedHubSource()
    return [
        SourceModel(
            id=seedhub.id,
            name=seedhub.name,
            description=seedhub.description,
            homepage_url=seedhub.homepage_url,
            search_function=seedhub.search,
            test_function=seedhub.test_search,
        )
    ]


def get_registered_sources() -> list[SourceModel]:
    return get_builtin_sources()
