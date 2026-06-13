from __future__ import annotations

import asyncio
import importlib
import sys
import types
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import apex_service


def _install_astrbot_stubs() -> None:
    if "astrbot.api" in sys.modules:
        return

    astrbot_mod = types.ModuleType("astrbot")
    api_mod = types.ModuleType("astrbot.api")
    event_mod = types.ModuleType("astrbot.api.event")
    components_mod = types.ModuleType("astrbot.api.message_components")
    star_mod = types.ModuleType("astrbot.api.star")

    class _Logger:
        def __getattr__(self, _name):
            return lambda *args, **kwargs: None

    class _Filter:
        class EventMessageType:
            ALL = "ALL"

        @staticmethod
        def command(*_args, **_kwargs):
            return lambda func: func

        @staticmethod
        def event_message_type(*_args, **_kwargs):
            return lambda func: func

    class _MessageChain:
        pass

    class _AstrMessageEvent:
        pass

    class _Star:
        pass

    class _Context:
        pass

    class _StarTools:
        @staticmethod
        def get_data_dir(*_args, **_kwargs):
            return Path("data")

    api_mod.logger = _Logger()
    event_mod.AstrMessageEvent = _AstrMessageEvent
    event_mod.MessageChain = _MessageChain
    event_mod.filter = _Filter()
    star_mod.Context = _Context
    star_mod.Star = _Star
    star_mod.StarTools = _StarTools

    sys.modules["astrbot"] = astrbot_mod
    sys.modules["astrbot.api"] = api_mod
    sys.modules["astrbot.api.event"] = event_mod
    sys.modules["astrbot.api.message_components"] = components_mod
    sys.modules["astrbot.api.star"] = star_mod


def _load_main_module():
    _install_astrbot_stubs()
    return importlib.import_module("main")


def _sample_player(main_module):
    return main_module.ApexPlayerStats(
        name="yumola",
        uid="123456",
        level=321,
        rank_score=18888,
        rank_name="Master",
        rank_div=0,
        global_rank_percent="0.7",
        is_online=True,
        selected_legend="Wraith",
        legend_kills_rank=None,
        current_state="in Lobby",
        is_in_lobby_or_match=True,
        platform="PC",
    )


def _blank_name_uid_payload():
    return {
        "global": {
            "name": "",
            "uid": "1007669673322",
            "level": 358,
            "rank": {
                "rankScore": 5933,
                "rankName": "Gold",
                "rankDiv": 4,
                "ALStopPercentGlobal": 54,
            },
        },
        "realtime": {
            "isOnline": 0,
            "selectedLegend": "Mad Maggie",
            "currentStateAsText": "Offline",
        },
        "legends": {"selected": {"data": []}},
    }


def test_output_mode_defaults_to_image_and_accepts_text():
    main_module = _load_main_module()

    default_config = main_module.PluginConfig.from_raw({})
    text_config = main_module.PluginConfig.from_raw({"output_mode": "text"})
    invalid_config = main_module.PluginConfig.from_raw({"output_mode": "bad"})

    assert default_config.output_mode == "image"
    assert text_config.output_mode == "text"
    assert invalid_config.output_mode == "image"


def test_player_rank_text_mode_does_not_render_image(monkeypatch):
    main_module = _load_main_module()
    plugin = object.__new__(main_module.Main)
    plugin._config = types.SimpleNamespace(
        api_key="legacy_key",
        tracker_api_key="tracker_key",
        min_valid_score=1,
        output_mode="text",
    )
    plugin._api = types.SimpleNamespace(
        fetch_player_stats_auto=lambda identifier, platform, use_uid: _async_return(
            (_sample_player(main_module), "PC")
        )
    )

    render_calls = []
    monkeypatch.setattr(plugin, "_render_player_rank_image", lambda player: render_calls.append(player))
    monkeypatch.setattr(plugin, "_guard_access", lambda event: "")
    monkeypatch.setattr(plugin, "_parse_player_platform", lambda event, player, platform: (player, platform))
    monkeypatch.setattr(plugin, "_is_blacklisted", lambda player: False)
    monkeypatch.setattr(plugin, "_is_query_blocked", lambda player: False)
    monkeypatch.setattr(plugin, "_time_line", lambda: "TIME")
    monkeypatch.setattr(plugin, "_plain", lambda event, text: ("plain", text))
    monkeypatch.setattr(plugin, "_image", lambda event, path: ("image", path))

    class _Event:
        pass

    async def collect():
        return [item async for item in plugin.apexrank(_Event(), "yumola", "pc")]

    result = asyncio.run(collect())

    assert render_calls == []
    assert result[0][0] == "plain"
    assert "yumola" in result[0][1]


