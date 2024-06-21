# pyrfc-read

<p align="center">
    <em>Query table data from SAP R/3 Systems</em>
</p>

[![License](https://img.shields.io/github/license/amarvin/pyrfc-read)](https://github.com/amarvin/pyrfc-read/blob/main/LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![codecov](https://codecov.io/gh/amarvin/pyrfc-read/branch/main/graph/badge.svg)](https://codecov.io/gh/amarvin/pyrfc-read)

## Install

```
pip install pyrfc-read
```

### Prerequisites

SAP NW RFC SDK must be installed (https://support.sap.com/nwrfcsdk).

## Demo

```py
from pyrfc_read import Connection

# Define credentials to the SAP R/3 System
#  many combinations of key-values will work here, and these are just an example
#  https://help.sap.com/doc/saphelp_nw74/7.4.16/de-DE/48/b0ff6b792d356be10000000a421937/frameset.htm
credentials = dict(
    ashost="hostname",
    sysnr="system_number",
    client="client",
    user="user",
    passwd="password",
    lang="EN",
)

# Open connection to the SAP R/3 System
with Connection(**credentials) as conn:
    # Confirm connection active by having SAP echo a message
    message = "Hello world!"
    response = conn.echo(message)

    # Get number of entries in table
    table = "T001"
    entries = conn.number_entries(table)

    # Get table description
    #  in any supported language by SAP Language Code
    #  https://help.sap.com/doc/saphelp_nw73ehp1/7.31.19/en-US/c1/ae563cd2ad4f0ce10000000a11402f/content.htm?no_cache=true
    description = conn.table_description(table, language="E")

    # Search tables by description
    description = "data that I need"
    tables = conn.find_tables_by_description(description, language="E")

    # Get table metadata about its fields
    field_info = conn.field_info(table, descriptions=True, language="E")

    # Read table table, only for select fields, matching where conditions
    fields = [
        "BUKRS",  # Company code
        "BUTXT",  # Name of company
    ]
    wheres = [
        "MANDT = 100",  # Client 100
        ["BUKRS", "in", ["0001", "0002", "0003"]],  # Only company codes 1 and 2
    ]
    data = conn.query(
        table,
        fields,  # optional, but requesting less fields reduces load on SAP
        wheres,  # optional
        field_info=field_info,  # optional, but makes it faster if you already it
        batch_rows=1000,  # optional, handles batching rows to not exceed SAP's output limit
        chunk_rows=100,  # optional, handles chunking long wheres conditions to not exceed SAP's input limit
    )
```

## License

This project is licensed under the terms of the MIT license.
