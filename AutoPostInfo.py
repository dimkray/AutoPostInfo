# -*- coding: utf-8 -*-
import json
import csv
import os
import time
import requests

# Настройка пейджинга
sPaging = {}
sPaging['paging'] = {}
sPaging['paging']['item'] = 0   # Страница
sPaging['paging']['rows'] = 3  # Число items

# Путь к действующему API
sProm = 'https://dsvc-api.taxcom.ru/v1/'
sEtalon = 'etalons.csv'
sInfo = sProm + 'info'

# Итоговая таблица
Posts = []


# Класс профилирования - замеры времени
class Profiler(object):
    def __enter__(self):
        self._startTime = time.time()

    def __exit__(self, type, value, traceback):
        if time.time() - self._startTime > 1:
            print('Время выполнения {:.3f} сек.'.format(time.time() - self._startTime))

# класс работы с файлами
class File:
    # Запись лога
    def log(s):
        from datetime import datetime
        with open('post.log', 'a', encoding='utf-8') as f:
            s = s.replace('\n', ' \ ')
            f.write('%s: %s\n' % (str(datetime.today()), s))
        #print(s)

    # Функция проверки существования файла
    def Exists(path):
        try:
            os.stat(path)
        except OSError:
            return False
        return True

    # Функция записи словаря
    def Save(dictionary, name):
        try:
            f = open(name + '.json', 'w', encoding='utf-8')
            json.dump(dictionary, f, sort_keys=False, ensure_ascii=False)
            f.close()
            return True
        except Exception as e:
            File.log(name + '.json - ' + str(e))
            return False

    # Функция загрузки словаря
    def Load(name):
        try:
            dictionary = {}
            if File.Exists(name + '.json') == False: return dictionary
            f = open(name + '.json', 'r', encoding='utf-8')
            dictionary = json.load(f)
            return dictionary
        except Exception as e:
            File.log(name + '.json - ' + str(e))
            return dictionary

    # Ручное чтение csv-файла
    def CSVReader(fullname):
        data = []
        with open(fullname, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile, delimiter=';', quotechar='"')
            for row in reader:
                data.append(row)
        return data

# Класс запросов
class HTTP:
    # Получение html/основного текста по запросу
    def GetData(shttp, stext='', textparam='', params={}):
        try:
            if len(textparam) > 0:
                params[textparam] = stext
            status = 0; d = '' # Данные для ответа
            if len(params) > 0:
                r = requests.get(shttp, params=params)
            else:
                r = requests.get(shttp)
            status = r.status_code
            if status == requests.codes.ok:
                d = r.text
            if status != requests.codes.ok:
                return '#problem: ' + str(r.status_code)
            else:
                return d
        except Exception as e:
            print('#bug: ' + str(e))

            # Использование метода POST
    def PostData(shttp, djson):
        try:
            if len(djson) > 0:
                r = requests.post(shttp, json=djson)
            else:
                r = requests.post(shttp)
            status = r.status_code
            d = ''
            if status == requests.codes.ok: d = r.text
            return d
        except Exception as e:
            print('#bug: ' + str(e))

    # типовой POST-запрос
    def post(url, sDict):
        try:
            File.log('POST: %s - json: %s' % (url, str(sDict)))
            dPost = json.loads(HTTP.PostData(url, sDict))
            File.log('REQUEST: ' + str(dPost))
            return dPost
        except Exception as e:
            File.log('BUG! ' + str(e))
            return {}

# Сложение словарей
def DictsAdd(dict1, dict2):
    d = dict1.copy()
    d.update(dict2)
    return d

