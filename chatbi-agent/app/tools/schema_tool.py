from app.core.database import get_connection


def get_schema():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name NOT LIKE 'sqlite_%';
    """)
    tables = [row["name"] for row in cur.fetchall()]

    schema = {}

    for table in tables:
        cur.execute(f"PRAGMA table_info({table});")
        columns = cur.fetchall()

        cur.execute(f"PRAGMA foreign_key_list({table});")
        foreign_keys = cur.fetchall()

        schema[table] = {
            "columns": [
                {
                    "cid": col["cid"],
                    "name": col["name"],
                    "type": col["type"],
                    "notnull": col["notnull"],
                    "default_value": col["dflt_value"],
                    "pk": col["pk"],
                }
                for col in columns
            ],
            "foreign_keys": [
                {
                    "from": fk["from"],
                    "to": fk["to"],
                    "table": fk["table"],
                }
                for fk in foreign_keys
            ],
        }

    conn.close()
    return schema


def get_schema_text():
    schema = get_schema()
    lines = []

    for table, info in schema.items():
        lines.append(f"Table: {table}")
        for col in info["columns"]:
            pk_mark = " [PK]" if col["pk"] else ""
            lines.append(f"  - {col['name']} ({col['type']}){pk_mark}")

        if info["foreign_keys"]:
            lines.append("  Foreign Keys:")
            for fk in info["foreign_keys"]:
                lines.append(f"    - {fk['from']} -> {fk['table']}.{fk['to']}")
        lines.append("")

    return "\n".join(lines)
