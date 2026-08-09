"""Tests for the schemas package (Parts 1-2 taxonomy, fields)."""

from __future__ import annotations

import pytest

from qros.governance.roles import ROLE_MATRIX, Role
from qros.schemas.corrections import ROLLOVER_METHODS, validate_factor_cross_vendor
from qros.schemas.data_types import DATA_TYPE_CATALOG, DATA_TYPE_IDS, DEPTH_LEVELS, validate_data_type_id
from qros.schemas.fields import EXP_ALL_IDS, EXP_FIELDS, HYP_ALL_IDS, HYP_FIELDS
from qros.schemas.vendors import VENDOR_CATALOG, VENDOR_CLASS_IDS, VendorClass


def test_13_data_types():
    assert len(DATA_TYPE_CATALOG) == 13
    assert len(DATA_TYPE_IDS) == 13


def test_depth_levels_l1_l2_l3():
    assert [d.level for d in DEPTH_LEVELS] == ["L1", "L2", "L3"]


def test_validate_data_type_id_rejects_unknown():
    with pytest.raises(ValueError):
        validate_data_type_id("NOPE")


def test_five_vendor_classes():
    assert len(VENDOR_CATALOG) == 5
    assert VENDOR_CLASS_IDS == {
        "direct_exchange_multicast",
        "consolidated_feed",
        "options_surface",
        "fundamental_reference",
        "macro_event",
    }


def test_hyp_fields_22_sequential():
    assert len(HYP_FIELDS) == 22
    assert [f.id for f in HYP_FIELDS] == [f"HYP-{i:02d}" for i in range(1, 23)]
    assert len(HYP_ALL_IDS) == 22


def test_exp_fields_17_sequential():
    assert len(EXP_FIELDS) == 17
    assert [f.id for f in EXP_FIELDS] == [f"EXP-{i:02d}" for i in range(1, 18)]
    assert len(EXP_ALL_IDS) == 17


def test_four_rollover_methods():
    assert {m.value for m in ROLLOVER_METHODS} == {
        "open_interest",
        "volume",
        "expiration_date",
        "ratio_adjusted_back",
    }


def test_cross_vendor_factor_validation():
    assert validate_factor_cross_vendor({"v1": 2.0, "v2": 2.0}) is True
    assert validate_factor_cross_vendor({"v1": 2.0, "v2": 2.5}) is False
    assert validate_factor_cross_vendor({"v1": 2.0}) is False


def test_eight_roles():
    assert len(ROLE_MATRIX) == 8
    assert Role.HEAD_OF_RESEARCH in ROLE_MATRIX
    assert Role.LEAD_STATISTICIAN in ROLE_MATRIX