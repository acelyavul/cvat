import pytest

from cvat_tools.annotations import _resolve_box_attributes
from cvat_tools.decisions import record_decision


class FakeAttr:
    def __init__(
        self,
        id,
        name,
        input_type="checkbox",
        default_value="false",
    ):
        self.id = id
        self.name = name
        self.input_type = input_type
        self.default_value = default_value


class FakeLabel:
    def __init__(self):
        self.id = 1
        self.name = "tire"
        self.type = "rectangle"
        self.attributes = [
            FakeAttr(1, "is_crowd"),
            FakeAttr(3, "sidewall_only"),
        ]


def test_checkbox_attributes():
    values = _resolve_box_attributes(
        FakeLabel(),
        [
            "is_crowd=true",
            "sidewall_only=false",
        ],
    )

    result = {
        item.spec_id: item.value
        for item in values
    }

    assert result == {
        1: "true",
        3: "false",
    }


def test_checkbox_rejects_invalid_value():
    with pytest.raises(ValueError):
        _resolve_box_attributes(
            FakeLabel(),
            ["is_crowd=yes"],
        )


def test_unknown_attribute_rejected():
    with pytest.raises(ValueError):
        _resolve_box_attributes(
            FakeLabel(),
            ["unknown=true"],
        )


def test_decision_rejects_invalid_status(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError):
        record_decision(
            task_id=1,
            frame=0,
            status="MAYBE",
            reason="test",
        )


def test_decision_written(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    path, result = record_decision(
        task_id=1,
        frame=10,
        status="PASS",
        reason="Policy compliant",
    )

    assert path.exists()
    assert result["status"] == "PASS"
    assert result["frame"] == 10
