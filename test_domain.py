"""Unit tests for each public pure business rule, using fixed expected results."""
from datetime import datetime, timedelta, timezone
import pytest
from domain import build_space_query, parse_filters, report_view, validate_report_fields

pytestmark = pytest.mark.unit


@pytest.mark.parametrize('query,expected', [('', ''), ('  library  ', 'library'), ('x'*119, 'x'*119), ('x'*120, 'x'*120), ('x'*121, 'x'*120)])
def test_search_whitespace_and_length_boundary(query, expected):
    assert parse_filters(query, '', '', '')['q'] == expected


@pytest.mark.parametrize('study,outlets,atmosphere', [('individual', '', ''), ('group', 'yes', 'quiet'), ('', 'yes', ''), ('', '', 'quiet')])
def test_allowed_filter_categories(study, outlets, atmosphere):
    assert parse_filters('', study, outlets, atmosphere) == {'q':'', 'study':study, 'outlets':outlets, 'atmosphere':atmosphere}


@pytest.mark.parametrize('study,outlets,atmosphere', [('invalid','',''), ('','no',''), ('','','loud')])
def test_invalid_filter_categories_raise_value_error(study, outlets, atmosphere):
    with pytest.raises(ValueError, match='available filters'):
        parse_filters('', study, outlets, atmosphere)


def test_search_query_parameters_are_separate_from_sql():
    raw = "x' OR 1=1 --"
    sql, args = build_space_query(parse_filters(raw, 'group', 'yes', 'quiet'))
    assert raw not in sql
    assert args == ["%x' OR 1=1 --%", 'group']
    assert 'name LIKE ?' in sql
    assert "study_type IN (?, 'both')" in sql
    assert 'outlets = 1' in sql and "atmosphere = 'quiet'" in sql
    assert sql.endswith('ORDER BY name')


@pytest.mark.parametrize('query,expected', [('%', '%\\%%'), ('_', '%\\_%'), ('\\', '%\\\\%')])
def test_search_special_characters_are_literal(query, expected):
    _, args = build_space_query(parse_filters(query, '', '', ''))
    assert args == [expected]


def test_no_filters_returns_all_spaces_sorted_by_name():
    sql, args = build_space_query(parse_filters('', '', '', ''))
    assert sql == 'SELECT * FROM study_spaces ORDER BY name'
    assert args == []


@pytest.mark.parametrize('crowd', ['low','medium','high'])
@pytest.mark.parametrize('noise', ['quiet','moderate','loud'])
def test_all_report_categories_are_accepted(crowd, noise):
    assert validate_report_fields(crowd, noise) == (crowd, noise)


@pytest.mark.parametrize('crowd,noise', [(None,'quiet'), ('low',None), ('','quiet'), ('low',''), ('invalid','quiet'), ('low','invalid')])
def test_missing_or_invalid_report_fields_are_rejected(crowd, noise):
    with pytest.raises(ValueError, match='crowd level and a noise level'):
        validate_report_fields(crowd, noise)


@pytest.mark.parametrize('seconds,age,stale', [(-60,'Just now',False), (0,'Just now',False), (59,'Just now',False), (60,'1 min ago',False), (3599,'59 min ago',False), (3600,'1 hours ago',True), (3660,'1 hours ago',True), (86340,'23 hours ago',True), (86400,'1 days ago',True), (86460,'1 days ago',True)])
def test_report_age_and_stale_boundaries(seconds, age, stale):
    now=datetime(2026,10,13,18,0,tzinfo=timezone.utc)
    posted=now-timedelta(seconds=seconds)
    row={'id':1,'crowd':'low','noise':'quiet','created_at':posted.isoformat()}
    result=report_view(row,now)
    assert result is not None
    assert result['age'] == age
    assert result['stale'] is stale
    assert result['crowd_label'] == 'Not busy' and result['noise_label'] == 'Quiet'
    assert result['display_time'] == posted.strftime('%Y-%m-%d %H:%M UTC')
    assert result['id'] == 1
    assert row == {'id':1,'crowd':'low','noise':'quiet','created_at':posted.isoformat()}


@pytest.mark.parametrize('row', [None, {}])
def test_no_report_returns_none(row):
    assert report_view(row,datetime(2026,10,13,tzinfo=timezone.utc)) is None
