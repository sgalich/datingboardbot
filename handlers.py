import os

import requests
from emoji import emojize
from telegram.error import InvalidToken, RetryAfter, TimedOut, Unauthorized

import utils
import texts


users = {}
# user:
# {
# 	chat_id (int): {
#       status: 'create' / 'search',
#       profile: {
#           profile Object
#           sex_my: 'male' / 'female',
#           sex_req: 'male' / 'both' / 'female',
#           photo: '',
#           comment: '',
#           username: ''
#       },
#       chat_id: int,
#       shown: [chat_id, chat_id, chat_id...],
#       awaits: True/False,
#       lang: en/ru/uk/...
#   }
# }

##############3
# statuses:
# sex_my
# sex_req
# photo
# comment
# confirm
# ready
#

# class Profile:
#
# 	def __init__(self):    #, sex_my, sex_required):
# 		pass
# 		# self.sex_my = sex_my
# 		# self.sex_required = sex_required
#

# UTILS

def send_stats(update):
	m_m = 0
	m_b = 0
	m_f = 0
	f_m = 0
	f_b = 0
	f_f = 0
	for _, user in users.items():
		if 'real' in update.message['text'] and 'test' in str(user['chat_id']):
			continue
		if user['profile']['sex_my'] == 'male':
			if user['profile']['sex_req'] == 'male':
				m_m += 1
			elif user['profile']['sex_req'] == 'both':
				m_b += 1
			elif user['profile']['sex_req'] == 'female':
				m_f += 1
		elif user['profile']['sex_my'] == 'female':
			if user['profile']['sex_req'] == 'male':
				f_m += 1
			elif user['profile']['sex_req'] == 'both':
				f_b += 1
			elif user['profile']['sex_req'] == 'female':
				f_f += 1
	males_count = m_f + m_m + m_b
	females_count = f_m + f_f + f_b
	males_percentage = '{:.1f}'.format(males_count / (males_count + females_count) * 100)
	females_percentage = '{:.1f}'.format(females_count / (males_count + females_count) * 100)
	stats_mes = f"""
Males: {males_count} ({males_percentage}%)
\t\t\tlooking for
\t\t\twomen: {m_f}
\t\t\tmen: {m_m}
\t\t\tboth: {m_b}

Females: {females_count} ({females_percentage}%)
\t\t\tlooking for
\t\t\tmen: {f_m}
\t\t\twomen: {f_f}
\t\t\tboth: {f_b}

Users total: {males_count + females_count}
"""
	update.message.reply_text(stats_mes, parse_mode='Markdown')


def create_new_user(chat_id, message):
	users[chat_id] = dict(
		status='sex_my',    # the first question in profile creation process
		profile=dict(
			sex_my=None,
			sex_req=None,
			photo=None,
			comment='',
			username=message['chat']['username']
		),
		chat_id=chat_id,
		shown=[],    # who viewed this profile (chat_id's)
		awaits=False,
		lang=message.from_user['language_code']
	)

def save_user(message):
	"""Save user's data."""
	chat_id = message['chat']['id']
	if not users.get(chat_id):
		create_new_user(chat_id, message)


# HANDLERS

def start(update, context):
	"""The first message handler."""
	save_user(update.message)
	create_profile(update, context)
	user = users[update.message['chat']['id']]
	utils.log(f'A new user: {user}')


def message(update, context):
	chat_id = update.message['chat']['id']
	try:
		user = users[chat_id]
	except KeyError:
		start(update, context)
		return None
	message_text = update.message['text']

	utils.log(f'MESSAGE from: {chat_id}, text: {message_text}')

	# Send statistics
	if message_text.split()[0] == 'statistics':
		send_stats(update)
	if user['status'] != 'search':
		create_profile(update, context)
	# List through profiles
	else:
		if '📋' in message_text:
			text = utils.get_text(update.message.from_user['language_code'])
			# text = utils.get_text(user['lang'])
			_send_profile(
				context,
				chat_id,
				user,
				reply_markup=utils.kbrd_my_profile(text)
			)
		elif '✍️' in message_text:
			user['status'] = 'sex_my'
			create_profile(update, context)
		elif '✅' in message_text or '🚀' in message_text \
			or '▶' in message_text:    # DEPRECATED!
			list_profiles(context, user)


def _photo_accepted(update, user):
	text = utils.get_text(update.message.from_user['language_code'])
	update.message.reply_text(
		text['q_description'],
		reply_markup=utils.kbrd_skip(text)
	)
	user['status'] = 'confirm'


def photo_message(update, context):
	user = users[update.message['chat']['id']]
	utils.log(f'message: {update.message}')
	utils.log(f'user: {user}')
	# print(update.message['photo'][-1]['file_id'])
	# If it is creating profile process
	if user['status'] == 'comment':
		user['profile']['photo'] = update.message['photo'][-1]['file_id']
		_photo_accepted(update, user)


