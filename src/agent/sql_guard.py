"""Guard keamanan SQL: hanya izinkan SELECT read-only + paksa LIMIT."""

import sqlglot
from sqlglot import exp

DEFAULT_LIMIT = 1000

_FORBIDDEN = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Create,
    exp.Alter,
    exp.TruncateTable,
    exp.Grant,
    exp.Command,
    exp.Merge,
)


class UnsafeSQLError(ValueError):
    """Diangkat ketika SQL bukan query read-only yang aman."""


def sanitize_sql(
    raw_sql: str,
    dialect: str = "postgres",
    max_limit: int = DEFAULT_LIMIT,
) -> str:
    sql = raw_sql.strip().rstrip(";").strip()
    if not sql:
        raise UnsafeSQLError("SQL kosong.")

    statements = [s for s in sqlglot.parse(sql, read=dialect) if s is not None]
    if len(statements) != 1:
        raise UnsafeSQLError("Hanya boleh satu statement.")

    tree = statements[0]

    if not isinstance(tree, (exp.Select, exp.Subquery, exp.With)):
        raise UnsafeSQLError(
            f"Hanya SELECT yang diizinkan, dapat: {type(tree).__name__}"
        )

    bad = tree.find(*_FORBIDDEN)
    if bad is not None:
        raise UnsafeSQLError(
            f"Operasi terlarang terdeteksi: {type(bad).__name__}"
        )

    select_node = tree if isinstance(tree, exp.Select) else tree.find(exp.Select)
    if select_node is not None and select_node.args.get("limit") is None:
        select_node.limit(max_limit, copy=False)

    return tree.sql(dialect=dialect)