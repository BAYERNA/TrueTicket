import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from streamlit.testing.v1 import AppTest


class IntegratedReview(unittest.TestCase):
    def test_opt_in_and_retry_in_the_original_viewer(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
        workspace = str(uuid4())
        app.query_params["w"] = workspace
        app.run()
        def submit():
            next(b for b in app.button if b.label == "선택 근거로 검토 접수").click().run()
        with patch("src.review_request.send", return_value="TG-demo-receipt") as sender:
            submit()
            self.assertFalse(sender.called)
            next(c for c in app.checkbox if c.label.startswith("가상 한빛 운영팀")).check().run()
            submit()
            submit()
            self.assertEqual(sender.call_count, 2)
            self.assertEqual(sender.call_args_list[0], sender.call_args_list[1])
            self.assertEqual(sender.call_args.args[0], workspace)
            self.assertEqual(sender.call_args.args[2], [0, 1, 2])
            self.assertIn("TG-demo-receipt", app.success[0].value)
            self.assertFalse(app.exception)
