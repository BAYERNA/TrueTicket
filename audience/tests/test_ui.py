import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import streamlit as st
from src.reporting import NOTICE, REPORTING_URL, SECTIONS
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


class UserJourneys(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        env = patch.dict(
            os.environ,
            {"TICKETGUARD_DB_PATH": str(Path(folder.name) / "catalog.db"), "OPENAI_API_KEY": ""},
        )
        env.start()
        self.addCleanup(env.stop)
        self.app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=6).run()

    def run_sample(self, label, category, level, marker):
        app = self.app
        if category != app.radio[0].value:
            app.radio[0].set_value(category).run()
        app.selectbox[0].set_value(label).run()
        app.checkbox[0].check().run()
        emitted = []
        real_download = st.download_button

        def capture(label, data, **kwargs):
            emitted.append(data.decode("utf-8"))
            return real_download(label, data, **kwargs)

        with patch.object(st, "download_button", side_effect=capture):
            app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertEqual(app.session_state["report"]["level"], level)
        self.assertIn(marker, emitted[-1])
        self.assertIn(NOTICE, emitted[-1])
        for _, title in SECTIONS:
            self.assertIn(f"[{title}]", emitted[-1])
        self.assertTrue(app.get("download_button")[0].proto.url)
        self.assertEqual(app.get("link_button")[0].proto.url, REPORTING_URL)

    def test_festival_ui_to_download(self):
        self.run_sample("페스티벌 · 고가 제시", "공연", "CAUTION", "+150.0%")

    def test_musical_ui_to_download(self):
        self.run_sample("뮤지컬 · 정가와 입장 조건", "공연", "CAUTION", "캡처")

    def test_baseball_ui_to_download(self):
        self.run_sample("프로야구 · 공식 선물하기", "스포츠", "REVIEW", "선물하기")

    def test_changed_input_clears_last_result(self):
        app = self.app
        self.run_sample("페스티벌 · 고가 제시", "공연", "CAUTION", "+150.0%")
        app.text_area[0].set_value("수정된 가상 글").run()
        self.assertFalse(app.get("download_button"))
        app.button[0].click().run()
        self.assertTrue(app.error)
        self.assertFalse(app.get("download_button"))
        self.assertFalse(app.exception)

    def test_key_and_consent_errors(self):
        app = self.app
        app.button[0].click().run()
        self.assertIn("확인란", app.error[0].value)
        app.checkbox[0].check().run()
        app.checkbox[1].check().run()
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertIn("키가 설정되지", app.error[0].value)
        self.assertFalse(app.get("download_button"))
