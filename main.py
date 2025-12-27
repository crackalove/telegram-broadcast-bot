import asyncio
import json
import logging
import os
import random
from typing import Any, Dict, List, Optional, Tuple

from telethon import TelegramClient, errors
from dotenv import load_dotenv

CONFIG_PATH = os.getenv("CONFIG_PATH", "config.json")
LOG_FILE = os.getenv("LOG_FILE", "send.log")

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def print_banner() -> None:
    text = "Скрипт создан командой t.me/ReChamo"
    border = "═" * (len(text) + 4)
    print(f"╔{border}╗")
    print(f"║  {text}  ║")
    print(f"╚{border}╝")


def jitter_interval(base_minutes: float, jitter_ratio: float = 0.1) -> float:
    delta = base_minutes * jitter_ratio
    return max(0.1, random.uniform(base_minutes - delta, base_minutes + delta))


async def send_message_safe(
    client: TelegramClient, chat: str, message: str
) -> Tuple[bool, Optional[str]]:
    try:
        await client.send_message(chat, message)
        return True, None
    except errors.FloodWaitError as e:
        wait_sec = e.seconds
        logger.warning(f"flood wait для чата {chat}: спим {wait_sec} секунд")
        await asyncio.sleep(wait_sec)
        return False, f"flood_wait:{wait_sec}"
    except errors.RPCError as e:
        logger.error(f"rpc ошибка для чата {chat}: {e}")
        return False, f"rpc_error:{e.__class__.__name__}"
    except Exception as e:
        logger.exception(f"Непредвиденная ошибка для чата {chat}: {e}")
        return False, f"unexpected:{e.__class__.__name__}"


async def main() -> None:
    print_banner()
    cfg = load_config(CONFIG_PATH)

    api_id = int(os.getenv("API_ID") or cfg["api_id"])
    api_hash = os.getenv("API_HASH") or cfg["api_hash"]
    session_name = os.getenv("SESSION_NAME") or cfg.get("session_name", "session")

    chat_list: List[str] = cfg["chat_list"]
    messages: List[str] = cfg["messages"]
    interval_minutes: float = float(cfg.get("interval_minutes", 5))
    jitter_ratio: float = float(cfg.get("jitter_ratio", 0.1))
    stats = {"sent": 0, "failed": 0}

    client = TelegramClient(session_name, api_id, api_hash)

    await client.start()
    logger.info("Скрипт запущен. Нажмите Ctrl+C для остановки.")

    try:
        while True:
            message = random.choice(messages)
            for chat in chat_list:
                ok, err = await send_message_safe(client, chat, message)
                if ok:
                    stats["sent"] += 1
                    logger.info(f"Отправлено в {chat}: {message!r}")
                else:
                    stats["failed"] += 1
                    logger.warning(f"Не отправлено в {chat}. reason={err}")

            wait_min = jitter_interval(interval_minutes, jitter_ratio)
            logger.info(f"Ждём {wait_min:.2f} минут (для обхода спамблока)")
            await asyncio.sleep(wait_min * 60)
    except KeyboardInterrupt:
        logger.info(
            f"Остановлено пользователем. Итог: sent={stats['sent']} failed={stats['failed']}"
        )
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())