def test_player_rank_image_mode_uses_rendered_image(monkeypatch, tmp_path):
    main_module = _load_main_module()
    image_path = tmp_path / "rank.png"
    plugin = object.__new__(main_module.Main)
    plugin._config = types.SimpleNamespace(
        api_key="legacy_key",
        tracker_api_key="tracker_key",
        min_valid_score=1,
        output_mode="image",
    )
    plugin._api = types.SimpleNamespace(
        fetch_player_stats_auto=lambda identifier, platform, use_uid: _async_return(
            (_sample_player(main_module), "PC")
        )
    )

    monkeypatch.setattr(plugin, "_render_player_rank_image", lambda player: image_path)
    monkeypatch.setattr(plugin, "_guard_access", lambda event: "")
    monkeypatch.setattr(plugin, "_parse_player_platform", lambda event, player, platform: (player, platform))
    monkeypatch.setattr(plugin, "_is_blacklisted", lambda player: False)
    monkeypatch.setattr(plugin, "_is_query_blocked", lambda player: False)
    monkeypatch.setattr(plugin, "_plain", lambda event, text: ("plain", text))
    monkeypatch.setattr(plugin, "_image", lambda event, path: ("image", path))

    class _Event:
        pass

    async def collect():
        return [item async for item in plugin.apexrank(_Event(), "yumola", "pc")]

    result = asyncio.run(collect())

    assert result == [("image", image_path)]


def test_cn_query_uid_command_accepts_api_response_with_blank_player_name(monkeypatch):
    main_module = _load_main_module()
    api_client = object.__new__(main_module.ApexApiClient)
    api_client._api_key = "key"
    api_client._tracker_api_key = "tracker_key"

    async def fake_request(_url, _params):
        return _blank_name_uid_payload()

    async def fake_tracker_request(_url, _identifier):
        return _blank_name_uid_payload()

    api_client._request_with_retry = fake_request
    api_client._request_tracker_player_data = fake_tracker_request

    plugin = object.__new__(main_module.Main)
    plugin._config = types.SimpleNamespace(
        api_key="key", tracker_api_key="tracker_key", min_valid_score=1, output_mode="text"
    )
    plugin._api = api_client

    monkeypatch.setattr(plugin, "_guard_access", lambda event: "")
    monkeypatch.setattr(plugin, "_is_blacklisted", lambda player: False)
    monkeypatch.setattr(plugin, "_is_query_blocked", lambda player: False)
    monkeypatch.setattr(plugin, "_time_line", lambda: "TIME")
    monkeypatch.setattr(plugin, "_plain", lambda event, text: ("plain", text))
    monkeypatch.setattr(plugin, "_image", lambda event, path: ("image", path))

    class _Event:
        pass

    async def collect():
        return [
            item
            async for item in plugin.apexrank_query_cn(
                _Event(), "uid:1007669673322", "pc"
            )
        ]

    result = asyncio.run(collect())

    assert len(result) == 1
    assert result[0][0] == "plain"
    assert "未找到该玩家" not in result[0][1]
    assert "1007669673322" in result[0][1]
    assert "5933" in result[0][1]
    assert "黄金 4" in result[0][1]


async def _async_return(value):
    return value


def test_apexrank_requires_tracker_api_key(monkeypatch):
    main_module = _load_main_module()
    plugin = object.__new__(main_module.Main)
    plugin._config = types.SimpleNamespace(
        api_key="legacy_key",
        tracker_api_key="",
        min_valid_score=1,
        output_mode="text",
    )
    plugin._api = types.SimpleNamespace()

    monkeypatch.setattr(plugin, "_guard_access", lambda event: "")
    monkeypatch.setattr(
        plugin, "_parse_player_platform", lambda event, player, platform: (player, platform)
    )
    monkeypatch.setattr(plugin, "_is_blacklisted", lambda player: False)
    monkeypatch.setattr(plugin, "_is_query_blocked", lambda player: False)
    monkeypatch.setattr(plugin, "_time_line", lambda: "TIME")
    monkeypatch.setattr(plugin, "_plain", lambda event, text: ("plain", text))

    class _Event:
        pass

    async def collect():
        return [item async for item in plugin.apexrank(_Event(), "yumola", "pc")]

    result = asyncio.run(collect())
    assert result[0][0] == "plain"
    assert "tracker_api_key" in result[0][1]


def test_apexmap_requires_legacy_api_key(monkeypatch):
    main_module = _load_main_module()
    plugin = object.__new__(main_module.Main)
    plugin._config = types.SimpleNamespace(
        api_key="",
        tracker_api_key="tracker_key",
        min_valid_score=1,
        output_mode="text",
    )
    plugin._api = types.SimpleNamespace()

    monkeypatch.setattr(plugin, "_guard_access", lambda event: "")
    monkeypatch.setattr(plugin, "_time_line", lambda: "TIME")
    monkeypatch.setattr(plugin, "_plain", lambda event, text: ("plain", text))

    class _Event:
        pass

    async def collect():
        return [item async for item in plugin.apexmap(_Event())]

    result = asyncio.run(collect())
    assert result[0][0] == "plain"
    assert "api_key（地图/猎杀线专用）" in result[0][1]


