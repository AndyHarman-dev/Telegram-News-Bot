from telegram import InlineKeyboardButton
import math
import copy

from app.misc.localization.lang_loc import make_localized_text


class Keyboard:
    _BACK_BUTTON_TEXT = "Back"

    _PREV_PAGE = "prev_page"
    _PREV_PAGE_TEXT = "⏪"

    _NEXT_PAGE = "next_page"
    _NEXT_PAGE_TEXT = "⏩"

    _LOCALE_KEYBOARD_KEY_PATH = "misc.keyboard"

    def __init__(self, items, max_buttons_per_page=10,
                 back_button_callback_data=None, start_page=0, transform_keyboard_data_func=lambda x: x,
                 lang_code="en"):
        self.items = items
        self.max_buttons_per_page = max_buttons_per_page
        self.current_page = start_page
        self.transform_keyboard_data_func = transform_keyboard_data_func
        self.back_button_callback_data = back_button_callback_data

        self._lang_code = lang_code

    def __deepcopy__(self, memodict={}):
        # Allow to deepcopy keyboard
        if memodict is None:
            memodict = {}

        cls = self.__class__

        # Create a new instance
        new_keyboard = cls(self.items, self.max_buttons_per_page,
                           self.back_button_callback_data, 0,
                           self.transform_keyboard_data_func, self._lang_code)
        return new_keyboard

    async def horizontal_buttons(self):
        # Asynchronously translate button texts and create buttons
        buttons = [
            InlineKeyboardButton(await self.transform_button_text(f"{text}", data),
                                 callback_data=self.transform_keyboard_data_func(data))
            for text, data in self.items.items()
        ]

        back_button = await self._try_to_get_back_button()
        if back_button is not None:
            buttons.append(back_button)

        return [buttons]

    async def vertical_buttons(self):
        # Asynchronously translate button texts and create buttons
        buttons = [
            [InlineKeyboardButton(await self.transform_button_text(f"{text}", data),
                                  callback_data=self.transform_keyboard_data_func(data))]
            for text, data in self.items.items()
        ]

        back_button = await self._try_to_get_back_button()
        if back_button is not None:
            buttons.append([back_button])

        return buttons

    async def paginated_buttons(self):
        """Create a paginated keyboard layout with navigation arrows if necessary."""
        paginated_items = list(self.items.items())
        pages = math.ceil(len(paginated_items) / self.max_buttons_per_page)

        # Determine the range of buttons for the current page
        start_index = self.current_page * self.max_buttons_per_page
        end_index = start_index + self.max_buttons_per_page
        page_items = paginated_items[start_index:end_index]

        # Create buttons for the current page
        keyboard = [[InlineKeyboardButton(await self.transform_button_text(f"{text}", data),
                                          callback_data=self.transform_keyboard_data_func(data))]
                    for text, data in page_items]

        # Add navigation buttons if there are multiple pages
        if pages > 1:
            navigation_buttons = []
            # Add 'previous page' button if not on the first page
            if self.current_page > 0:
                navigation_buttons.append(InlineKeyboardButton(self._PREV_PAGE_TEXT, callback_data=self._PREV_PAGE))
            # Add 'next page' button if not on the last page
            if self.current_page < pages - 1:
                navigation_buttons.append(InlineKeyboardButton(self._NEXT_PAGE_TEXT, callback_data=self._NEXT_PAGE))
            keyboard.append(navigation_buttons)

        # Add the back button
        back_button = await self._try_to_get_back_button()
        keyboard.append([back_button]) if back_button is not None else None  # Do nothing if there is no back button

        return keyboard

    def handle_page_navigation(self, callback_data):
        """Adjust the current page based on the navigation button pressed."""
        if callback_data == self._NEXT_PAGE:
            self.current_page += 1
        elif callback_data == self._PREV_PAGE:
            self.current_page -= 1

    async def get_keyboard(self):
        """Get the keyboard layout based on the number of items."""
        if len(self.items) <= self.max_buttons_per_page:
            return await self.horizontal_buttons() if len(self.items) == 1 else await self.vertical_buttons()
        else:
            return await self.paginated_buttons()

    async def set_language_code(self, new_language_code):
        self._lang_code = new_language_code

    async def transform_button_text(self, key, data=None):
        from app.bot.telegram_bot import ChatGPTTelegramBot
        locale = await make_localized_text(self._lang_code)
        sub_path = ChatGPTTelegramBot.menu_generalization(key.lower())
        return await locale.get_text(f"{self._LOCALE_KEYBOARD_KEY_PATH}.{sub_path}")

    async def _try_to_get_back_button(self):
        if self.back_button_callback_data is not None:
            locale = await make_localized_text(self._lang_code)
            self._BACK_BUTTON_TEXT = await locale.get_text(f"{self._LOCALE_KEYBOARD_KEY_PATH}.back")
            return InlineKeyboardButton(self._BACK_BUTTON_TEXT,
                                        callback_data=self.transform_keyboard_data_func(self.back_button_callback_data))
        else:
            return None


class TextRetrievedKeyboard(Keyboard):
    async def vertical_buttons(self):
        # Asynchronously translate button texts and create buttons
        text_buttons = [await self.transform_button_text(f"{text}", None) for text in self.items]

        buttons = [
            [InlineKeyboardButton(text_button, switch_inline_query_current_chat=text_button)]
            for text_button in text_buttons
        ]

        back_button = await self._try_to_get_back_button()
        if back_button is not None:
            buttons.append([back_button])

        return buttons

    async def horizontal_buttons(self):
        # Asynchronously translate button texts and create buttons
        text_buttons = [await self.transform_button_text(f"{text}", None) for text in self.items]

        buttons = [
            InlineKeyboardButton(text_button, switch_inline_query_current_chat=text_button)
            for text_button in text_buttons
        ]

        back_button = await self._try_to_get_back_button()
        if back_button is not None:
            buttons.append(back_button)

        return [buttons]


class HelpKeyboard(Keyboard):
    _LOCALE_KEYBOARD_KEY_PATH = 'misc.help_keyboard'
