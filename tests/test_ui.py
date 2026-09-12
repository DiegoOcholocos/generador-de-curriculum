"""Browser-driven tests for behavior that only exists in the live DOM (badge
counters, the page-break indicator) and can't be exercised through the JSON
API alone. Spins up the real Flask app on a background thread and drives it
with a real Chromium instance via Playwright.
"""
import os
import sys
import threading

import pytest
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope='module')
def live_server(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp('ui_db')
    os.environ['CVWIZARD_DB_PATH'] = str(tmp_path / 'ui_test.db')

    import storage
    storage.DB_PATH = str(tmp_path / 'ui_test.db')
    storage.LEGACY_PROFILES_DIR = str(tmp_path / 'no_legacy')
    storage.init_db()

    import app as app_module
    server = make_server('127.0.0.1', 0, app_module.app)
    port = server.server_port
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    yield f'http://127.0.0.1:{port}/'
    server.shutdown()


@pytest.fixture(scope='module')
def browser():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def page(browser, live_server):
    p = browser.new_page()
    p.goto(live_server)
    p.wait_for_selector('#cv-wrap')
    yield p
    p.close()


PROFILE_MANY_SECTIONS = {
    'lang': 'es', 'template': 'moderna_roja', 'personal': {'name': 'Ana Torres'},
    'summary': '', 'experience': [
        {'position': f'Cargo {i}', 'company': f'Empresa {i}', 'start_date': '2015',
         'end_date': '2020', 'description': ''} for i in range(1, 7)
    ],
    'education': [{'degree': 'X', 'institution': 'Y', 'start_date': '', 'end_date': ''}],
    'skills': [], 'languages': [], 'courses': [], 'recommendations': [],
    'projects': [{'name': 'Proy 1', 'tech': '', 'link': '', 'description': ''}],
    'hobbies': '',
}


def test_section_badges_match_actual_item_counts(page):
    # Regression test: badges used to count the list *container* element too
    # (its id also matched the "exp-" prefix), showing one more than the
    # real number of entries; and a section loaded with zero items kept
    # showing whatever count was left over from before, since restoreData()
    # skipped it entirely for having nothing to add.
    page.evaluate('(d) => { restoreData(d); }', PROFILE_MANY_SECTIONS)
    page.wait_for_timeout(150)
    assert page.inner_text('#b-exp') == '6'
    assert page.inner_text('#b-edu') == '1'
    assert page.inner_text('#b-proj') == '1'
    assert page.inner_text('#b-sk') == '0'
    assert page.inner_text('#b-lg') == '0'
    assert page.inner_text('#b-co') == '0'
    assert page.inner_text('#b-rec') == '0'


def test_page_break_indicator_reflects_content_length(page):
    short_profile = dict(PROFILE_MANY_SECTIONS, experience=[], education=[], projects=[])
    page.evaluate('(d) => { restoreData(d); }', short_profile)
    page.wait_for_timeout(150)
    assert page.inner_text('#page-badge') == '1 página'
    assert page.eval_on_selector_all('.page-break-guide', 'els => els.length') == 0

    long_profile = dict(PROFILE_MANY_SECTIONS, experience=[
        {'position': f'Cargo {i}', 'company': f'Empresa {i}', 'start_date': '2015',
         'end_date': '2020', 'description': 'Responsabilidad muy larga. ' * 25}
        for i in range(1, 7)
    ])
    page.evaluate('(d) => { restoreData(d); }', long_profile)
    page.wait_for_timeout(150)
    assert page.inner_text('#page-badge') != '1 página'
    assert page.eval_on_selector('#page-badge', 'el => el.classList.contains("warn")')
    assert page.eval_on_selector_all('.page-break-guide', 'els => els.length') >= 1
