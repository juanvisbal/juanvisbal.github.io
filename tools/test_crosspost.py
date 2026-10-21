"""Offline cross-post regression tests; never contact a network or publish a post."""
import contextlib
import datetime as dt
import email
import hashlib
import http.server
import io
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import threading
import unittest
from unittest import mock

import crosspost as c


class PostTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.enterContext(mock.patch.object(c, "DRY_RUN", False))

    def post(self, body="Hello world!", *, title="", date="2026-10-21T00:00:00Z", blocks="", name="post"):
        path = self.root / "2026" / f"{name}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'---\ndate: {date}\ntitle: "{title}"\nurl: /blog/{name}.html\n{blocks}---\n{body}\n')
        return c.Post(path)

    def client(self):
        client = object.__new__(c.DevNull)
        client.signature = mock.Mock(return_value="c2lnbmF0dXJl")
        client.request = mock.Mock(return_value="Committed: https://dev-null.sh/@juan/commits/abc-123\n")
        return client


class DevNullPostTests(PostTestCase):
    def test_plain_payload_and_front_matter(self):
        post = self.post("Hello [world](https://example.com) 👋")
        client = self.client()
        with mock.patch.object(c.time, "time", return_value=123), mock.patch.object(c.uuid, "uuid4") as nonce:
            nonce.return_value.hex = "a" * 32
            block = client.post(post, "https://juanvisbal.com")
        payload = ("123\n" + "a" * 32 + "\n\nHello world (https://example.com) 👋").encode()
        client.signature.assert_called_once_with(payload, "devnull-commit")
        client.request.assert_called_once_with(
            "/api/cli/commits", data=payload, timeout=60,
            headers={"Content-Type": "text/plain; charset=utf-8", "X-SSH-Signature": "c2lnbmF0dXJl"},
        )
        post.add_block(block)
        self.assertTrue(c.Post(post.path).has_block("devnull"))
        self.assertIn('id: "abc-123"', post.front)
        self.assertEqual(post.body, "Hello [world](https://example.com) 👋\n")

    def test_title_and_long_text(self):
        client = self.client()
        for title, body in (("A title", "Ignore this body"), ("", "x" * 5000), ("Y" * 5000, "body")):
            with self.subTest(title=title[:10]):
                post = self.post(body, title=title)
                client.post(post, "https://juanvisbal.com")
                text = client.signature.call_args.args[0].decode().split("\n", 3)[3]
                self.assertLessEqual(len(text), c.DEVNULL_LIMIT)
                self.assertTrue(text.endswith("https://juanvisbal.com/blog/post"))
                if title == "A title":
                    self.assertEqual(text, "A title\n\nhttps://juanvisbal.com/blog/post")
                else:
                    self.assertIn("…\n\n", text)

    def test_images_are_limited_and_hashes_cover_uploaded_bytes(self):
        post = self.post()
        images = [(pathlib.Path(f"{i}.gif"), "alt") for i in range(4)]
        client = self.client()
        with mock.patch.object(post, "images", return_value=images), mock.patch.object(c, "shrink") as shrink:
            shrink.side_effect = [(f"converted-{i}".encode(), "image/jpeg", (10, 10)) for i in range(3)]
            client.post(post, "https://juanvisbal.com")
        self.assertEqual(shrink.call_count, 3)
        shrink.assert_any_call(images[0][0], c.DEVNULL_IMAGE_MAX, formats=("JPEG", "PNG", "WEBP"))
        payload, namespace = client.signature.call_args.args
        self.assertEqual(namespace, "devnull-commit-images")
        signed_hashes = payload.decode().split("\n", 4)[3].split(",")
        call = client.request.call_args.kwargs
        message = email.message_from_bytes(
            f'Content-Type: {call["headers"]["Content-Type"]}\r\nMIME-Version: 1.0\r\n\r\n'.encode() + call["data"]
        )
        parts = {part.get_param("name", header="content-disposition"): part for part in message.get_payload()}
        self.assertEqual(parts["payload"].get_payload(decode=True), payload)
        self.assertEqual(set(parts), {"payload", "images[0]", "images[1]", "images[2]"})
        for i in range(3):
            raw = parts[f"images[{i}]"].get_payload(decode=True)
            self.assertEqual(signed_hashes[i], hashlib.sha256(raw).hexdigest())
        self.assertEqual(call["timeout"], 600)

    def test_image_only_post_has_link_as_required_text(self):
        post = self.post('![alt](/not-local.png)')
        client = self.client()
        client.post(post, "https://juanvisbal.com")
        self.assertTrue(client.signature.call_args.args[0].endswith(b"https://juanvisbal.com/blog/post"))

    def test_pending_review_is_recorded(self):
        client = self.client()
        client.request.return_value = "Committed: https://dev-null.sh/@juan/commits/abc-123 (pending review, only you can see it until it is approved)\n"
        self.assertIn('id: "abc-123"', client.post(self.post(), "https://juanvisbal.com"))

    def test_unexpected_response_is_not_recorded(self):
        client = self.client()
        for response in ("OK", "Committed: https://other.example/@juan/commits/abc-123\n"):
            with self.subTest(response=response), self.assertRaises(RuntimeError):
                client.request.return_value = response
                client.post(self.post(), "https://juanvisbal.com")

    def test_dry_run_does_not_sign_upload_post_or_write(self):
        post = self.post()
        before = post.path.read_bytes()
        client = self.client()
        with mock.patch.object(c, "DRY_RUN", True), mock.patch.object(c, "shrink") as shrink, contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertIsNone(client.post(post, "https://juanvisbal.com"))
        self.assertIn("/dev/null", output.getvalue())
        client.signature.assert_not_called()
        client.request.assert_not_called()
        shrink.assert_not_called()
        self.assertEqual(post.path.read_bytes(), before)


