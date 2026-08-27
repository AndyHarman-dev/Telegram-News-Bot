from telegram import Update
from telegram.ext import ContextTypes
from app.bot.states import state


class ItemManagementState(state.State):
    pass


# TODO : Rethink the idea of this class and probably don't use it as it's primary goal for the keyboard expansion only
# class VerticalListState(state.State):
#     """
#     Vertical list state is a state which displays buttons in a vertical way
#     """
#
#     def __init__(self, display_message: str, keyboard_layout):
#
#         # Expands the initial keyboard layout to make every item separate thus making it vertical
#         expanded_layout = None
#         if keyboard_layout is not None:
#             expanded_layout = self._expand_keyboard_layout(keyboard_layout)
#
#         super().__init__(display_message, expanded_layout)
#
#     @staticmethod
#     def _expand_keyboard_layout(keyboard_list):
#         """
#         Converts a list of keyboard layout dictionaries into a
#         list of individual key-value pair dictionaries.
#
#         Parameters:
#         keyboard_list (list of dict): A list where each item is a
#         dictionary representing a keyboard layout.
#
#         Returns:
#         list of dict: A new list where each dictionary contains a
#         single key-value pair from the original keyboard list.
#         """
#         # Initialize a new list to store the expanded keyboard layout
#         expanded_layout = []
#
#         # Iterate over each dictionary in the keyboard list
#         for keyboard_dict in keyboard_list:
#             # Iterate over each key-value pair in the dictionary
#             for key, value in keyboard_dict.items():
#                 # Create a new dictionary for each item and append to the expanded layout
#                 expanded_layout.append({key: value})
#
#         return expanded_layout
