"""Тесты ``tier_of_module``: тир берётся из сегмента-папки, а не из имени модуля."""

from db_models.tiers import Tier, tier_of_module


def test_base_tier_for_plain_model() -> None:
    assert tier_of_module("db_models.models.example.foo") is Tier.MAIN


def test_detects_tier_subpackage() -> None:
    assert tier_of_module("db_models.models.example.dev.bar") is Tier.DEV


def test_tier_named_module_at_schema_root_is_base() -> None:
    # Файл example/dev.py — модель базового тира: имя самого модуля не считается tier-папкой.
    assert tier_of_module("db_models.models.example.dev") is Tier.MAIN


def test_tier_segment_anywhere_in_path_wins() -> None:
    assert tier_of_module("db_models.models.example.dev.x") is Tier.DEV
