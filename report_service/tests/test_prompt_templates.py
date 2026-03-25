from app.prompt_templates import SQL_PROMPT_TEMPLATE, HTML_PROMPT_TEMPLATE


def test_sql_prompt_has_placeholders():
    out = SQL_PROMPT_TEMPLATE.format(template_html="<div></div>", db_schema="{}", report_request="abc")
    assert "<div></div>" in out
    assert "abc" in out


def test_html_prompt_has_placeholders():
    out = HTML_PROMPT_TEMPLATE.format(template_html="<table></table>", query_rows_json="[]", function_catalog="[]")
    assert "<table></table>" in out
    assert "[]" in out
