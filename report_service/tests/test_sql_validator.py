import re
from app.sql_validator import SafeSqlValidator, SqlValidationError
from app.dto import DbSchema, TableSchema, ColumnSchema


def test_sql_validator_allows_select():
    schema = DbSchema(tables=[TableSchema(name="roads", columns=[ColumnSchema(name="id", type="int")])])
    v = SafeSqlValidator(schema)
    assert v.validate("SELECT 1") == "SELECT 1"


def test_sql_validator_blocks_dml():
    schema = DbSchema(tables=[TableSchema(name="roads", columns=[ColumnSchema(name="id", type="int")])])
    v = SafeSqlValidator(schema)
    try:
        v.validate("DELETE FROM roads")
        assert False, "must raise"
    except SqlValidationError as e:
        assert "Запрещённое" in str(e)


def test_sql_validator_restricts_tables():
    schema = DbSchema(tables=[TableSchema(name="roads", columns=[ColumnSchema(name="id", type="int")])])
    v = SafeSqlValidator(schema)
    try:
        v.validate("SELECT * FROM hacks")
        assert False, "must raise"
    except SqlValidationError as e:
        assert "Таблица не разрешена" in str(e)
