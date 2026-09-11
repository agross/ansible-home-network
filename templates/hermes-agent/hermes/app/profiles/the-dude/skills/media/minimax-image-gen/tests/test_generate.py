import base64
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).parents[1] / "scripts" / "generate.py"
SPEC = importlib.util.spec_from_file_location("minimax_generate", SCRIPT)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class FakeOpener:
    def __init__(self, body):
        self.body = body

    def open(self, request, timeout):
        return io.BytesIO(json.dumps(self.body).encode("utf-8"))


class GenerateTests(unittest.TestCase):
    def test_payload_uses_documented_defaults(self):
        args = module.parser().parse_args([
            "--prompt", "A fox", "--output-dir", "outputs",
        ])
        self.assertEqual(module.payload(args), {
            "model": "image-01",
            "prompt": "A fox",
            "n": 1,
            "response_format": "base64",
            "prompt_optimizer": False,
            "aspect_ratio": "1:1",
        })

    def test_api_error_has_status_message_and_trace_id(self):
        error = module.api_error({
            "base_resp": {"status_code": 1008, "status_msg": "insufficient balance"},
            "id": "trace-123",
        })
        self.assertIn("status_code=1008", str(error))
        self.assertIn("status_msg='insufficient balance'", str(error))
        self.assertIn("trace_id='trace-123'", str(error))

    def test_generate_reports_previously_saved_paths_on_later_bad_image(self):
        valid_png = base64.b64encode(b"\x89PNG\r\n\x1a\nfirst").decode()
        response = {
            "base_resp": {"status_code": 0},
            "data": {"image_base64": [valid_png, base64.b64encode(b"not an image").decode()]},
            "metadata": {"failed_count": 0},
        }
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.object(module.urllib.request, "build_opener", return_value=FakeOpener(response)):
                with self.assertRaises(module.PartialResultError) as raised:
                    module.generate(
                        {"model": "image-01", "prompt": "x", "n": 2},
                        Path(directory), "secret", 30,
                    )
            error = raised.exception
            self.assertEqual(error.requested, 2)
            self.assertEqual(len(error.paths), 1)
            self.assertTrue(Path(error.paths[0]).is_file())
            self.assertIn("Unrecognized image format", str(error))

    def test_main_prints_partial_result_json(self):
        args = module.parser().parse_args(["--prompt", "x", "--output-dir", "outputs"])
        parser = mock.Mock()
        parser.parse_args.return_value = args
        stream = io.StringIO()
        error = module.PartialResultError("bad response", ["/tmp/one.png"], 2)
        with mock.patch.object(module, "parser", return_value=parser), \
             mock.patch.object(module, "generate", side_effect=error), \
             mock.patch.dict(module.os.environ, {"MINIMAX_API_KEY": "secret"}, clear=False), \
             mock.patch.object(module.sys, "stdout", stream):
            self.assertEqual(module.main(), 2)
        self.assertEqual(json.loads(stream.getvalue()), {
            "paths": ["/tmp/one.png"],
            "requested": 2,
            "received": 1,
            "partial": True,
            "error": "bad response",
        })


if __name__ == "__main__":
    unittest.main()
