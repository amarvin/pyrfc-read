import logging
import textwrap
from collections.abc import Iterable

logger = logging.getLogger(__name__)


def field_value(value, field_type: str):
    """Convert value from a field to the proper Python type, given its field_type

    Args:
        value: Value to convert
        field_type: Field type

    Returns:
        Converted value
    """

    match field_type:
        case "I":
            return int(value)
        case "F" | "P":
            try:
                return float(value)
            except ValueError:
                return value
        case "C":
            return value.rstrip()


def format_fields(fields) -> list[dict[str, str]]:
    """Format fields into SAP Query format

    Args:
        fields: String or Iterable of field(s) to format

    Returns:
        Formatted fields as list of dict['FIELDNAME', str]
    """

    if not fields or fields == "*":
        fields = ""
    elif isinstance(fields, str):
        fields = [{"FIELDNAME": fields}]
    elif isinstance(fields, Iterable):
        fields = [
            field if isinstance(field, dict) else {"FIELDNAME": field}
            for field in fields
        ]
    else:
        raise ValueError(f"Improper 'fields' format: {fields}")

    return fields


def format_value(value, field_type: str, field_length: int) -> str:
    """Format field value into SAP Query format

    Args:
        value: Value to format
        field_type: Field datatype
            (e.g. 'C' for character string, 'I' for integer, 'F' for floating point number)
        field_length: Field length

    Returns:
        Formatted value
    """

    if field_type == "C":
        try:
            try:
                value = int(value)
            except ValueError:
                value = float(value)
            # value look numeric, so left-pad it with zeroes
            value = str(value).zfill(field_length)
        except ValueError:
            # value doesn't look numeric
            pass

    # enclose in quotes
    value = f"'{value}'"

    return value


def format_wheres(
    wheres, field_info: dict[str, dict[str, str]]
) -> list[dict[str, str]]:
    """Format wheres into SAP Query format

    Args:
        wheres: Where(s) to format
        field_info: Info for each field in the table (use `field_info()` to get this)

    Returns:
        Formatted wheres as list of dict['TEXT', str]
    """

    if not wheres:
        return [{"TEXT": ""}]
    elif isinstance(wheres, str):
        options = wheres
    elif isinstance(wheres, (list, set)):
        options = ""
        for where in wheres:
            if len(options) > 0:
                options += " AND "
            if isinstance(where, str):
                options += where
            elif isinstance(where, list):
                if len(where) == 1 and isinstance(where[0], str):
                    options += where[0]
                elif len(where) == 3:
                    if all(isinstance(where[i], str) for i in range(3)):
                        options += " ".join(where)
                    elif (
                        all(isinstance(where[i], str) for i in range(2))
                        and where[1].lower() in ("in", "not in")
                        and isinstance(where[2], Iterable)
                    ):
                        # This field considers a list
                        if len(where[2]) == 0:
                            logger.warning(
                                f"Ignoring 'wheres' with empty list: {where}"
                            )
                            if len(wheres) == 1:
                                return [{"TEXT": ""}]
                            continue
                        # Find the field format
                        field = where[0]
                        field_type = field_info[field]["INTTYPE"]
                        field_length = int(field_info[field]["LENG"])
                        if where[1].lower() == "in":
                            # Field must be in list
                            for n, item in enumerate(where[2]):
                                item_str = format_value(item, field_type, field_length)
                                if n == 0:
                                    options += f"({field} = {item_str}"
                                else:
                                    options += f" OR {field} = {item_str}"
                        else:
                            # Field must not be in list
                            for n, item in enumerate(where[2]):
                                item_str = format_value(item, field_type, field_length)
                                if n == 0:
                                    options += f"({field} <> {item_str}"
                                else:
                                    options += f" AND {field} <> {item_str}"
                        options += ")"
                    elif (
                        isinstance(where[0], Iterable)
                        and all(isinstance(i, str) for i in where[0])
                        and where[1].lower() in ("in", "not in")
                        and isinstance(where[2], Iterable)
                    ):
                        # This list of fields must be within allowed combinations (a list of tuples)
                        if len(where[2]) == 0:
                            logger.warning(
                                f"Ignoring 'wheres' with empty list: {where}"
                            )
                            if len(wheres) == 1:
                                return [{"TEXT": ""}]
                            continue
                        # Find the fields format
                        fields = where[0]
                        fields_type = {
                            field: field_info[field]["INTTYPE"] for field in fields
                        }
                        fields_length = {
                            field: int(field_info[field]["LENG"]) for field in fields
                        }
                        if where[1].lower() == "in":
                            # Fields must be in list
                            for n, items in enumerate(where[2]):
                                if n == 0:
                                    options += "("
                                else:
                                    options += " OR "
                                for n_field, field in enumerate(where[0]):
                                    item = items[n_field]
                                    field_type = fields_type[field]
                                    field_length = fields_length[field]
                                    item_str = format_value(
                                        item, field_type, field_length
                                    )
                                    if n_field == 0:
                                        options += f"({field} = {item_str}"
                                    else:
                                        options += f" AND {field} = {item_str}"
                                options += ")"
                        else:
                            # Fields must not be in list
                            for n, items in enumerate(where[2]):
                                if n == 0:
                                    options += "("
                                else:
                                    options += " AND "
                                for n_field, field in enumerate(where[0]):
                                    item = items[n_field]
                                    field_type = fields_type[field]
                                    field_length = fields_length[field]
                                    item_str = format_value(
                                        item, field_type, field_length
                                    )
                                    if n_field == 0:
                                        options += f"({field} <> {item_str}"
                                    else:
                                        options += f" OR {field} <> {item_str}"
                                options += ")"
                        options += ")"
                    else:
                        raise ValueError(f"Improper 'wheres' format: {where}")
                else:
                    raise ValueError(f"Improper 'wheres' format: {where}")
            else:
                raise ValueError(f"Improper 'wheres' format: {where}")
    else:
        raise ValueError(f"Improper 'wheres' format: {wheres}")

    # Split where clauses into max 72-character lines
    wheres = [
        {"TEXT": line} for line in textwrap.wrap(options, 72, drop_whitespace=False)
    ]

    return wheres
