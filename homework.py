import logging
import os
import requests
import sys
import telegram
import time

from dotenv import load_dotenv

from exceptions import (TokensChatIdError,
                        CheckApiKey,
                        CheckHomeworkStatus,
                        ResponseError)

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s - [%(levelname)s] - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Send message Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Бот отправил сообщение {message}')
    except Exception as error:
        logger.error('Сбой при отправке сообщения в Telegram:'
                     f'{message}. Ошибка {error}')


def get_api_answer(current_timestamp):
    """Get API homework result."""
    if (type(current_timestamp) == int or type(
            current_timestamp) == float) and (
            0 <= current_timestamp <= time.time()):
        timestamp = current_timestamp
    else:
        timestamp = int(time.time())
    logger.debug(f'Время запроса {time.ctime(timestamp)}')
    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(ENDPOINT,
                                         headers=HEADERS, params=params)
        response = homework_statuses.json()
    except Exception as error:
        raise ResponseError(f'Эндпоинт {ENDPOINT} недоступен. {error}')
    if homework_statuses.status_code != 200:
        message = (f'Эндпоинт {ENDPOINT} недоступен.'
                   f'Код ответа API: {homework_statuses.status_code}. ')
        if response.get('error') is not None:
            error = f'Ошибка {response.get("error")}'
            message += error
        if response.get('code') is not None:
            error = f'Причина ошибки {response.get("code")}'
            message += error
        raise ResponseError(message)
    return response


def check_response(response):
    """Check correct API."""
    if type(response['homeworks']) != list or type(
            response['current_date']) != int:
        raise CheckApiKey('Отсутствие ожидаемых ключей в ответе API')
    homeworks = response['homeworks']
    return homeworks


def parse_status(homework):
    """Status last homework."""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    logger.info(f'Работа: {homework_name}')
    if homework_status not in HOMEWORK_STATUSES:
        raise CheckHomeworkStatus('Недокументированный статус домашней работы,'
                                  'обнаруженный в ответе API.')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Check tokens and chat_id."""
    if type(TELEGRAM_CHAT_ID) is not None:
        logger.critical('Отсутствует обязательная переменная окружения:'
                        '"TELEGRAM_CHAT_ID" Программа принудительно'
                        'остановлена.')
        return False
    elif type(TELEGRAM_TOKEN) is not None:
        logger.critical('Отсутствует обязательная переменная окружения:'
                        '"TELEGRAM_TOKEN" Программа принудительно'
                        'остановлена.')
        return False
    elif type(PRACTICUM_TOKEN) is not None:
        logger.critical('Отсутствует обязательная переменная окружения:'
                        '"PRACTICUM_TOKEN" Программа принудительно'
                        'остановлена.')
        return False
    return True


def main():
    """Basic logic of the bot."""
    if not check_tokens():
        raise TokensChatIdError('Tokens or chat_id missing.')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    last_message = None
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            current_timestamp = response.get('current_date')
            if len(homework) == 0:
                logger.info('Изменения отсутствуют.')
                time.sleep(RETRY_TIME)
                continue
            message = parse_status(homework[0])
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
        if last_message != message and message is not None:
            last_message = message
            send_message(bot, message)
        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
