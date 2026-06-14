# -*- coding: utf-8 -*-
"""
媒体作品分型配置。

movie-ingest 历史上以电影为主；大批量混合录入前，所有入口必须通过
profile 统一 module / submodule / schemaType / ID 前缀与字段要求。
"""
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional


MODULE_CODE = {
    "video": "01",
    "book": "02",
    "anime": "03",
    "music": "04",
    "game": "05",
}

SUBMODULE_CODE = {
    "movie": "01",
    "tv_series": "02",
    "tv": "02",
    "documentary": "03",
    "short_drama": "04",
    "short": "04",
    "anime_movie": "01",
    "anime_series": "02",
}


@dataclass(frozen=True)
class MediaProfile:
    key: str
    label: str
    module: str
    submodule: str
    schema_type: str
    tmdb_kind: str
    required_fields: List[str]
    series_fields: List[str]
    enhancement_required_fields: List[str]

    @property
    def id_prefix(self) -> str:
        return f"{MODULE_CODE[self.module]}{SUBMODULE_CODE[self.submodule]}"

    @property
    def asset_dir(self) -> str:
        return f"{self.module}/{self.submodule}"


MEDIA_PROFILES: Dict[str, MediaProfile] = {
    "live_action_movie": MediaProfile(
        key="live_action_movie",
        label="真人电影",
        module="video",
        submodule="movie",
        schema_type="live_action_movie",
        tmdb_kind="movie",
        required_fields=["id", "title", "year", "module", "submodule", "schemaType"],
        series_fields=[],
        enhancement_required_fields=[],
    ),
    "documentary_film": MediaProfile(
        key="documentary_film",
        label="纪录片",
        module="video",
        submodule="documentary",
        schema_type="documentary_film",
        tmdb_kind="movie",
        required_fields=["id", "title", "year", "module", "submodule", "schemaType"],
        series_fields=[],
        enhancement_required_fields=[],
    ),
    "animated_movie": MediaProfile(
        key="animated_movie",
        label="动画电影",
        module="anime",
        submodule="anime_movie",
        schema_type="animated_movie",
        tmdb_kind="movie",
        required_fields=["id", "title", "year", "module", "submodule", "schemaType"],
        series_fields=[],
        enhancement_required_fields=[],
    ),
    "live_action_series": MediaProfile(
        key="live_action_series",
        label="真人剧集",
        module="video",
        submodule="tv_series",
        schema_type="live_action_series",
        tmdb_kind="tv",
        required_fields=["id", "title", "year", "module", "submodule", "schemaType", "episodeCount"],
        series_fields=["episodeCount", "episodeTime", "episodesStory"],
        enhancement_required_fields=["episodesStory"],
    ),
    "documentary_series": MediaProfile(
        key="documentary_series",
        label="纪录片",
        module="video",
        submodule="documentary",
        schema_type="documentary_series",
        tmdb_kind="tv",
        required_fields=["id", "title", "year", "module", "submodule", "schemaType", "episodeCount"],
        series_fields=["episodeCount", "episodeTime", "episodesStory"],
        enhancement_required_fields=["episodesStory"],
    ),
    "animated_series": MediaProfile(
        key="animated_series",
        label="番剧 / 多季动画",
        module="anime",
        submodule="anime_series",
        schema_type="animated_series",
        tmdb_kind="tv",
        required_fields=["id", "title", "year", "module", "submodule", "schemaType", "episodeCount"],
        series_fields=["episodeCount", "episodeTime", "episodesStory", "characters"],
        enhancement_required_fields=["episodesStory", "characters"],
    ),
}


def normalize_schema_type(value: Optional[str]) -> str:
    return value or "live_action_movie"


def get_profile_by_schema_type(schema_type: Optional[str]) -> MediaProfile:
    key = normalize_schema_type(schema_type)
    if key not in MEDIA_PROFILES:
        raise ValueError(f"未知媒体 schemaType: {schema_type}")
    return MEDIA_PROFILES[key]


def get_profile(module: Optional[str], submodule: Optional[str], schema_type: Optional[str]) -> MediaProfile:
    if schema_type:
        profile = get_profile_by_schema_type(schema_type)
        if module and profile.module != module:
            raise ValueError(f"schemaType={schema_type} 期望 module={profile.module}，实际 {module}")
        if submodule and profile.submodule != submodule:
            raise ValueError(f"schemaType={schema_type} 期望 submodule={profile.submodule}，实际 {submodule}")
        return profile

    for profile in MEDIA_PROFILES.values():
        if profile.module == (module or "video") and profile.submodule == (submodule or "movie"):
            return profile

    return MEDIA_PROFILES["live_action_movie"]


def resolve_profile_from_data(data: Dict) -> MediaProfile:
    return get_profile(
        data.get("module"),
        data.get("submodule"),
        data.get("schemaType") or data.get("schema_type"),
    )


def apply_profile_defaults(data: Dict) -> Dict:
    profile = resolve_profile_from_data(data)
    data.setdefault("module", profile.module)
    data.setdefault("submodule", profile.submodule)
    data.setdefault("schemaType", profile.schema_type)
    return data


def expected_next_id(max_id: str, profile: MediaProfile) -> str:
    if not max_id:
        return f"{profile.id_prefix}000001"
    return f"{profile.id_prefix}{int(max_id[-6:]) + 1:06d}"


def supported_schema_types() -> Iterable[str]:
    return MEDIA_PROFILES.keys()