# Класс тестирования
class Test:
    # Сравнение result Json с эталонным Json (только по одному item)
    def ItemEqual(itemTest, itemEtalon, section='result'):
        diff = {}
        if itemTest == itemEtalon:
            return diff
        if not isinstance(itemTest, dict) or not isinstance(itemEtalon, dict):
            diff[section] = 'Значения не равны: %s <> %s' % (str(itemTest), str(itemEtalon))
            return diff
        if itemTest is None or itemEtalon is None:
            diff[section] = 'Значения не равны: %s <> %s' % (str(itemTest), str(itemEtalon))
            return diff
        for key in itemEtalon:
            if key not in itemTest:
                diff[section+'.'+key] = 'Не найден параметр!'
            else:
                if itemTest[key] != itemEtalon[key] and section != 'result':
                    diff[section+'.'+key] = 'Значения не равны: %s <> %s' % (str(itemTest[key]), str(itemEtalon[key]))
        for key in itemTest:
            if key not in itemEtalon:
                diff[section+'.'+key] = 'Найден лишний параметр!'
        return diff

    # Сравнение result Json с эталонным Json
    def DictEqual(test, etalon):
        diff = {}
        if test == etalon: return diff
        if test is None or etalon is None:
            diff['result'] = '%s <> %s' % (str(test), str(etalon))
            return diff
        diff = Test.ItemEqual(test, etalon)
        for key in etalon:
            if key == 'items':
                i = 0
                for item in test[key]:
                    diff = DictsAdd(diff, Test.ItemEqual(item, etalon['items'][i], section = 'items[%i]' % i))
                    i += 1
            else:
                if key in test:
                    diff2 = Test.ItemEqual(test[key], etalon[key], section = key)
                    diff = DictsAdd(diff, diff2)
                else:
                    diff[key] = 'Не найден параметр!'
        for key in test:
            if key not in etalon:
                diff[key] = 'Найден лишний параметр!'
        return diff

    # Сравнение с эталонами
    def Equal(method, djson, dapi):
        rez = ''
        for iapi in Etalons:
            if method == iapi[0]:
                diff = Test.DictEqual(djson, json.loads(iapi[1]))
                if diff != {}: return 'Входящие параметры отличаются! ' + json.dumps(diff, sort_keys=False, ensure_ascii=False)
                if dapi['status'] == False: return 'Метод не работает!'
                diff = Test.DictEqual(dapi['result'], json.loads(iapi[3]))
                if diff != {}: return 'Ответы отличаются! ' + json.dumps(diff, sort_keys=False, ensure_ascii=False)
                return 'Всё хорошо!'
        return 'Метод %s не найден!' % method

# Создание json-запроса
def createJson(sModel, sMethod='model', bList=False):
    crJson = {}
    if bList: crJson = sPaging.copy() # если есть признак list
    if sModel in dApi: # если есть настройки модели
        if sMethod in dApi[sModel]: # если есть настройки метода
            for key in dApi[sModel][sMethod]:
                crJson[key] = dApi[sModel][sMethod][key]
        else:
            for key in dApi[sModel]['other']:
                crJson[key] = dApi[sModel]['other'][key]
    else:
        if sMethod in dApi['other']:
            for key in dApi['other'][sMethod]:
                crJson[key] = dApi['other'][sMethod][key]
        else:
            for key in dApi['other']['other']:
                crJson[key] = dApi['other']['other'][key]
    return crJson

# Проверка API
def testApi(sMethod, dJson={'id':'112'}):
    dapi = {}
    dapi['api'] = sProm + sMethod
    dapi['json'] = json.dumps(dJson, sort_keys=False, ensure_ascii=False)
    sUrl = dapi['api']
    try:
        dReq = {'status': False}
        with Profiler() as p:
            dReq = HTTP.post(sUrl, dJson) # POST-запрос
        if 'status' in dReq:
            dapi['status'] = dReq['status']
        else:
            print('- STATUS BUG! - %s: %s' % (sMethod, str(dReq)))
            return dReq
        dapi['result'] = dReq['result']
        if dapi['result'] != 'Метод не должен быть реализован.':
            if dapi['status']: # если ок
                print('+ OK - %s' % sMethod)
                dapi['diff'] = Test.Equal(dapi['api'], dJson, dReq)
                if dapi['result'] is not None or dapi['result'] != '':
                    dapi['result'] = json.dumps(dapi['result'], sort_keys=False, ensure_ascii=False)
                print('Результат сравнения: ' + dapi['diff'])
            else: # если ошибка
                print('- BUG! - %s: %s' % (sMethod, dapi['result']))
                dapi['diff'] = 'Сравнение пропущено!'
            Posts.append(dapi) # добалвение для csv
    except Exception as e:
        print('BUG! ' + str(e))
        File.log('BUG! ' + str(e))
        pass
    return dReq

