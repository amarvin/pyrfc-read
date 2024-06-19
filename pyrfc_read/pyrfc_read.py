import logging
from collections.abc import Iterable

import pyrfc

from pyrfc_read.utils import field_value, format_fields, format_wheres

logger = logging.getLogger(__name__)


class Connection(pyrfc.Connection):
    def query(
        self,
        table: str,
        fields: None | list[str] = None,
        wheres=None,
        max_rows: int = 50,
        from_row: int = 0,
        field_info: None | bool | dict[str, dict[str, str]] = None,
        delimiter: str = "⁂",
        batch_rows: None | int = None,
        chunk_rows: int = 10000,
        make_unique: bool = True,
    ) -> list[list]:
        """Query table data from SAP R/3 System

        Args:
            table: Table to query
            fields: Fields to query
            wheres: Where condition(s) for query
            max_rows: Maximum number of rows to return
            from_row: Starting row
            field_info: Metadata for each field in the table (None to query field_info, False to not)
            delimiter: Delimiter character used in data transfers
            batch_rows: Number of rows to query at a time
            chunk_rows: Query data in chuncks of this size, if wheres have many entries
            make_unique: Convert wheres to unique values

        Returns:
            List of list, with data from table
        """

        # Convert all wheres to unique values
        if make_unique and wheres is not None:
            wheres_with_arrays = (
                i
                for i, where in enumerate(wheres)
                if isinstance(where, list)
                if len(where) == 3
                if isinstance(where[0], str)
                if where[1].lower() in ("in", "not in")
                if not isinstance(where[2], str)
                if isinstance(where[2], Iterable)
            )
            for i in wheres_with_arrays:
                # Reduce array to unique values
                uniques = set()
                wheres[i][2] = [
                    x
                    for x in wheres[i][2]
                    if x not in uniques and (uniques.add(x) or True)
                ]
            return self.query(
                table,
                fields,
                wheres,
                max_rows,
                from_row,
                field_info,
                delimiter,
                batch_rows,
                chunk_rows,
                make_unique=False,
            )

        # Get field metadata
        if field_info is None:
            field_info = self.field_info(table)

        # Convert inputs to SAP Query format
        fields = format_fields(fields)

        # Detect if chinking wheres is needed
        chunk_field = None
        if wheres is not None:
            for where in wheres:
                if (
                    isinstance(where, list)
                    and len(where) == 3
                    and isinstance(where[0], str)
                    and where[1].lower() == "in"
                    and not isinstance(where[2], str)
                    and isinstance(where[2], Iterable)
                ):
                    chunk_list = where[2]
                    if len(chunk_list) > chunk_rows:
                        # This field needs chunking
                        chunk_field = where[0]

                        # Remove this where
                        wheres.remove(where)

                        break

        # Query data
        if not chunk_field:
            if not batch_rows:
                data = self._query(
                    table, fields, wheres, max_rows, from_row, field_info, delimiter
                )
            else:
                # Batch queries
                data = []
                max_rows_batch = min(max_rows, batch_rows) if max_rows else batch_rows
                last_data = self._query(
                    table,
                    fields,
                    wheres,
                    max_rows_batch,
                    from_row,
                    field_info,
                    delimiter,
                )
                data.extend(last_data)

                # Query more data, if needed
                last_row = max_rows_batch + from_row
                while len(last_data) == max_rows_batch and (
                    not max_rows or last_row < max_rows
                ):
                    # Query more data
                    last_data = self._query(
                        table,
                        fields,
                        wheres,
                        max_rows_batch,
                        last_row,
                        field_info,
                        delimiter,
                    )
                    data.extend(last_data)
                    last_row += max_rows_batch
        else:
            # Chunk queries
            data = []
            for i in range(0, len(chunk_list), chunk_rows):
                chunk = chunk_list[i : i + chunk_rows]
                new_wheres = wheres + [[chunk_field, "in", chunk]]
                if not batch_rows:
                    last_data = self.query(
                        table,
                        fields,
                        new_wheres,
                        max_rows,
                        from_row,
                        field_info,
                        delimiter,
                        batch_rows,
                        chunk_rows,
                    )
                    data.extend(last_data)
                else:
                    # Batch queries
                    max_rows_batch = (
                        min(max_rows, batch_rows) if max_rows else batch_rows
                    )
                    last_data = self.query(
                        table,
                        fields,
                        new_wheres,
                        max_rows_batch,
                        from_row,
                        field_info,
                        delimiter,
                        batch_rows,
                        chunk_rows,
                    )
                    data.extend(last_data)

                    # Query more data, if needed
                    last_row = max_rows_batch + from_row
                    while len(last_data) == max_rows_batch and (
                        not max_rows or last_row < max_rows
                    ):
                        # Query more data
                        last_data = self.query(
                            table,
                            fields,
                            new_wheres,
                            max_rows_batch,
                            last_row,
                            field_info,
                            delimiter,
                            batch_rows,
                            chunk_rows,
                        )
                        data.extend(last_data)
                        last_row += max_rows_batch

        # Return results
        return data

    def _query(
        self,
        table: str,
        fields: None | list[str],
        wheres,
        max_rows: int,
        from_row: int,
        field_info: None | dict[str, dict[str, str]],
        delimiter: str,
    ) -> list[list]:
        """Low-level query function

        Args:
            table: Table to query
            fields: Fields to query
            wheres: Where condition(s) for query
            max_rows: Maximum number of rows to return
            from_row: Starting row
            field_info: Metadata for each field in the table
            delimiter: Delimiter character used in data transfers

        Returns:
            Query results

        See Also:
            query
        """

        # Convert inputs to SAP Query format
        options = format_wheres(wheres, field_info)

        # Execute query
        # TODO: check if user has access to RFC "/BODS/RFC_READ_TABLE" or "/BODS/RFC_READ_TABLE2"
        RFCs = [
            "BBP_RFC__READ_TABLE",
            "RFC_READ_TABLE",
        ]
        rfc = RFCs[0]
        kwargs = dict(
            QUERY_TABLE=table,
            DELIMITER=delimiter,
            ROWCOUNT=max_rows,
            ROWSKIPS=from_row,
        )
        if fields:
            kwargs["FIELDS"] = fields
        if options:
            kwargs["OPTIONS"] = options
        result = self.call(rfc, **kwargs)
        logger.info(f"Ran {rfc}")

        # Parse results
        data = []
        for line in result["DATA"]:
            raw_data = line["WA"].strip().split(delimiter)
            data.append(
                [
                    field_value(value, result["FIELDS"][i]["TYPE"])
                    for i, value in enumerate(raw_data)
                ]
            )

        """data = [
            [
                field_value(value, result["FIELDS"][i]["TYPE"])
                for i, value in enumerate(line["WA"].strip().split(delimiter))
            ]
            for line in result["DATA"]
        ]"""
        """data = map(
            lambda line: [
                field_value(value, result["FIELDS"][i]["TYPE"])
                for i, value in enumerate(line["WA"].strip().split(delimiter))
            ],
            result["DATA"],
        )"""

        # Return results
        return data

    def number_entries(self, table: str) -> int:
        """Get number of entries in table

        Args:
            table: Table to query

        Returns:
            Number of entries in table
        """

        # Method 1
        # This actually reads the whole table into memory within SAP R/3!
        # result = self.call("RFC_GET_TABLE_ENTRIES", TABLE_NAME=table, MAX_ENTRIES=1)
        # logger.info("Ran RFC_GET_TABLE_ENTRIES")
        # entries = result["NUMBER_OF_ENTRIES"]

        # Method 2
        # Access often restricted to this RFC
        # result = self.call("EM_GET_NUMBER_OF_ENTRIES", IT_TABLES=[{"TABNAME": table}])
        # logger.info("Ran EM_GET_NUMBER_OF_ENTRIES")
        # entries = result["IT_TABLES"][0]["TABROWS"]

        # Method 3
        field_info = self.field_info(table)
        shortest_field = min(field_info, key=lambda field: field_info[field]["LENG"])
        data = self.query(table, shortest_field, max_rows=0)
        entries = len(data)

        return entries

    def table_description(self, table: str, language: str = "E") -> str:
        """Get table description

        Args:
            table: Table to query
            language: Language code

        Returns:
            Table description
        """

        fields = [
            "DDTEXT",  # short description
        ]
        wheres = [
            f"TABNAME = '{table}'",
            f"DDLANGUAGE = '{language}'",  # desired language
            "AS4LOCAL = 'A'",  # only active descriptions
        ]
        data = self.query("DD02T", fields, wheres, max_rows=0, field_info=False)
        if data:
            description = data[-1][0]
        else:
            description = None

        return description

    def find_tables_by_description(
        self, description: str, language: str = "E"
    ) -> list[list[str]]:
        """Find tables by description

        Args:
            description: Description to search for (% as wildcard)
            language: Language code

        Returns:
            List of tables and their descriptions
        """

        fields = [
            "TABNAME",  # table name
            "DDTEXT",  # short description
        ]
        wheres = [
            f"DDTEXT LIKE '{description}'",
            f"DDLANGUAGE = '{language}'",  # desired language
            "AS4LOCAL = 'A'",  # only active descriptions
        ]
        data = self.query("DD02T", fields, wheres, max_rows=0, field_info=False)

        return data

    def field_info(
        self, table: str, descriptions: bool = False, language: str = "E"
    ) -> dict[str, dict[str, str]]:
        """Get field information

        Args:
            table: Table to query
            descriptions: Include field text descriptions?
            language: Language code

        Returns:
            Field information
        """

        # Query basic field information
        fields = [
            "FIELDNAME",  # field name
            "KEYFLAG",  # key flag
            "ROLLNAME",  # data element (for getting field text from DD04T)
            "INTTYPE",  # ABAP data type
            "DATATYPE",  # data type
            "LENG",  # field length
            "POSITION",  # position in table
        ]
        wheres = [
            f"TABNAME = '{table}'",
            "AS4LOCAL = 'A'",  # only active descriptions
            "INTTYPE <> ''",  # has a data type
        ]
        data = self.query("DD03L", fields, wheres, max_rows=0, field_info=False)
        results = {
            row[0]: {fields[i]: row[1] for i in range(1, len(fields))} for row in data
        }

        if descriptions is True:
            # Query field text descriptions
            roll_index = fields.index("ROLLNAME")
            rollnames = [row[roll_index] for row in data]
            fields = [
                "ROLLNAME",  # data element
                "DDTEXT",  # short description
                "REPTEXT",  # heading
                "SCRTEXT_S",  # short field label
                "SCRTEXT_M",  # medium field label
                "SCRTEXT_L",  # long field label
            ]
            wheres = [
                ["ROLLNAME", "in", rollnames],
                f"DDLANGUAGE = '{language}'",  # desired language
                "AS4LOCAL = 'A'",  # only active descriptions
            ]
            field_info = {"ROLLNAME": {"LENG": 30, "INTTYPE": "C"}}
            data = self.query(
                "DD04T", fields, wheres, max_rows=0, field_info=field_info
            )
            roll_descriptions = {
                row[0]: {fields[i]: row[i] for i in range(1, len(fields))}
                for row in data
            }
            for field, info in results.items():
                roll = info["ROLLNAME"]
                if roll in roll_descriptions:
                    for key, value in roll_descriptions[roll].items():
                        results[field][key] = value
                del results[fields]["ROLLNAME"]

        return results

    def echo(self, message: str = "Hello world!"):
        """Echo a message

        Args:
            message: Message to echo

        Returns:
            Response from SAP R/3 System
        """
        response = self.call("STFC_CONNECTION", REQUTEXT=message)

        return response
