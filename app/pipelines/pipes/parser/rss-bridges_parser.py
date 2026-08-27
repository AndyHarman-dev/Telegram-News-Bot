import requests
import json
import csv
from datetime import datetime
from itertools import product
#from app.header import PROJECT_ROOT
from io import FileIO
from pathlib import Path

from app.misc.paths import Paths


def abstract_way_in_all_systems_to(way: str):
    return Paths.ROOT_DIR + f'/app/pipelines/pipes/parser/{way}'


class GetterRSSBridges:
    _url = 'http://localhost:3000/'
    file_name = 'sites_with_rss_bridges.csv'

    def __init__(self, big_restrict=True, white=True, all_feeds=False, rate=True, best=True, individual=True):
        self.all_data, self.bridges = self._all_bridges()
        self.is_not_calling_yet = True
        self.current_bridge = ''
        
        self.restrict_big_bridges = big_restrict
        self.restrict_number = 10

        self.white_list_using = white
        self.white_list_file = abstract_way_in_all_systems_to('white_list.csv')
        self.white_list = set()
        if self.white_list_using:
            self.white_list = self._reed_to_csv_white_list()

        self.get_all_feeds_data = all_feeds
        self.all_data_feeds = abstract_way_in_all_systems_to('rss_name.csv')

        self.evaluated_whitelist_using = rate
        self.evaluated_whitelist_file = abstract_way_in_all_systems_to('evaluated_whitelist.csv')
        self.evaluated_whitelist = {}
        if self.evaluated_whitelist_using:
            self.read_evaluated_list()

        self.best_bridges_selected = best
        self.best_bridges_quota = 3  # 0 or less for unlimited rss-feed count quota for 5-rated bridges

        self.bridges_with_individual_sets_existing = individual
        self.bridges_with_individual_sets_file = \
            FileIO(Path(abstract_way_in_all_systems_to('individual_sets_for_bridges.json')).absolute(), "rb")
        self.bridges_with_individual_sets = {}
        if self.bridges_with_individual_sets_existing:
            self.bridges_with_individual_sets = json.load(self.bridges_with_individual_sets_file)

    def _all_bridges(self):
        params = {
            'action': 'list'
        }
        response = requests.get(self._url, params=params)

        if response.status_code == 200:
            rss_data = response.text
            rss_data_dict: dict = json.loads(rss_data)
            list_of_bridges = rss_data_dict['bridges'].keys()
            return rss_data_dict, list(list_of_bridges)
        raise f"Response status isn\'t 200 Error {response.status_code}"

    def gen_feeds(self):
        for bridge_name in self.bridges:
            self.current_bridge = bridge_name
            if self.get_all_feeds_data:
                self._write_to_csv_all_feeds(bridge_name, self.all_data['bridges'][bridge_name]['uri'])
            #if self.white_list_using and bridge_name not in self.white_list:
            #    continue
            if (self.evaluated_whitelist_using and
                    self.evaluated_whitelist.get(self.all_data['bridges'][bridge_name]['uri'], 0) < 4):
                continue
            bridge_obj = self.all_data['bridges'][bridge_name]['parameters']
            bridge_option = [[f'&bridge={bridge_name}']]
            if type(bridge_obj) is list:
                if not bridge_obj:
                    self._write_to_csv(bridge_option[0][0], bridge_name)
                    continue
                self._feed_object(bridge_obj, prev=bridge_option)
                continue
            if type(bridge_obj) is not dict: # this condition will never be triggered, added just in case
                continue
            if 'global' in bridge_obj:
                global_param = self._feed_object(bridge_obj, ex_key='global', finite=False)
                if type(global_param) is not list:
                    continue
            else:
                global_param = []
            global_param = bridge_option + global_param
            for key in bridge_obj:
                if key == 'global':
                    continue
                self._feed_object(bridge_obj, global_param, key)

    def _write_to_csv(self, params: str = '', bridge_name: str = 'SomeBridge'):
        data = self._url + '?action=display' + params + '&format=Mrss'
        data = data.replace(' ', '+')
        if self.is_not_calling_yet:
            mode = 'w'
            self.is_not_calling_yet = False
        else:
            mode = 'a'
        with open(self.file_name, mode=mode, newline='', encoding='utf-8') as file:
            writer = csv.writer(file, delimiter=';')
            writer.writerow([bridge_name, data, datetime.now().strftime('%Y-%m-%d')])

    def _write_to_csv_all_feeds(self, bridge: str = '', url_bridge: str = ''):
        with open(self.all_data_feeds, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file, delimiter=';')
            writer.writerow([bridge, url_bridge])

    def _reed_to_csv_white_list(self):
        unique_first_column = set()
        with open(self.white_list_file, newline='', encoding='utf-8') as csvfile:
            csvreader = csv.reader(csvfile, delimiter=';')
            # next(csvreader) - if the headline appears
            for row in csvreader:
                unique_first_column.add(row[0])
        return unique_first_column

    def _feed_object(self, obj: list | dict, prev: list = (), ex_key: str = '', finite: bool = True) -> list | int:
        list_of_lists = []
        if prev:
            list_of_lists.extend(prev.copy())
        if ex_key and ex_key != 'global':
            list_of_lists.append([f'&context={ex_key}'])
        new_res = self._appropriate_feed_elem(ex_key, obj)
        if type(new_res) is not list:
            return new_res
        list_of_lists.extend(new_res)
        if finite:
            result = self.create_prod_list(list_of_lists)
            for val in result:
                self._write_to_csv(val, self.current_bridge)
        else:
            return list_of_lists

    def _appropriate_feed_elem(self, ex_key: str, elem: list | dict) -> list | int:
        if (type(elem) is not list) and (ex_key != '') and (type(elem[ex_key]) is list):
            return [['']]
        result = []
        if type(elem) is dict:
            iter_for_ = elem[ex_key]
        else:
            iter_for_ = elem[0]
        for key in iter_for_:
            if self._this_is_values_elem_list(iter_for_[key]):
                new_data = self._get_values_from_elem_list(key, iter_for_[key])
                if self.bridges_with_individual_sets_existing:
                    new_data = self._individual_clearing(new_data, key)
                result.append(new_data)
            elif self._this_is_limit(key, iter_for_[key]):
                val = '&' + key + '=' + str(self._get_default_value(iter_for_[key]))
                result.append([val])
            elif self._this_is_required(iter_for_[key]):
                return 0
        if result:
            return result
        return [['']]

    def _individual_clearing(self, _data: list, key_name: str):
        if not self.bridges_with_individual_sets.get(self.current_bridge, False):
            return _data
        if not self.bridges_with_individual_sets[self.current_bridge].get("viewed_feeds", False):
            return _data
        if not self.bridges_with_individual_sets[self.current_bridge]["viewed_feeds"].get("restrict", False):
            return _data
        if self.bridges_with_individual_sets[self.current_bridge]["viewed_feeds"]["topic"] != key_name:
            return _data
        for elem in self.bridges_with_individual_sets[self.current_bridge]["viewed_feeds"]["names"]:
            try:
                _data.remove('&'+key_name+'='+str(elem))
            except:
                print(f'Topic {elem} cannot be deleted as it does not exist!')
        return _data

    @staticmethod
    def _this_is_values_elem_list(obj: dict):
        for key in obj:
            if type(obj[key]) is dict:
                return True
        return False

    @staticmethod
    def _get_values_from_elem_list(ex_key: str, obj: dict):
        for key in obj:
            if type(obj[key]) is dict:
                result = []

                def recurse(_key: str, items):
                    for _, value in items.items():
                        if isinstance(value, dict):
                            recurse(_key, value)
                        else:
                            val = '' if not value else value
                            result.append('&'+_key+'='+str(val))

                recurse(ex_key, obj[key])
                return result
        return False  # "False" must never be the result of this function

    @staticmethod
    def _this_is_required(obj: dict):
        if 'required' not in obj:
            return False
        return obj['required']

    @staticmethod
    def _this_is_limit(key: str, obj: dict):
        if key.lower() == 'limit':
            return True
        if 'type' in obj and obj['type'] == "number" and 'required' in obj:
            return True
        if 'name' not in obj:
            return False
        return obj['name'].lower() == 'limit'

    @staticmethod
    def _get_default_value(obj: dict):
        if 'defaultValue' in obj:
            return int(obj['defaultValue'])
        return 10

    def create_prod_list(self, list_of_lists: list):
        if self.restrict_big_bridges and self.count_elem_in_prod(list_of_lists) > self.restrict_number:
            best_value = self.best_bridges_checking()
            if not best_value:
                print(f'\033[94mThe bridge {self.current_bridge} \033[0m'
                      f'\033[94mcontains too many variants of rss-feeds: {self.count_elem_in_prod(list_of_lists)}.\n\033[0m'
                      f'\033[94mOnly the first feed variant (presumably the default feed) has been added.\033[0m')
                return [''.join(items[0] for items in list_of_lists)]
            print(f'\033[94mThe bridge {self.current_bridge} \033[0m'
                  f'\033[94mcontains too many variants of rss-feeds: {self.count_elem_in_prod(list_of_lists)}.\n\033[0m'
                  f'\033[94mOnly the first {self.best_bridges_quota} feed variant has been added.\033[0m')
            combined = product(*list_of_lists)
            result = []
            for _ in range(self.best_bridges_quota):
                result.append(''.join(next(combined)))
            return result
        combined = product(*list_of_lists)
        result = [''.join(items) for items in combined]
        return result

    @staticmethod
    def count_elem_in_prod(list_of_lists: list):
        result = 1
        for el in list_of_lists:
            result *= len(el)
        return result

    def best_bridges_checking(self):
        if not self.evaluated_whitelist_using or not self.best_bridges_selected:
            return False
        return self.evaluated_whitelist.get(self.all_data['bridges'][self.current_bridge]['uri'], 0) == 5

    def read_evaluated_list(self):
        with open(self.evaluated_whitelist_file, newline='', encoding='utf-8') as csvfile:
            csvreader = csv.reader(csvfile, delimiter=';')
            # next(csvreader) - if the headline appears
            for row in csvreader:
                self.evaluated_whitelist.update({row[0]: int(row[1])})
            print(self.evaluated_whitelist)


if __name__ == '__main__':
    feeds_getter = GetterRSSBridges()
    feeds_getter.gen_feeds()