dQuery = File.Load('query') # список запросов

# получение текущего id по инн
def getid(query):
    if query in dQuery: return dQuery[query]
    jquery = {'paging': {'item': 0, 'rows': 3}, 'query': query}
    result = HTTP.post(sProm + 'company/search', jquery)
    if result['status']:
        items = result['result']['items']
        if items is not None and items != []:
            item = items[0]
            dQuery[query] = item['id']['value']
            return item['id']['value']
        else:
            return None
    else:
        return None

# Настройки автопроверки API ('other' всегда должен быть!)
dApi = { 'company': {'search': {'query': 'такском'},
                     'model-list': {'filters': {'inn': '3803100054'}},
                     'other': {'id': getid('3441010551')}},
         'organization': {'model': {'id': getid('3441010551')}, # для получения модели
                          'event': {'id': getid('3441010551')}, # для получения определённого свойства
                          'address-history': {'id': getid('3804999814')},
                          'invalid-address': {'id': getid('3250517943')},
                          'invalid-data': {'id': getid('3442112524')},
                          'unfair-compliant-inclusion': {'id': getid('1901117599')},
                          'unfair-compliant': {'id': getid('6686023835')},
                          'established': {'id': getid('7744001497')},
                          'established-history': {'id': getid('7744001497')},
                          'planned-inspection': {'id': getid('0101002156')},
                          'unplanned-inspection': {'id': getid('0105025965')},
                          'trademarks': {'id': getid('7826014923')},
                          'founder_in': {'id': getid('7712040126')},
                          'leader_in': {'id': getid('4205253730')},
                          'iplegallist': {'id': getid('4821003030')},
                          'iplegal': {'id': getid('5903037635')},
                          'headed': {'id': getid('2312100526')},
                          # 'founder': {'id': getid('7713073050')},
                          'founder-history': {'id': getid('7704211201')},
                          'leader': {'id': getid('3803100054')},
                          'leader-history': {'id': getid('6166016158')},
                          'change-address-decision': {'id': getid('7709305252')},
                          'source-file': {'id': getid('5507245279')},
                          'okved': {'id': getid('7730161765')},
                          'license': {'id': getid('7704211201')},
                          'other': {'id': getid('7704211201')}}, # для получения всех остальных свойств
         'entrepreneur': {'model': {'id': getid('641901324491')},
                          'model-list': {'filters': {'inn':'250500383158'}},
                          'established': {'id': getid('190200291847')},
                          'established-history': {'id':getid('190200291847')},
                          'license': {'id': getid('781612806543')},
                          'okved': {'id': getid('772333709256')},
                          'planned-inspection': {'id': getid('024700158025')},
                          'unfair-compliant-inclusion': {'id': getid('190122108234')},
                          'unfair-compliant': {'id': getid('190122108234')},
                          'unplanned-inspection': {'id': getid('251100055570')},
                          'source-file': {'id': getid('222500327630')},
                          'headed': {'id': getid('190200291847')},
                          'leader_in': {'id': getid('7712040126')},
                          'other': {'id': getid('641901324491')}},
         'person': {'model': {'id': '4503420'},
                    'established': {'id': '4503420'},
                    'established-history': {'id': '4503420'},
                    'disqualified': {'id': '36059'},
                    'other': {'id': getid('770474061704')}},
         'disqualified': {'model-list': {'filters': {'lastname': 'ФЕДОРОВА', 'firstname': 'ИРИНА'}},
                          'other': {'id': getid('770474061704')}},
         'disqualifiedperson': {'model-list': {'filters': {'inn': '7720753667'}},
                                'other': {'id': getid('770474061704')}},
         'expired-passport': {'model-list': {'filters': {'series': '5203', 'number': '783664'}},
                              'other': {'id': getid('770474061704')}},
         'founder': {'massfounder': {'id': '13365974'},
                     'other': {'id': '3645256'}},
         'leader': {'massleader': {'id': '21931213'},
                    'other': {'id': '2243524'}},
         'massaddress': {'model-list': {'filters': {'street':'УЛЬЯНОВЫХ УЛ'}},
                         'other': {'id': '111'}},
         'massfounders': {'model-list': {'filters': {'inn': '010600636563'}},
                          'other': {'id': '111'}},
         'massleaders': {'model-list': {'filters': {'inn': '010501275725'}},
                         'other': {'id': '111'}},
         'planned-inspections': {'model-list': {'filters': {'id': '150500007456'}},
                                 'other': {'id': '150500007456'}},
         'unplanned-inspections': {'model-list': {'filters': {'id': '160601387571'}},
                                   'other': {'id': '160601387571'}},
         'massleader': {'model-list': {'filters': {'inn': '772023555408'}},
                        'other': {'id': '111'}},
         'rsmp': {'model-list': {'filters': {'inn': '232000373667'}},
                  'other': {'id': '111'}},
         'operators': {'model-list': {'filters': {'inn': '7704211201'}},
                       'other': {'id': '111'}},
         'trademarks': {'model-list': {'filters': {'ogrn': '1027700071530'}},
                        'other': {'id': '111'}},
         'okved-group': {'model-list': {},
                         'other': {'id': '111'}},
         'other': {'model-list': {'filters': {}},
                   'other': {'id': getid('770474061704')}} }


