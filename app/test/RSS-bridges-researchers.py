import requests
import json


def researcher1():
    """
    Смотрим на мосты, у которых более одного списочного параметра.
    Таких мостов быть не должно.
    """
    rss_bridge_url = 'http://localhost:3000/'

    params = {
        'action': 'list'
    }

    response = requests.get(rss_bridge_url, params=params)

    if response.status_code == 200:
        rss_data = response.text
        rss_data_dict: dict = json.loads(rss_data)
        list_of_bridges = rss_data_dict['bridges'].keys()
        list_of_multy = [el for el in list_of_bridges
                         if (type(rss_data_dict['bridges'][el]['parameters']) is list) and
                         len(rss_data_dict['bridges'][el]['parameters']) > 1]
        if list_of_multy:
            print('Мосты, у которых более одного списочного параметра: ', *list_of_multy, sep='\n')
        else:
            print('Мостов, у которых более одного списочного параметра, не существует')
    else:
        print("Ошибка при запросе к серверу RSS Bridge:", response.status_code)


def researcher2():
    """
    Смотрим на мосты, у которых списочные параметры не списки и не словари.
    Таких мостов быть не должно.
    """
    rss_bridge_url = 'http://localhost:3000/'

    params = {
        'action': 'list'
    }

    response = requests.get(rss_bridge_url, params=params)

    if response.status_code == 200:
        rss_data = response.text
        rss_data_dict: dict = json.loads(rss_data)
        list_of_bridges = rss_data_dict['bridges'].keys()
        list_of_multy = [el for el in list_of_bridges
                         if (type(rss_data_dict['bridges'][el]['parameters']) is not list) and
                         (type(rss_data_dict['bridges'][el]['parameters']) is not dict)]
        if list_of_multy:
            print('Список весьма странных фидов: ', *list_of_multy, sep='\n')
        else:
            print('Странных фидов нет')
    else:
        print("Ошибка при запросе к серверу RSS Bridge:", response.status_code)


def researcher3():
    """
    Смотрим на структуру фактора global в многофакторных мостах.
    """
    rss_bridge_url = 'http://localhost:3000/'

    params = {
        'action': 'list'
    }

    response = requests.get(rss_bridge_url, params=params)

    if response.status_code == 200:
        rss_data = response.text
        rss_data_dict: dict = json.loads(rss_data)
        list_of_bridges = rss_data_dict['bridges'].keys()
        for el in list_of_bridges:
            if type(rss_data_dict['bridges'][el]['parameters']) is dict:
                if 'global' in rss_data_dict['bridges'][el]['parameters']:
                    print('\033[94m{}:\033[0m'.format(el))
                    print(rss_data_dict['bridges'][el]['parameters']['global'])
                    print('\033[94m{}\n\n\033[0m'.format(len(rss_data_dict['bridges'][el]['parameters']['global'])))
    else:
        print("Ошибка при запросе к серверу RSS Bridge:", response.status_code)


def researcher4():
    """
    А здесь проверим есть ли списки в списках опций многофакторных мостов, и какие эти списки (все пустые).
    """
    rss_bridge_url = 'http://localhost:3000/'

    params = {
        'action': 'list'
    }

    response = requests.get(rss_bridge_url, params=params)

    if response.status_code == 200:
        rss_data = response.text
        rss_data_dict: dict = json.loads(rss_data)
        list_of_bridges = rss_data_dict['bridges'].keys()
        for el in list_of_bridges:
            if type(rss_data_dict['bridges'][el]['parameters']) is dict:
                obj = rss_data_dict['bridges'][el]['parameters']
                for elem in obj:
                    if type(obj[elem]) is list:
                        print(el, obj[elem])
    else:
        print("Ошибка при запросе к серверу RSS Bridge:", response.status_code)


