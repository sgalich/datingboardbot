import logging

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

import settings
import handlers
import utils


logging.basicConfig(
	format='%(asctime)s - %(levelname)s - %(message)s',
	level=logging.INFO,
	filename='bot.log'
)


def main():
	handlers.users = utils.get_saved_info()
	updater = Updater(settings.API_KEY)
	dispatcher = updater.dispatcher
	dispatcher.add_handler(CommandHandler('start', handlers.start, pass_user_data=True))
	dispatcher.add_handler(MessageHandler(Filters.text & (~Filters.command), handlers.message, pass_user_data=True))
	dispatcher.add_handler(MessageHandler(Filters.photo, handlers.photo_message, pass_user_data=True))
	dispatcher.add_handler(MessageHandler(Filters.document, handlers.file_message, pass_user_data=True))
	dispatcher.add_handler(CommandHandler('stop', handlers.stop))
	updater.start_polling()
	updater.idle()


if __name__ == '__main__':
	main()