class DevNullLoginTests(PostTestCase):
    def test_key_lookup_sends_only_public_key_and_disables_redirects(self):
        key = self.root / "key.pub"
        key.write_text("ssh-ed25519 cHVibGlj comment\n")
        with mock.patch.object(c, "request", return_value=(200, "ssh-ed25519 cHVibGlj\n")) as request, mock.patch.object(c.DevNull, "signature") as signature:
            c.DevNull(str(key))
        request.assert_called_once_with(
            "POST", "https://dev-null.sh/api/cli/key-lookups", text_response=True, follow_redirects=False,
            data=b"ssh-ed25519 cHVibGlj\n", headers={"Content-Type": "text/plain; charset=utf-8"},
        )
        signature.assert_called_once_with(b"Cross-post signing check", "devnull-commit")

    def test_rejects_private_or_unrecognized_keys(self):
        key = self.root / "key.pub"
        key.write_text("-----BEGIN OPENSSH PRIVATE KEY-----\n")
        with mock.patch.object(c, "request") as request, self.assertRaises(ValueError):
            c.DevNull(str(key))
        request.assert_not_called()
        key.write_text("ssh-ed25519 cHVibGlj\n")
        with mock.patch.object(c, "request", return_value=(200, "ssh-ed25519 b3RoZXI=\n")), self.assertRaises(RuntimeError):
            c.DevNull(str(key))