def researcher5():
    """
    Мосты, содержащие несколько опций, которые тегаются списочными опциями.
    Сложные в обработке.
    """
    rss_bridge_url = 'http://localhost:3000/'

    params = {
        'action': 'list'
    }

    response = requests.get(rss_bridge_url, params=params)

    if response.status_code == 200:
        rss_data = response.text
        rss_data_dict: dict = json.loads(rss_data)
        list_of_bridges = rss_data_dict['bridges'].keys()
        global_count = 0
        for el in list_of_bridges:
            count = 0
            obj = rss_data_dict['bridges'][el]['parameters']
            if (type(obj) is list) and obj:
                for elem in obj[0]:
                    if type(obj[0][elem]) is dict:
                        for option in obj[0][elem]:
                            if type(obj[0][elem][option]) is dict:
                                count += 1
            if type(obj) is dict:
                for basic in obj:
                    if type(obj[basic]) is dict:
                        for elem in obj[basic]:
                            if type(obj[basic][elem]) is dict:
                                for option in obj[basic][elem]:
                                    if type(obj[basic][elem][option]) is dict:
                                        count += 1
            if count > 1:
                print(el, obj)
                global_count += 1
        if global_count:
            print(f'Всего непрятных странных фидов: {global_count}')
        else:
            print('Неприятных фидов нет')
    else:
        print("Ошибка при запросе к серверу RSS Bridge:", response.status_code)


def researcher6():
    """
    Мосты, внутренние опции которых тегаются параметром с более, чем одной списочной опцией.
    Таких мостов быть не должно.
    """
    rss_bridge_url = 'http://localhost:3000/'

    params = {
        'action': 'list'
    }

    response = requests.get(rss_bridge_url, params=params)

    if response.status_code == 200:
        rss_data = response.text
        rss_data_dict: dict = json.loads(rss_data)
        list_of_bridges = rss_data_dict['bridges'].keys()
        global_count = 0
        for el in list_of_bridges:
            obj = rss_data_dict['bridges'][el]['parameters']
            if (type(obj) is list) and obj:
                for elem in obj[0]:
                    if type(obj[0][elem]) is dict:
                        count = 0
                        for option in obj[0][elem]:
                            if type(obj[0][elem][option]) is dict:
                                count += 1
                        if count > 1:
                            print(el, obj, '\n\t\t', elem, obj[0][elem])
                            global_count += 1
            if type(obj) is dict:
                for basic in obj:
                    if type(obj[basic]) is dict:
                        for elem in obj[basic]:
                            if type(obj[basic][elem]) is dict:
                                count = 0
                                for option in obj[basic][elem]:
                                    if type(obj[basic][elem][option]) is dict:
                                        count += 1
                                if count > 1:
                                    print(el, obj, '\n\t\t', elem, obj[basic][elem])
                                    global_count += 1
        if global_count:
            print(f'Всего весьма странных фидов: {global_count}')
        else:
            print('Странных фидов нет')
    else:
        print("Ошибка при запросе к серверу RSS Bridge:", response.status_code)


def researcher7():
    """
    Мосты, в которых множественных контекст включает только 'global'.
    Таких мостов быть не должно.
    """
    rss_bridge_url = 'http://localhost:3000/'

    params = {
        'action': 'list'
    }

    response = requests.get(rss_bridge_url, params=params)

    if response.status_code == 200:
        rss_data = response.text
        rss_data_dict: dict = json.loads(rss_data)
        list_of_bridges = rss_data_dict['bridges'].keys()
        global_count = 0
        for el in list_of_bridges:
            obj = rss_data_dict['bridges'][el]['parameters']
            if type(obj) is dict:
                for basic in obj:
                    if type(obj[basic]) is dict:
                        if len(obj) == 1 and 'global' in obj:
                            global_count += 1
                            print(el, obj)
        if global_count:
            print(f'Всего весьма странных фидов: {global_count}')
        else:
            print('Странных фидов нет')
    else:
        print("Ошибка при запросе к серверу RSS Bridge:", response.status_code)


def researcher8():
    """
    Мосты, у которых один из элементов множественного контекста равен '' (пустой строке).
    Лучше бы таких мостов не было.
    """
    rss_bridge_url = 'http://localhost:3000/'

    params = {
        'action': 'list'
    }

    response = requests.get(rss_bridge_url, params=params)

    if response.status_code == 200:
        rss_data = response.text
        rss_data_dict: dict = json.loads(rss_data)
        list_of_bridges = rss_data_dict['bridges'].keys()
        global_count = 0
        for el in list_of_bridges:
            obj = rss_data_dict['bridges'][el]['parameters']
            if type(obj) is dict:
                for basic in obj:
                    if basic == '':
                        print(el, obj)
                        global_count += 1
        if global_count:
            print(f'Всего весьма неприятных фидов: {global_count}')
        else:
            print('Неприятных фидов нет')
    else:
        print("Ошибка при запросе к серверу RSS Bridge:", response.status_code)


if __name__ == '__main__':
    researcher4()
