import asyncio
import importlib.util
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import bot
import db


def run(coro):
    return asyncio.run(coro)


class LeadFlowTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path_patch = patch.object(db, "DB_PATH", Path(self.tmp.name) / "leads.db")
        self.path_patch.start()
        db.init_db()
        self.admin_patch = patch.object(bot, "ADMIN_CHAT_ID", 99)
        self.admin_patch.start()

    def tearDown(self):
        self.admin_patch.stop()
        self.path_patch.stop()
        self.tmp.cleanup()

    def update(self, text, user_id=12):
        return SimpleNamespace(message=SimpleNamespace(text=text, reply_text=AsyncMock()),
                               effective_user=SimpleNamespace(id=user_id, username="someone"))

    def test_blank_fields_rejected_then_persist_and_escape_html(self):
        context = SimpleNamespace(user_data={"lead": {}}, bot=SimpleNamespace(send_message=AsyncMock()))
        for handler, key, state in [(bot.lead_name, "name", bot.NAME),
                                    (bot.lead_contact, "contact", bot.CONTACT),
                                    (bot.lead_need, "need", bot.NEED)]:
            self.assertEqual(run(handler(self.update("   "), context)), state)
            self.assertNotIn(key, context.user_data["lead"])
        self.assertEqual(run(bot.lead_budget(self.update("   "), context)), bot.BUDGET)
        self.assertEqual(db.stats()["total"], 0)
        run(bot.lead_name(self.update("<Ai & Co>"), context))
        run(bot.lead_contact(self.update("<contact>"), context))
        run(bot.lead_need(self.update("Telegram <bot> integration"), context))
        run(bot.lead_budget(self.update("20,000 THB & more"), context))
        self.assertEqual(db.stats()["pending"], 1)
        lead = db.get_lead(1)
        self.assertEqual(lead["name"], "<Ai & Co>")
        sent = context.bot.send_message.await_args.kwargs["text"]
        self.assertIn("&lt;Ai &amp; Co&gt;", sent)
        self.assertIn("&lt;bot&gt;", sent)
        self.assertIn("THB &amp; more", sent)

    def test_atomic_decision_and_admin_access(self):
        lead_id = db.create_lead(12, "someone", "Name", "contact", "need", "budget", 30, "COLD")
        self.assertTrue(db.update_status(lead_id, "APPROVED"))
        self.assertFalse(db.update_status(lead_id, "REJECTED"))
        self.assertEqual(db.get_lead(lead_id)["status"], "APPROVED")
        with self.assertRaises(ValueError):
            db.update_status(lead_id, "UNKNOWN")
        user = self.update("/stats", user_id=12)
        with patch.object(bot, "stats", side_effect=AssertionError("unauthorized access")):
            run(bot.stats_cmd(user, SimpleNamespace()))
        self.assertIn("Admin only", user.message.reply_text.await_args.args[0])

    def test_replayed_callback_does_not_notify_twice(self):
        lead_id = db.create_lead(12, "someone", "Name", "contact", "need", "budget", 30, "COLD")
        query = SimpleNamespace(from_user=SimpleNamespace(id=99), data=f"approve:{lead_id}",
                                answer=AsyncMock(), edit_message_reply_markup=AsyncMock(),
                                message=SimpleNamespace(reply_text=AsyncMock()))
        update = SimpleNamespace(callback_query=query)
        context = SimpleNamespace(bot=SimpleNamespace(send_message=AsyncMock()))
        run(bot.admin_action(update, context))
        query.data = f"reject:{lead_id}"
        run(bot.admin_action(update, context))
        self.assertEqual(db.get_lead(lead_id)["status"], "APPROVED")
        self.assertEqual(context.bot.send_message.await_count, 1)
        self.assertEqual(query.edit_message_reply_markup.await_count, 1)
        query.from_user.id = 12
        run(bot.admin_action(update, context))
        self.assertEqual(context.bot.send_message.await_count, 1)

    def test_db_failure_does_not_claim_success(self):
        update = self.update("1000 USD")
        context = SimpleNamespace(user_data={"lead": {"name": "N", "contact": "C", "need": "Bot"}},
                                  bot=SimpleNamespace(send_message=AsyncMock()))
        with patch.object(bot, "create_lead", side_effect=sqlite3.OperationalError("disk unavailable")):
            with self.assertRaises(sqlite3.OperationalError):
                run(bot.lead_budget(update, context))
        update.message.reply_text.assert_not_awaited()
        context.bot.send_message.assert_not_awaited()