def file_message(update, context):

	def save_image(url, file_id):
		"""Save an image in a certain directory."""
		file_path = os.path.join('.', 'images', f'{file_id}.jpeg')
		resp = requests.get(url)
		if resp.status_code == 200:
			with open(file_path, 'wb') as f:
				f.write(resp.content)
		return file_path

	chat_id = update.message['chat']['id']
	user = users[chat_id]

	utils.log(f'message: {update.message}')

	# Handle it as a usual message
	if user['status'] == 'comment' and update.message['document']['mime_type'] == 'image/jpeg':
		# Save a photo
		file_id = update.message['document']['file_id']
		url = context.bot.getFile(file_id)['file_path']
		file = save_image(url, file_id)
		# Send the photo in chat
		file_sent = context.bot.sendPhoto(
			update.message.chat.id,
			open(file, 'rb')
		)
		user['profile']['photo'] = file_sent['photo'][-1]['file_id']
		context.bot.deleteMessage(
			update.message.chat.id,
			file_sent['message_id']
		)
		_photo_accepted(update, user)
		os.remove(file)
	else:
		user = users[update.message['chat']['id']]
		utils.log(f'message: {update.message}')
		utils.log(f'user: {user}')


def create_profile(update, context):
	# Check if this user is active (is looking for a pair)
	chat_id = update.message['chat']['id']
	user = users[chat_id]
	user['lang'] = update.message.from_user['language_code']
	text = utils.get_text(update.message.from_user['language_code'])
	if user['status'] == 'sex_my':
		user['status'] = 'sex_req'
		user['profile'] = dict(
			sex_my=None,
			sex_req=None,
			photo=None,
			comment='',
			username=update.message['chat']['username']
		)
		update.message.reply_text(
			text['create_profile']
		)
		update.message.reply_text(
			text['q_your_gender'],
			reply_markup=utils.kbrd_my_gender(text)
		)
	# sex_my is awaiting as an answer
	elif user['status'] == 'sex_req':
		sex_my = utils.understand_gender(update.message['text'])
		# Update answer to the previous question
		# if the answer is not relevant
		if not sex_my:
			update.message.reply_text(
				text['error_answer']
			)
			update.message.reply_text(
				text['q_your_gender'],
				reply_markup=utils.kbrd_my_gender(text)
			)
		else:
			user['profile']['sex_my'] = sex_my
			user['status'] = 'photo'
			update.message.reply_text(
				text['q_req_gender'],
				reply_markup=utils.kbrd_gender_req(text)
			)
	# sex_req is awaiting as an answer
	elif user['status'] == 'photo':
		sex_req = utils.understand_gender(update.message['text'])
		# Update answer to the previous question
		# if the answer is not relevant
		if not sex_req:
			update.message.reply_text(
				text['error_answer']
			)
			update.message.reply_text(
				text['q_req_gender'],
				reply_markup=utils.kbrd_gender_req(text)
			)
		else:
			user['profile']['sex_req'] = sex_req
			user['status'] = 'comment'
			update.message.reply_text(
				text['q_photo'],
				reply_markup={'hide_keyboard': True}
			)
	# photo is awaiting as an answer
	elif user['status'] == 'comment':
		# Update answer to the previous question
		# if the answer is not relevant
		if not update.message['photo']:
			update.message.reply_text(
				text['error_photo'],
				reply_markup={'hide_keyboard': True}
			)
	# comment is awaiting as an answer
	elif user['status'] == 'confirm':
		reply = update.message['text']
		# Save the comment if it exists
		if '⏭' not in reply:
			user['profile']['comment'] = reply
		_send_profile(context, update.message.chat.id, user)
		update.message.reply_text(
			text['q_confirm'],
			reply_markup=utils.kbrd_my_profile(text)
		)
		user['status'] = 'ready'
	# confirm is awaiting as an answer
	elif user['status'] == 'ready':
		if '✅' in update.message['text']:
			user['shown'] = []    # Reset viewers of this profile
			user['status'] = 'search'
			update.message.reply_text(
				text['confirm'],
				reply_markup={'hide_keyboard': True}
			)
			update.message.reply_text(
				text['how_to_stop'],
				reply_markup=utils.kbrd_search(text)
			)
			_send_new_profile_to_awaits(context, user)
			utils.save_users(users)
			list_profiles(context, user)
		elif update.message['text'] == emojize(':writing_hand: edit'):
			user['status'] = 'sex_my'
			create_profile(update, context)


def stop(update, context):
	"""Stop handler."""
	chat_id = update.message['chat']['id']
	del users[chat_id]
	utils.save_users(users)


#################
# LIST PROFILES #
#################

