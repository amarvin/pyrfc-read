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

    # Read table data, only for select fields, matching where conditions
    fields = [
        "BUKRS",  # Company code
        "BUTXT",  # Name of company
    ]
    wheres = [
        "MANDT = 100",  # Client 100
        ["BUKRS", "in", ["0001", "0002", "0003"]],  # Only company codes 1, 2 and 3
    ]
    data = conn.query(
        table,
        fields,  # optional, but requesting less fields reduces load on SAP
        wheres,  # optional
        field_info=field_info,  # optional, but makes it faster if you already it
        batch_rows=1000,  # optional, handles batching rows to not exceed SAP's output limit
        chunk_rows=100,  # optional, handles chunking long wheres conditions to not exceed SAP's input limit
    )
