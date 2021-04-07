import logging
import settings
import json
import os

import requests
from telegram import ReplyKeyboardMarkup, KeyboardButton

import texts

USERS_FILE = os.path.join('.', 'data', 'users.json')
FAKE_USERS_FILE = os.path.join('.', 'data', 'fakes.json')
WAITLIST_FILE = os.path.join('.', 'data', 'waitlist.json')


##################
# KEYBOARDS
##################


def kbrd_start():
	btn_start = KeyboardButton('/start')
	keyboard = ReplyKeyboardMarkup(
		[[btn_start]],
		resize_keyboard=True
	)
	return keyboard


def kbrd_my_gender(text):
	btn_female = KeyboardButton(text['a_im_female'])
	btn_male = KeyboardButton(text['a_im_male'])
	keyboard = ReplyKeyboardMarkup(
		[[btn_female, btn_male]],
		resize_keyboard=True
	)
	return keyboard


def kbrd_gender_req(text):
	btn_female = KeyboardButton(text['a_req_female'])
	btn_both = KeyboardButton(text['a_req_both'])
	btn_male = KeyboardButton(text['a_req_male'])
	keyboard = ReplyKeyboardMarkup(
		[[btn_male, btn_both, btn_female]],
		resize_keyboard=True
	)
	return keyboard


def kbrd_skip(text):
	skip = KeyboardButton(text['a_skip'])
	keyboard = ReplyKeyboardMarkup(
		[[skip]],
		resize_keyboard=True,
		hide_keyboard=False
	)
	return keyboard


def kbrd_my_profile(text):
	btn_edit = KeyboardButton(text['a_edit'])
	btn_ok = KeyboardButton(text['a_ok'])
	keyboard = ReplyKeyboardMarkup(
		[[btn_edit, btn_ok]],
		resize_keyboard=True,
		hide_keyboard=False
	)
	return keyboard


def kbrd_search(text):
	btn_profile = KeyboardButton(text['a_my_profile'])
	btn_next = KeyboardButton(text['a_next'])
	keyboard = ReplyKeyboardMarkup(
		[[btn_profile, btn_next]],
		resize_keyboard=True,
		hide_keyboard=False
	)
	return keyboard


def kbrd_nothing_to_show(text):
	btn_profile = KeyboardButton(text['a_my_profile'])
	keyboard = ReplyKeyboardMarkup(
		[[btn_profile]],
		resize_keyboard=True,
		hide_keyboard=False
	)
	return keyboard


def get_saved_info():

	def get_users(file):
		users = {}
		try:
			with open(file, 'r') as f:
				saved_users = json.loads(f.read())
		except:
			pass
		else:
			for chat_id, user in saved_users.items():
				try:
					chat_id = int(chat_id)
				except ValueError:
					pass
				users[chat_id] = user
		return users

	users = get_users(USERS_FILE)
	fake_users = get_users(FAKE_USERS_FILE)
	users.update(fake_users)
	return users


def save_users(users):
	users_to_save = users.copy()
	real_users = {}
	fake_users = {}
	for chat_id, user in users_to_save.items():
		if 'test' in str(chat_id):
			fake_users[chat_id] = user
		elif user['status'] == 'search':
			real_users[chat_id] = user
	with open(USERS_FILE, 'w+') as f:
		f.write(json.dumps(real_users, indent=4))
	with open(FAKE_USERS_FILE, 'w+') as f:
		f.write(json.dumps(fake_users, indent=4))


def save_waitlist(waitlist):
	with open(WAITLIST_FILE, 'w+') as f:
		f.write(json.dumps(waitlist))


def getPhoto(file_id):
	link_1 = f'https://api.telegram.org/bot{settings.API_KEY}/getFile?file_id={file_id}'
	response = requests.get(link_1)
	response_json = json.loads(response.text)
	file_path = response_json['result']['file_path']
	file = f'https://api.telegram.org/file/bot{settings.API_KEY}/{file_path}'
	return file


def log(update):
	logging.info(f'update: {update}')


def get_text(user_lang):
	if not user_lang:
		return texts.en  # English lang by default
	user_lang = user_lang.split('-')[0]
	try:
		text = getattr(texts, user_lang)
	except (AttributeError, TypeError):
		text = texts.en    # English lang by default
		log(f'ERROR: no lang {user_lang}')
	return text


def understand_gender(answer):
	if '👨' in answer:
		return 'male'
	elif '👩' in answer:
		return 'female'
	elif '⚤' in answer:
		return 'both'
	else:
		return None
