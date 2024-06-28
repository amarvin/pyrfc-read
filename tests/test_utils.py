import pytest

from pyrfc_read.utils import field_value, format_fields, format_value, format_wheres


@pytest.mark.parametrize(
    "value, field_type, expected",
    [
        ("123", "I", 123),
        ("0123", "I", 123),
        (123, "I", 123),
        ("ABC", "C", "ABC"),
        ("ABC    ", "C", "ABC"),
        (123.45, "F", 123.45),
        ("a 123.45", "F", "a 123.45"),
    ],
)
def test_field_value(value, field_type, expected):
    assert field_value(value, field_type) == expected


def test_format_fields():
    assert format_fields(None) == ""
    assert format_fields("") == ""
    assert format_fields("*") == ""
    assert format_fields("ABC") == [{"FIELDNAME": "ABC"}]
    assert format_fields(("ABC", "DEF")) == [
        {"FIELDNAME": "ABC"},
        {"FIELDNAME": "DEF"},
    ]
    assert format_fields(["ABC", "DEF"]) == [
        {"FIELDNAME": "ABC"},
        {"FIELDNAME": "DEF"},
    ]

    # Improper fields format
    fields = object()
    with pytest.raises(ValueError):
        format_fields(fields)


@pytest.mark.parametrize(
    "value, field_type, field_length, expected",
    [
        ("123", "C", 7, "'0000123'"),
        ("123.45", "C", 7, "'0123.45'"),
        ("ABC", "C", 7, "'ABC'"),
        (123, "I", 7, "'123'"),
        (123.45, "F", 7, "'123.45'"),
        (123.45, "P", 7, "'123.45'"),
    ],
)
def test_format_value(value, field_type, field_length, expected):
    assert format_value(value, field_type, field_length) == expected


def test_format_wheres():
    field_info = {
        "Field1": {"INTTYPE": "C", "LENG": 7},
        "Field2": {"INTTYPE": "I", "LENG": 2},
    }
    assert format_wheres(None, field_info) == [{"TEXT": ""}]
    assert format_wheres("", field_info) == [{"TEXT": ""}]
    assert format_wheres("ABC", field_info) == [{"TEXT": "ABC"}]
    assert format_wheres(["ABC", "DEF"], field_info) == [
        {"TEXT": "ABC AND DEF"},
    ]
    assert format_wheres(
        "A long query condition that has to be split into many lines, as it's too long for SAP.",
        field_info,
    ) == [
        {
            "TEXT": "A long query condition that has to be split into many lines, as it's too"
        },
        {"TEXT": " long for SAP."},
    ]
    assert format_wheres([["Field1", "in", ["ABC", "DEF", "GHI"]]], field_info) == [
        {"TEXT": "(Field1 = 'ABC' OR Field1 = 'DEF' OR Field1 = 'GHI')"}
    ]
    assert format_wheres([["Field1", "not in", ["ABC", "DEF", "GHI"]]], field_info) == [
        {"TEXT": "(Field1 <> 'ABC' AND Field1 <> 'DEF' AND Field1 <> 'GHI')"}
    ]
    assert format_wheres([[["Field1", "Field2"], "in", []]], field_info) == [
        {"TEXT": ""}
    ]
    assert format_wheres(
        [[["Field1", "Field2"], "in", [["ABC", 1], ["DEF", 2], ["GHI", 3]]]], field_info
    ) == [
        {
            "TEXT": "((Field1 = 'ABC' AND Field2 = '1') OR (Field1 = 'DEF' AND Field2 = '2') "
        },
        {"TEXT": "OR (Field1 = 'GHI' AND Field2 = '3'))"},
    ]
    assert format_wheres([[["Field1", "Field2"], "not in", []]], field_info) == [
        {"TEXT": ""}
    ]
    assert format_wheres(
        [[["Field1", "Field2"], "not in", [["ABC", 1], ["DEF", 2], ["GHI", 3]]]],
        field_info,
    ) == [
        {
            "TEXT": "((Field1 <> 'ABC' OR Field2 <> '1') AND (Field1 <> 'DEF' OR Field2 <> "
        },
        {"TEXT": "'2') AND (Field1 <> 'GHI' OR Field2 <> '3'))"},
    ]
