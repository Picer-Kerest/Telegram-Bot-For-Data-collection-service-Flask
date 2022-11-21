import requests
import re
import copy
from flask import Flask, redirect, url_for, session
from flask.views import MethodView
from flask import request
import os
# from dotenv import load_dotenv
# load_dotenv()
# For local No need


app = Flask(__name__)
TOKEN = os.environ.get('TOKEN')
API_URL = os.environ.get('API_URL')
TELEGRAM_URL = f'https://api.telegram.org/bot{TOKEN}/sendMessage'


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
    # dog_pattern = r'@\w+-\w+$'
    message = 'Invalid request'
    if '/' in text_msg:
        if '/start' in text_msg or '/help' in text_msg:
            message = '''
            To view cities: `/city`
            To view programming languages: `/language` 
            To make a job request, enter separated by a space: `@city @language`
            Example: `@moscow @python`
            '''
            return message
        elif '/cities' in text_msg or '/languages' in text_msg:
            command = re.search(command_p, text_msg).group().replace('/', '')  # group: MatchObject ->str
            command = adresses.get(command)
            return [command]
            # Возвращаем список, потому что может быть несколько команд в строке.
            # Ниже пример такой строки
        else:
            return message
        
    elif '@' in text_msg:
        if text_msg == '@sankt-peterburg @python' or text_msg == '@python @sankt-peterburg':
            commands = ['sankt-peterburg', 'python']
            return commands
        else:
            result = re.findall(dog_pattern, text_msg)
            commands = [el.replace('@', '') for el in result]
            return commands if len(commands) == 2 else None

    else:
        return message


@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == 'POST':
        return '<h1 align="center">POST METHOD from def index</h1>'
    return '<h1 align="center">GET METHOD from def index</h1>'


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
                        message += '#' + d['slug'] + '\n'
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
                command = '/vacancy/?city={}&language={}'.format(*tmp)
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
                    text_msg = 'Результаты поиска, согласно Вашего запроса:\n'
                    text_msg += '- ' * 38 + '\n'
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

