from app.html_guard import HtmlPostCheckError, auto_patch_html, validate_generated_html

TEMPLATE = """
<html><body>
<table><thead><tr><th>Название</th><th>Сумма</th><th>Подпись</th></tr></thead>
<tbody>
<tr><td>______</td><td></td><td>_________</td></tr>
</tbody></table>
</body></html>
"""

GOOD_HTML = """
<html><body>
<table><thead><tr><th>Название</th><th>Сумма</th><th>Подпись</th></tr></thead>
<tbody>
<tr><td>{{road_name}}</td><td>{{sum(total_amount)}}</td><td>{{if(count(roads)>0,'Да','Нет')}}</td></tr>
</tbody></table>
</body></html>
"""

BAD_HTML_UNDERSCORES = """
<html><body><table><tbody><tr><td>_____</td></tr></tbody></table></body></html>
"""

ROWSPAN_TEMPLATE = """
<html><body>
<div class="line">{{owner_name}}</div>
<span class="inline-line">{{total_length_km}}</span>
<table>
  <thead>
    <tr><th rowspan="2">Дорога</th><th colspan="2">Показатели</th></tr>
    <tr><th>ДТП</th><th>Ранено</th></tr>
  </thead>
  <tbody>
    <tr><td>_____</td><td></td><td></td></tr>
  </tbody>
</table>
<span class="total-line">{{sum(accident_count)}}</span>
</body></html>
"""

BROKEN_ROWSPAN_HTML = """
<html><body>
<div class="line"></div>
<span class="inline-line"></span>
<table>
  <tr><th>Дорога</th><th>ДТП</th><th>Ранено</th></tr>
  <tr><td>{road_name}</td><td>{accident_count}</td><td>{injured_count}</td></tr>
</table>
<span class="total-line"></span>
</body></html>
"""


def test_html_guard_ok():
    out = validate_generated_html(TEMPLATE, GOOD_HTML)
    assert "{{" in out


def test_html_guard_fails_on_underscores():
    try:
        validate_generated_html(TEMPLATE, BAD_HTML_UNDERSCORES)
        assert False, "must raise"
    except HtmlPostCheckError:
        assert True


def test_auto_patch_recovers_template_structure_and_special_fields():
    patched = auto_patch_html(
        ROWSPAN_TEMPLATE,
        BROKEN_ROWSPAN_HTML,
        row_keys=["road_name", "accident_count", "injured_count", "owner_name", "total_length_km"],
    )

    out = validate_generated_html(ROWSPAN_TEMPLATE, patched)
    assert out.count("rowspan=") >= 1
    assert out.count("colspan=") >= 1
    assert "{{owner_name}}" in out
    assert "{{total_length_km}}" in out
    assert "{{road_name}}" in out
    assert "{{accident_count}}" in out
    assert "{{sum(accident_count)}}" in out
