# an interface that allows user to work with the database

from app.database.db_tariff import TariffManager
from flask import Flask, render_template






# a class that represents the whole interface of the database
class DBInterface:

    def __init__(self):
        pass

    # a dictionary of query functions
    _query_functions = {
        'tariffs': TariffManager.get_tariffs_info,
        # other tables are here ...
    }

    # Query the database and return the data in html table format
    @staticmethod
    def get_data_html(table_name=None, table_width=70):
        if table_name not in DBInterface._query_functions:
            raise ValueError(f'Invalid table name: {table_name}')
        query_function = DBInterface._query_functions[table_name]
        data = query_function()
        return OutputFormat.render_to_html(data=data, width=table_width)




# prerequisite for checking the work of code. Will be deleted after it's done
app = Flask(__name__, template_folder='./')


# rendering engine of choice for the data you want to get
class OutputFormat:

    def __init__(self):
        pass

    # render the data via jinja2 template
    @staticmethod
    @app.route('/')
    def render_to_html(data, width=70):
        return render_template('template.html', new_data=data, new_width=width)


# test of how it works. Not a part of this interface
with app.app_context():
    print(DBInterface.get_data_html(table_name='tariffs', table_width=100))