class MainTests(PostTestCase):
    def run_main(self, *, enabled=True, failed=None, post_failed=None):
        env = {"BLUESKY_HANDLE": "test", "BLUESKY_APP_PASSWORD": "test", "MASTODON_INSTANCE": "example.com", "MASTODON_TOKEN": "test"}
        if enabled:
            env["DEVNULL_PUBLIC_KEY"] = "test.pub"
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.dict(os.environ, env, clear=True))
            stack.enter_context(mock.patch.object(c, "CONTENT", self.root))
            stack.enter_context(mock.patch.object(c, "DRY_RUN", False))
            # Keep these date-sensitive tests deterministic, including on the rollout day.
            clock = stack.enter_context(mock.patch.object(c.dt, "datetime", wraps=dt.datetime))
            clock.now.return_value = dt.datetime(2026, 10, 23, tzinfo=dt.timezone.utc)
            wait = stack.enter_context(mock.patch.object(c, "wait_until_live"))
            clients = {}
            for key, cls in (("bluesky", "Bluesky"), ("mastodon", "Mastodon"), ("devnull", "DevNull")):
                factory = stack.enter_context(mock.patch.object(c, cls))
                factory.__name__ = cls
                factory.return_value.post.return_value = f'{key}:\n  id: "copy"\n'
                if failed == key:
                    factory.side_effect = RuntimeError("offline")
                if post_failed == key:
                    factory.return_value.post.side_effect = RuntimeError("publish failed")
                clients[key] = factory
            output = stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            stack.enter_context(contextlib.redirect_stderr(io.StringIO()))
            try:
                c.main()
                code = 0
            except SystemExit as e:
                code = e.code
        return code, clients, wait, output.getvalue()

    def test_posts_to_missing_network_then_skips_on_rerun(self):
        post = self.post(blocks="bluesky:\n  id: b\nmastodon:\n  id: m\n")
        code, clients, _, _ = self.run_main()
        self.assertEqual(code, 0)
        clients["devnull"].return_value.post.assert_called_once()
        clients["bluesky"].assert_not_called()
        clients["mastodon"].assert_not_called()
        self.assertTrue(c.Post(post.path).has_block("devnull"))
        _, clients, wait, _ = self.run_main()
        for client in clients.values():
            client.assert_not_called()
        wait.assert_not_called()

    def test_no_backfill_but_old_posts_can_still_reach_other_networks(self):
        post = self.post(date="2026-10-09T12:00:00Z")
        code, clients, _, _ = self.run_main()
        self.assertEqual(code, 0)
        clients["devnull"].assert_not_called()
        self.assertTrue(c.Post(post.path).has_block("mastodon"))

    def test_no_key_disables_only_devnull(self):
        self.post()
        code, clients, _, output = self.run_main(enabled=False)
        self.assertEqual(code, 0)
        self.assertIn("/dev/null disabled", output)
        clients["devnull"].assert_not_called()
        clients["bluesky"].return_value.post.assert_called_once()
        clients["mastodon"].return_value.post.assert_called_once()

    def test_login_failure_is_isolated_and_successes_are_saved(self):
        post = self.post()
        code, clients, _, _ = self.run_main(failed="devnull")
        self.assertEqual(code, 1)
        saved = c.Post(post.path)
        self.assertTrue(saved.has_block("bluesky"))
        self.assertTrue(saved.has_block("mastodon"))
        self.assertFalse(saved.has_block("devnull"))
        code, clients, _, _ = self.run_main()
        self.assertEqual(code, 0)
        clients["bluesky"].assert_not_called()
        clients["mastodon"].assert_not_called()
        self.assertTrue(c.Post(post.path).has_block("devnull"))

    def test_post_failure_does_not_block_other_networks(self):
        post = self.post()
        code, clients, _, _ = self.run_main(post_failed="bluesky")
        self.assertEqual(code, 1)
        clients["devnull"].return_value.post.assert_called_once()
        saved = c.Post(post.path)
        self.assertFalse(saved.has_block("bluesky"))
        self.assertTrue(saved.has_block("mastodon"))
        self.assertTrue(saved.has_block("devnull"))

    def test_drafts_future_and_pre_import_posts_are_skipped(self):
        self.post(blocks="draft: true\n", name="draft")
        self.post(date="2099-10-21T00:00:00Z", name="future")
        self.post(date="2026-09-01T00:00:00Z", name="imported")
        code, clients, wait, _ = self.run_main()
        self.assertEqual(code, 0)
        for client in clients.values():
            client.assert_not_called()
        wait.assert_not_called()

    def test_check_login_checks_signing_without_publishing(self):
        env = {"CHECK_LOGIN": "1", "BLUESKY_HANDLE": "test", "BLUESKY_APP_PASSWORD": "test", "MASTODON_INSTANCE": "example.com", "MASTODON_TOKEN": "test", "DEVNULL_PUBLIC_KEY": "test.pub"}
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(c, "Bluesky") as bluesky, mock.patch.object(c, "Mastodon") as mastodon, mock.patch.object(c, "DevNull") as devnull, contextlib.redirect_stdout(io.StringIO()):
            c.main()
        devnull.assert_called_once_with("test.pub")
        for client in (bluesky, mastodon, devnull):
            client.return_value.post.assert_not_called()

    def test_actual_dry_run_previews_all_without_credentials_or_writes(self):
        post = self.post()
        before = post.path.read_bytes()
        with mock.patch.dict(os.environ, {"CHECK_LOGIN": "1"}, clear=True), mock.patch.object(c, "CONTENT", self.root), mock.patch.object(c, "DRY_RUN", True), mock.patch.object(c, "request") as request, mock.patch.object(c, "wait_until_live") as wait, contextlib.redirect_stdout(io.StringIO()) as output:
            with self.assertRaises(SystemExit) as exit:
                c.main()
        self.assertEqual(exit.exception.code, 0)
        for network in ("Bluesky", "Mastodon", "/dev/null"):
            self.assertIn(network, output.getvalue())
        request.assert_not_called()
        wait.assert_not_called()
        self.assertEqual(post.path.read_bytes(), before)


