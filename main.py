import requests
import re
import copy
from flask import Flask, redirect, url_for, session
from flask.views import MethodView
from flask import request
from utils import from_cyrillic_to_eng
import os
# from dotenv import load_dotenv
# load_dotenv()
# For local


app = Flask(__name__)
TOKEN = os.environ.get('TOKEN')
API_URL = os.environ.get('API_URL')
TELEGRAM_URL = f'https://api.telegram.org/bot{TOKEN}/sendMessage'


def is_spb(text_msg):
    """
    Проверка на то, присутствует ли @Sankt Peterburg в введённом сообщении
    return: ['Sankt Peterburg', 'Python']

    # replace return str
    # split return list
    """
    commands = []
    if '@Sankt Peterburg' in text_msg:
        tmp = text_msg.split()
        if tmp[0] == '@Sankt':
            # tmp = ['@Sankt', 'Peterburg', '@Python']
            # commands = ['Sankt Peterburg', 'Python']
            commands.append(tmp[0].replace('@', '') + ' ' + tmp[1])
            commands.append(tmp[2].replace('@', ''))
        elif tmp[1] == '@Sankt':
            # tmp = ['@Python', '@Sankt', 'Peterburg']
            # commands = ['Sankt Peterburg', 'Python']
            commands.append(tmp[1].replace('@', '') + ' ' + tmp[2])
            commands.append(tmp[0].replace('@', ''))
        else:
            commands = None
    return commands


def get_data_from_api(command):
    """
    return: http://127.0.0.1:8000/api/cities
                            or
            http://127.0.0.1:8000/api/languages
    """
    url = API_URL + command
    session = requests.Session()
    r = session.get(url).json()
    return r


def send_message(chat_id, msg):
    session = requests.Session()
    r = session.get(TELEGRAM_URL, params=dict(chat_id=chat_id, text=msg, parse_mode='Markdown'))
    return r.json()


def parse_text(text_msg):
    # https://pythex.org/
    adresses = {
        'cities': '/cities',
        'languages': '/languages'
    }
    # Значения из scraping.api.urls.py
    command_p = r'/\w+'
    dog_pattern = r'@\w+'
    message = 'Invalid request'
    if '/' in text_msg:
        if '/start' in text_msg or '/help' in text_msg:
            message = 'To view cities: `/city`\nTo view programming languages: `/language`\n' \
                      'To make a job request, enter separated by a space: `@City @Language`\n' \
                      'Example: `@Moscow @Python`\n'
            return message
        else:
            command = re.search(command_p, text_msg).group().replace('/', '')  # group: MatchObject ->str
            command = adresses.get(command, None)
            return [command] if command else None
            # Возвращаем список, потому что может быть несколько команд в строке.
            # Ниже пример такой строки

    elif '@' in text_msg:
        if '@Sankt Peterburg' in text_msg:
            commands = is_spb(text_msg)
            return commands
            # commands = text_msg.replace('@', '').split()  # replace return str
            # return commands                               # split return list
        elif '@C#' in text_msg:
            if '@Sankt Peterburg' in text_msg:
                return ['Sankt Peterburg', 'C#']
            elif '@Moscow' in text_msg:
                return ['Moscow', 'C#']
            else:
                return None
        else:
            result = re.findall(dog_pattern, text_msg)
            commands = [el.replace('@', '') for el in result]
            return commands if len(commands) == 2 else None

    else:
        return message


@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == 'POST':
        return '<h1 align="center">POST METHOD from function</h1>'
    return '<h1 align="center">GET METHOD from function</h1>'


class BotAPI(MethodView):

    def get(self):
        return '<h1 align="center">GET method from class</h1>'

    def post(self):
        resp = request.get_json()
        text_msg = resp['message']['text']
        chat_id = resp['message']['chat']['id']
        tmp = parse_text(text_msg)
        empty = 'Invalid request'
        error_msg = 'Nothing was found for your query'
        if tmp:
            if len(tmp) > 10:
                send_message(chat_id, tmp)
            elif len(tmp) == 1:
                resp = get_data_from_api(tmp[0])  # type=dict
                message = ''
                msg = ''
                if resp:
                    for d in resp:
                        message += '#' + d['name'] + '\n'
                    if tmp[0] == '/languages':
                        msg = 'Available programming languages: \n'
                    elif tmp[0] == '/cities':
                        msg = 'Available cities: \n'
                    send_message(chat_id, msg + message)
                else:
                    send_message(chat_id, error_msg)
            elif len(tmp) == 2:
                # tmp = ['python', 'moscow']
                # ?city=moscow&language=python
                # tmp = ['Python', 'Moscow']
                city_slug = from_cyrillic_to_eng(str(tmp[0]))
                language_slug = from_cyrillic_to_eng(str(tmp[1]))
                command = '/vacancy/?city={}&language={}'.format(city_slug, language_slug)
                resp = get_data_from_api(command)
                if resp:
                    pieces = []
                    size = len(resp)        # Длина ответа
                    extra = len(resp) % 10  # Остатки в случае некратности 10
                    if size < 11:           # Если меньше 11, то ответ готов
                        pieces.append(resp)
                    else:
                        for i in range(size // 10):
                            y = i * 10
                            pieces.append(resp[y:y + 10])
                        if extra:
                            pieces.append(resp[y + 10:])
                    # Сначала отправляем в ответ заголовок
                    text_msg = f'The result according to your request: {tmp[0]}, {tmp[1]}\n'
                    text_msg += '- ' * 30 + '\n'
                    send_message(chat_id, text_msg)

                    for part in pieces:
                        # Потом для каждой части, формируем новый ответ
                        # И добавляем его в тот же чат
                        message = ''
                        for v in part:
                            message += v['title'] + '\n'
                            # url = v['url']
                            message += v['url'] + '\n'
                            message += '-' * 5 + '\n\n'
                        send_message(chat_id, message)
            else:
                send_message(chat_id, error_msg)
        else:
            send_message(chat_id, empty)
        return '', 200


# app.add_url_rule('/TOKEN/', view_func=BotAPI.as_view('bot'))  # for local
app.add_url_rule(f'/{TOKEN}/', view_func=BotAPI.as_view('bot'))  # for production
# Общая рекомендация по названию адреса


if __name__ == '__main__':
    app.run(debug=True)