def test_dual_key_routing_tracker_vs_legacy(monkeypatch):
    class _SilentLogger:
        def __getattr__(self, _name):
            return lambda *args, **kwargs: None

    class _DummyAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def aclose(self):
            return None

    async def run_case():
        monkeypatch.setattr(apex_service.httpx, "AsyncClient", _DummyAsyncClient)
        client = apex_service.ApexApiClient(
            api_key="legacy_123",
            tracker_api_key="tracker_456",
            timeout_ms=1000,
            max_retries=0,
            logger=_SilentLogger(),
        )
        captured: dict[str, object] = {}

        async def fake_with_headers(url, params, headers):
            captured["player_url"] = url
            captured["player_params"] = params
            captured["player_headers"] = headers
            return {
                "data": {
                    "platformInfo": {"platformUserIdentifier": "9997kazusa"},
                    "segments": [
                        {
                            "type": "overview",
                            "stats": {
                                "level": {"value": 1},
                                "rankScore": {"value": 1, "metadata": {"rankName": "Unranked"}},
                            },
                        }
                    ],
                }
            }

        async def fake_retry(url, params):
            captured["legacy_url"] = url
            captured["legacy_params"] = params
            return {}

        client._request_with_retry_with_headers = fake_with_headers
        client._request_with_retry = fake_retry
        try:
            await client.fetch_player_stats_by_name("9997kazusa", "PC")
            await client.fetch_predator_info()
        finally:
            await client.close()

        assert "public-api.tracker.gg" in str(captured["player_url"])
        assert captured["player_params"] == {}
        assert "auth" not in captured["player_params"]  # type: ignore[operator]
        assert captured["player_headers"]["TRN-Api-Key"] == "tracker_456"  # type: ignore[index]
        assert "api.mozambiquehe.re/predator" in str(captured["legacy_url"])
        assert captured["legacy_params"]["auth"] == "legacy_123"  # type: ignore[index]

    asyncio.run(run_case())


def test_parse_tracker_player_stats():
    payload = {
        "data": {
            "platformInfo": {
                "platformUserIdentifier": "9997kazusa",
                "platformUserId": "1234567890",
            },
            "metadata": {
                "activeLegendName": "Wraith",
            },
            "segments": [
                {
                    "type": "overview",
                    "stats": {
                        "level": {"value": 321},
                        "rankScore": {
                            "value": 15000,
                            "percentile": 0.5,
                            "metadata": {"rankName": "Diamond 4"},
                        },
                    },
                },
                {
                    "type": "legend",
                    "metadata": {"name": "Wraith", "isActive": True},
                    "stats": {
                        "kills": {
                            "value": 888,
                            "percentile": 1.23,
                        }
                    },
                },
            ],
        }
    }

    stats = apex_service._parse_player_stats(payload, "PC", "fallback_name")

    assert stats.name == "9997kazusa"
    assert stats.uid == "1234567890"
    assert stats.level == 321
    assert stats.rank_score == 15000
    assert stats.rank_name == "钻石"
    assert stats.rank_div == 4
    assert stats.global_rank_percent == "0.50"
    assert stats.is_online is False
    assert stats.selected_legend == "恶灵"
    assert stats.legend_kills_rank is not None
    assert stats.legend_kills_rank.value == 888
    assert stats.legend_kills_rank.global_percent == "1.23"
    assert stats.current_state == "离线"
    assert stats.is_in_lobby_or_match is False


def test_parse_legacy_mozambique_player_stats_still_works():
    payload = {
        "global": {
            "name": "legacy_player",
            "uid": "legacy_uid",
            "level": 55,
            "rank": {
                "rankScore": 4321,
                "rankName": "Gold",
                "rankDiv": 2,
                "ALStopPercentGlobal": "5.4",
            },
        },
        "realtime": {
            "isOnline": 1,
            "selectedLegend": "Pathfinder",
            "currentStateAsText": "inLobby",
        },
        "legends": {
            "selected": {
                "data": [
                    {
                        "name": "BR Kills",
                        "value": 100,
                        "rank": {"topPercent": 2.34},
                    }
                ]
            }
        },
    }

    stats = apex_service._parse_player_stats(payload, "PC", "fallback_name")

    assert stats.name == "legacy_player"
    assert stats.uid == "legacy_uid"
    assert stats.rank_score == 4321
    assert stats.rank_name == "黄金"
    assert stats.rank_div == 2
    assert stats.global_rank_percent == "5.4"
    assert stats.is_online is True
    assert stats.selected_legend == "探路者"
    assert stats.current_state == "在大厅"


def test_tracker_not_found_detection_and_error_message():
    not_found_payload = {
        "errors": [
            {
                "code": "CollectorResultStatus::NotFound",
                "message": "CollectorResultStatus::NotFound",
            }
        ]
    }

    assert apex_service._is_player_not_found(not_found_payload) is True

    response = httpx.Response(
        404,
        json=not_found_payload,
        request=httpx.Request(
            "GET",
            "https://public-api.tracker.gg/v2/apex/standard/profile/origin/none",
        ),
    )
    message = apex_service._extract_response_error_message(response)
    assert "NotFound" in message
