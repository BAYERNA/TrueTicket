import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

from streamlit.testing.v1 import AppTest


class IntegratedReview(unittest.TestCase):
    def test_selected_evidence_and_retry_key_follow_guest_to_consent_form(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
        workspace = str(uuid4())
        app.query_params["w"] = workspace
        app.run()

        def next_link():
            return next(x.proto.url for x in app.get("link_button") if x.proto.label == "선택 근거 확인 및 접수")

        all_selected = urlsplit(next_link())
        self.assertEqual(parse_qs(all_selected.query)["w"], [workspace])
        self.assertEqual(parse_qs(all_selected.fragment)["e"], ["0,1,2"])
        app.run()
        self.assertEqual(urlsplit(next_link()), all_selected)
        app.multiselect[0].set_value(["추가금 장당 27,000원"]).run()
        one_selected = parse_qs(urlsplit(next_link()).fragment)
        self.assertEqual(one_selected["e"], ["1"])
        self.assertNotEqual(one_selected["k"], parse_qs(all_selected.fragment)["k"])
        app.multiselect[0].set_value([]).run()
        self.assertFalse(any(x.proto.label == "선택 근거 확인 및 접수" for x in app.get("link_button")))
        self.assertFalse(app.exception)
