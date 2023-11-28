from typing import Final

MAX_QUOTATIONS_IN_LINE = 2


def read_config_to_dict(config_file: str):
    data_dict = {}
    with open(config_file, 'r') as file:
        b_accumulating_string = False  # Flag to distinct whether we are gathering a multiline string or not
        accumulated_key: str = ''
        for line in file:
            if '#' in line and not b_accumulating_string:  # Ignore sharp comments that aren't in a quotients
                continue

            if '"' in line and line.count('"') < MAX_QUOTATIONS_IN_LINE:  # If there is quotes, then we expect a
                # multiline string and do not strip any symbols
                if not b_accumulating_string:
                    b_accumulating_string = True
                    if '=' in line:
                        accumulated_key, value = line.split('=', 1)  # split line into key and value
                        data_dict[accumulated_key] = value
                        continue
                else:
                    b_accumulating_string = False
                    data_dict[accumulated_key] += line  # Add the last line
                    continue

            if b_accumulating_string:
                data_dict[accumulated_key] += line
                continue

            line = line.strip()  # remove leading/trailing whitespace
            if '=' in line:  # check if line is in correct format
                key, value = line.split('=', 1)  # split line into key and value
                data_dict[key] = value  # add key-value pair to dictionary
    return data_dict


# Dict in which config is gathered
CONFIG_DICT = read_config_to_dict("config.txt")
