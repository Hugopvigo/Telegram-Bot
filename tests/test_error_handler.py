"""Regression tests: Transient Telegram network errors stay at WARNING.

Run inside the bot container (has all deps):
    docker cp tests <contenedor>:/tmp/tbtests
    docker exec <contenedor> python -m unittest discover -s /tmp/tbtests -t /app -v
"""
import unittest
from types import SimpleNamespace

from telegram.error import NetworkError

from app.bot import error_handler


class ErrorHandlerTest(unittest.IsolatedAsyncioTestCase):
    async def test_network_error_downgraded_to_warning(self):
        ctx = SimpleNamespace(error=NetworkError("Bad Gateway"))
        with self.assertLogs("app.bot", level="WARNING") as logs:
            await error_handler(None, ctx)
        self.assertTrue(
            any("transitorio" in line for line in logs.output), logs.output
        )
        self.assertFalse(
            any("Traceback" in line for line in logs.output), logs.output
        )

    async def test_unexpected_error_logged_with_traceback(self):
        ctx = SimpleNamespace(error=RuntimeError("boom"))
        with self.assertLogs("app.bot", level="ERROR") as logs:
            await error_handler(None, ctx)
        # exc_info adjunta el tipo de error al registro.
        self.assertTrue(
            any("RuntimeError: boom" in line for line in logs.output),
            logs.output,
        )


if __name__ == "__main__":
    unittest.main()