class HttpTests(unittest.TestCase):
    def test_plain_text_json_and_redirect_refusal_over_http(self):
        paths = []

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                paths.append(self.path)
                self.rfile.read(int(self.headers.get("Content-Length", 0)))
                if self.path == "/redirect":
                    self.send_response(302)
                    self.send_header("Location", "/destination")
                    self.end_headers()
                    return
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"ok": true}' if self.path == "/json" else b"Committed: test\n")

            def do_GET(self):
                paths.append(self.path)
                self.send_response(200)
                self.end_headers()

            def log_message(self, *args):
                pass

        with http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
            thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
            thread.start()
            try:
                base = f"http://127.0.0.1:{server.server_port}"
                self.assertEqual(c.request("POST", base + "/text", data=b"test", text_response=True, follow_redirects=False), (200, "Committed: test\n"))
                self.assertEqual(c.request("POST", base + "/json", json_body={"test": True}), (200, {"ok": True}))
                with self.assertRaisesRegex(RuntimeError, "302"):
                    c.request("POST", base + "/redirect", data=b"signed payload", text_response=True, follow_redirects=False)
                self.assertEqual(paths, ["/text", "/json", "/redirect"])
            finally:
                server.shutdown()
                thread.join(timeout=5)


class ImageTests(PostTestCase):
    def test_images_meet_devnull_format_and_size_limits(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow required for image conversion tests")
        for format in ("JPEG", "PNG", "WEBP", "GIF"):
            with self.subTest(format=format):
                path = self.root / f"image.{format.lower()}"
                Image.new("RGB", (10, 20), "red").save(path, format)
                data, mime, size = c.shrink(path, c.DEVNULL_IMAGE_MAX, formats=("JPEG", "PNG", "WEBP"))
                self.assertEqual(size, (10, 20))
                self.assertLessEqual(len(data), c.DEVNULL_IMAGE_MAX)
                with Image.open(io.BytesIO(data)) as result:
                    self.assertIn(result.format, ("JPEG", "PNG", "WEBP"))
                    self.assertEqual(mime, Image.MIME[result.format])
                    if format == "GIF":
                        self.assertEqual(result.format, "JPEG")


@unittest.skipUnless(all(shutil.which(cmd) for cmd in ("ssh-keygen", "ssh-agent", "ssh-add")), "OpenSSH required")
class RealSignatureTests(unittest.TestCase):
    def test_agent_signature_verifies_for_the_exact_namespace_and_payload(self):
        # Disposable key/agent, never the developer's SSH identity or live /dev/null.
        with tempfile.TemporaryDirectory(prefix="crosspost-", dir="/tmp") as directory:
            root = pathlib.Path(directory)
            key = root / "key"
            subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True, timeout=10)
            agent = subprocess.run(["ssh-agent", "-s", "-a", str(root / "agent.sock")], capture_output=True, text=True, check=True, timeout=10)
            env = {**os.environ, **dict(re.findall(r"(SSH_AUTH_SOCK|SSH_AGENT_PID)=([^;]+);", agent.stdout))}
            try:
                subprocess.run(["ssh-add", str(key)], env=env, capture_output=True, check=True, timeout=10)
                with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(c, "request", return_value=(200, " ".join(key.with_suffix(".pub").read_text().split()[:2]))):
                    client = c.DevNull(str(key.with_suffix(".pub")))
                    payload = "123\nnonce\n\nHello 👋".encode()
                    for namespace in ("devnull-commit", "devnull-commit-images"):
                        signature = client.signature(payload, namespace)
                        sig = root / "signature"
                        sig.write_text("-----BEGIN SSH SIGNATURE-----\n" + signature + "\n-----END SSH SIGNATURE-----\n")
                        allowed = root / "allowed"
                        allowed.write_text("crosspost " + key.with_suffix(".pub").read_text())
                        command = ["ssh-keygen", "-Y", "verify", "-f", str(allowed), "-I", "crosspost", "-n", namespace, "-s", str(sig)]
                        verified = subprocess.run(command, input=payload, capture_output=True, timeout=10)
                        self.assertEqual(verified.returncode, 0, verified.stderr)
                        tampered = subprocess.run(command, input=payload + b"!", capture_output=True, timeout=10)
                        self.assertNotEqual(tampered.returncode, 0)
            finally:
                subprocess.run(["ssh-agent", "-k"], env=env, capture_output=True, timeout=10)


if __name__ == "__main__":
    unittest.main()