# ------------------------------------------------------------
# Автотестирование всего API по данным API-Info
# ------------------------------------------------------------

File.log('------------------------------------------')
File.log('Старт AutoPostInfo 0.3')
File.log('')

# Массив эталонных значений
Etalons = File.CSVReader(sEtalon)

# Получение списка моделей
Dict = json.loads(HTTP.GetData(sInfo))
if Dict['status']:
    mList = Dict['result']['items']
else:
    File.log('Ошибка получения списка моделей!')
for model in mList:
    File.log('Работа с моделью [%s]' % model)
    # Описание модели
    sURL = '%s/%s/model' % (sInfo, model)
    dStruct = json.loads(HTTP.GetData(sURL))
    if dStruct['status']:
        dModel = testApi('%s/model' % model, createJson(model,'model'))
        dModelList = testApi('%s/model-list' % model, createJson(model,'model-list', True))
        if model.lower() == 'company':
            dModelList = testApi('%s/search' % model, createJson(model,'search', True))
    else:
        File.log('BUG! Данных модели нет!')
    # свойства модели
    sURL = '%s/%s/properties' % (sInfo, model)
    dProp = json.loads(HTTP.GetData(sURL))
    if dProp['status']:
        for item in dProp['result']['items']: # проход по всем свойствам
            File.log('Свойство "%s" :' % item['name'])
            dPr = testApi('%s/property/%s' % (model, item['name']), createJson(model, item['name']))
            dPrList = testApi('%s/property-list/%s' % (model, item['name']), createJson(model, item['name'], True))
    else:
        File.log('Свойства не найдены!')
    # связи модели
    sURL = '%s/%s/relations' % (sInfo, model)
    dRl = json.loads(HTTP.GetData(sURL))
    if dRl['status']:
        for item in dRl['result']['items']:
            File.log('Связь "%s" -> модель [%s]' % (item['name'], item['relatedModel']))
            dRlList = testApi('%s/relation/%s' % (model, item['name']), createJson(model, item['name'], True))
    else:
        File.log('Связи не найдены!')
    File.log('')

    File.Save(dQuery, 'query') # сохраняем все запросы

# Запись результатов
from datetime import date
with open('results_%s.csv' % str(date.today()), "w") as f:
    writer = csv.DictWriter(f, delimiter=';', fieldnames=['api','json','status','result','diff'])
    writer.writeheader()
    writer.writerows(Posts)
    File.log('Загруженные данные успешно записаны в файл results.csv!')


