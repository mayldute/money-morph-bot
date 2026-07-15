import logging

import telebot

from .config import BOT_TOKEN
from .constants import SUPPORTED_CURRENCIES
from .converter import CurrencyConverter, CurrencyConverterError


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN)


@bot.message_handler(commands=["start", "help"])
def handle_start_help(message: telebot.types.Message) -> None:
    """Handle the /start and /help commands."""

    text = (
        "Send a conversion request in the following format:\n"
        "<currency_from> <currency_to> <amount>\n\n"
        "Example:\n"
        "USD EUR 100\n\n"
        "Use /values to see all supported currencies."
    )

    bot.send_message(message.chat.id, text)


@bot.message_handler(commands=["values"])
def handle_values(message: telebot.types.Message) -> None:
    """Show all supported currencies."""

    currency_list = "\n".join(sorted(SUPPORTED_CURRENCIES))
    text = f"Available currencies:\n{currency_list}"

    bot.send_message(message.chat.id, text)


@bot.message_handler(content_types=["text"])
def handle_conversion(message: telebot.types.Message) -> None:
    """Handle a currency conversion request."""

    if not message.text:
        return

    parts = message.text.split()

    if len(parts) != 3:
        bot.send_message(
            message.chat.id,
            "Incorrect input format.\n"
            "Use: <currency_from> <currency_to> <amount>\n"
            "Example: USD EUR 100",
        )
        return

    quote, base, amount = parts

    try:
        total_base = CurrencyConverter.get_price(
            quote=quote,
            base=base,
            amount=amount,
        )
    except CurrencyConverterError as exc:
        bot.send_message(
            message.chat.id,
            f"Unable to convert currency.\n{exc}",
        )
    except Exception:
        logger.exception(
            "Unexpected error while processing a conversion request."
        )
        bot.send_message(
            message.chat.id,
            "An unexpected error occurred. Please try again later.",
        )
    else:
        normalized_quote = quote.upper()
        normalized_base = base.upper()

        text = (
            f"{amount} {normalized_quote} = "
            f"{total_base:.2f} {normalized_base}"
        )

        bot.send_message(message.chat.id, text)


def main() -> None:
    """Start the Telegram bot."""

    logger.info("Starting MoneyMorphBot")

    bot.infinity_polling(
        skip_pending=True,
        allowed_updates=["message"],
    )


if __name__ == "__main__":
    main()