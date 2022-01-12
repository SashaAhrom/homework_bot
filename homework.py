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
                        SendMessage)

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s - [%(levelname)s] - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = 550872843

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
    bot.send_message(TELEGRAM_CHAT_ID, message)
    logger.info(f'Бот отправил сообщение {message}')


def get_api_answer(current_timestamp):
    """Get API homework result."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    homework_statuses = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if homework_statuses.status_code != 200:
        raise SendMessage(f'Эндпоинт {ENDPOINT} недоступен.'
                          f'Код ответа API: {homework_statuses.status_code}')
    logger.info(homework_statuses.json())
    return homework_statuses.json()


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
    if type(TELEGRAM_CHAT_ID) != int:
        logger.critical('Отсутствует обязательная переменная окружения:'
                        '"TELEGRAM_CHAT_ID" Программа принудительно'
                        'остановлена.')
        return False
    elif type(TELEGRAM_TOKEN) != str:
        logger.critical('Отсутствует обязательная переменная окружения:'
                        '"TELEGRAM_TOKEN" Программа принудительно'
                        'остановлена.')
        return False
    elif type(PRACTICUM_TOKEN) != str:
        logger.critical('Отсутствует обязательная переменная окружения:'
                        '"PRACTICUM_TOKEN" Программа принудительно'
                        'остановлена.')
        return False
    return True


def sleep_a_bit(response):
    """The program delay 'RETRY_TIME' minutes."""
    time.sleep(RETRY_TIME)
    current_timestamp = response.get('current_date')
    logger.debug(f'Время нового запроса {time.ctime(current_timestamp)}')


def main():
    """Basic logic of the bot."""
    if not check_tokens():
        raise TokensChatIdError('Tokens or chat_id missing.')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    logger.debug(f'Начало работы програмы {time.ctime(current_timestamp)}')
    last_message = None
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if len(homework) == 0:
                sleep_a_bit(response)
                continue
            message = parse_status(homework[0])
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
        else:
            try:
                if last_message != message and message is not None:
                    last_message = message
                    send_message(bot, message)
            except Exception as error:
                logger.error('Сбой при отправке сообщения в Telegram:'
                             f'{message}. Ошибка {error}')
            sleep_a_bit(response)


if __name__ == '__main__':
    main()