def _send_profile(context, chat_id, user_from, reply_markup=None):
	if 'test' in str(chat_id):
		return None
	reply_markup = {'hide_keyboard': True} if not reply_markup else reply_markup
	comment = user_from['profile']['comment']
	link = user_from['profile']['username']
	user_from_chat_id = user_from['chat_id']
	text = utils.get_text(users[chat_id].get('lang'))
	connect = text['connect']
	# TODO: Check if user exists. If not - delete it
	#  Example:  https://tg://user?id=1523667791
	mention = f'[{connect}](tg://user?id={user_from_chat_id})'
	parse_mode = 'Markdown'
	# Fakes:
	if 'test' in mention:
		mention = f'@{link}'
		parse_mode = None
	caption = mention if not comment else f'{comment}\n\n{mention}'
	context.bot.sendPhoto(
		chat_id,
		user_from['profile']['photo'],
		caption=caption,
		reply_markup=reply_markup,
		parse_mode=parse_mode
	)


def list_profiles(context, user_to):
	# Find a candidate to show
	chat_id_to = user_to['chat_id']
	sex_my = user_to['profile']['sex_my']
	sex_req = user_to['profile']['sex_req']
	text = utils.get_text(user_to.get('lang'))
	# Random order
	chat_ids = list(users.keys())
	for _id in chat_ids:
		user_from = users[_id]
		if chat_id_to not in user_from['shown'] \
			and user_from['status'] == 'search' \
			and (user_from['profile']['sex_my'] == sex_req or sex_req == 'both') \
			and (user_from['profile']['sex_req'] == sex_my or user_from['profile']['sex_req'] == 'both') \
			and user_from['chat_id'] != chat_id_to:
			_send_profile(
				context,
				chat_id_to,
				user_from,
				reply_markup=utils.kbrd_search(text)
			)
			user_from['shown'].append(chat_id_to)
			utils.save_users(users)

			utils.log(f'Sent a profile: {user_from}')

			return None
	# If there is no profiles to show
	context.bot.send_message(
		chat_id_to,
		text['nothing_to_show'],
		reply_markup=utils.kbrd_nothing_to_show(text)
	)

	utils.log('Nothing to show!')

	users[chat_id_to]['awaits'] = True


def _send_new_profile_to_awaits(context, user_from):
	# Find a candidate to whom we are showing a new profile
	sex_my = user_from['profile']['sex_my']
	sex_req = user_from['profile']['sex_req']
	for chat_id, user_to in users.items():
		if chat_id not in user_from['shown'] \
			and user_to['awaits'] \
			and user_to['status'] == 'search' \
			and (user_to['profile']['sex_my'] == sex_req or sex_req == 'both') \
			and (user_to['profile']['sex_req'] == sex_my or user_to['profile']['sex_req'] == 'both') \
			and chat_id != user_from['chat_id']:
			text = utils.get_text(user_to.get('lang'))
			try:
				context.bot.send_message(
					chat_id,
					text['new_profile'],
					reply_markup=utils.kbrd_search(text)
				)
			except Unauthorized:
				utils.log(f'USER STOPPED THE BOT: {users[chat_id]}')
				del users[chat_id]
				utils.save_users(users)
				continue
			_send_profile(
				context,
				chat_id,
				user_from,
				reply_markup=utils.kbrd_search(text)
			)
			user_to['shown'].append(chat_id)
			user_to['awaits'] = False
			utils.save_users(users)


# TODO: ??? Добавить кнопки под реплаем бота
# TODO: ???? Добавить вопросы для расширения анкеты
# TODO: ???? при редактириовании анкеты добавить кнопки «оставить старое значение»
# 1. Данные сохранять локально, чтобы перезапуск бота не влиял на его работу
# 2. Сделать кнопки edit и my profile рабочими
# 3. Сделать waitlist - когда некого показывать и вдруг появляется новая анкета - она отправляется всем из waitlist'а
# TODO: 4. Протестировать различные случаи
# TODO: 5. Устранить ошибки - /start внезапный или вообще путаница с командами
# Убрать ники, сделать просто ссылку типа "Написать"
# Добавить both для поиска
# разделить профайлы на фейки и не фейки
# Сделать поддержку языков: ru, en, uk, it, be
# TODO: Исправить повторную отправку анкеты после отправки awaits
# добавить нулевое сообщение перед start
# todo: добавить возможность остановить бот и не показывать больше анкету сделать остановку бота когда из него выходишь (delete and stop bot)
# TODO:  добавить ответ на /stop
# TODO:  убрать клавиатуру после /stop (добавить кнопку /start)
# TODO:  edit появляется только при просмотре своего профиля
# добавить просмотр статистики пользователей
# todo: сделать user плоским (убрать profile)
# todo: ...
