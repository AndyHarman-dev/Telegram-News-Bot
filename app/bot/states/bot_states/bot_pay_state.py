import json
import logging
from abc import ABC, abstractmethod

from app.bot.states import state

from telegram import LabeledPrice, Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from app.database.db_chat import ChatManager
from app.database.db_translation import TranslationManager
from app.misc.keyboard import Keyboard
from app.misc.localization.lang_loc import make_localized_text
from app.misc.log_helper import LogHelper

from app.database.db_tariff import TariffManager

LOG_PAY_STATE = LogHelper(__name__, "Pay State Thread")


# Interface for shared state
class IPaySharedState(ABC):
    """This interfaces aims for an implementation of a
    shared information between states that can be freely accessed.
    Thread safety is upon the user"""

    @abstractmethod
    def set_tariff(self, data):
        pass

    @abstractmethod
    def get_tariff(self):
        pass

    @abstractmethod
    def set_provider_code(self, data):
        pass

    @abstractmethod
    def get_provider_code(self):
        pass

    @abstractmethod
    def set_currency(self, data):
        pass

    @abstractmethod
    def get_currency(self):
        pass

    @abstractmethod
    def set_prices(self, data):
        pass

    @abstractmethod
    def get_prices(self):
        pass


class BotPayState(state.State):
    class PayKeyboard(Keyboard):
        async def transform_button_text(self, key, data=None):
            return key.upper()

    _KEYBOARD_CLASS = PayKeyboard

    class BasePayState(state.State.BaseSubState, ABC):

        """Base substate class for substates of this main state"""

        def __init__(self, *args):
            super().__init__(*args)
            self.shared_data = None

        def set_shared_data(self, data):
            self.shared_data = data

    class ChooseTariff(BasePayState):
        """State for choosing a tarif"""

        async def handle_enter_state(self, update, context):
            pass

        async def handle_on_user_message(self, update, context):
            pass

        async def handle_callback_query(self, update, context):
            self.shared_data.set_tariff(update.callback_query.data)

            next_state = BotPayState.ChooseProvider(self.state)
            next_state.set_shared_data(self.shared_data)

            self.state.change_state(update, context, next_state)

            providers_list = TariffManager.get_payment_methods()
            self.state._keyboard = self.state._instantiate_default_keyboard(
                providers_list)  # redraw keyboard with the new data

            await self.state.transition_to_state(update, context, self.state.state_name)

    class ChooseProvider(BasePayState):
        """State for choosing a provider"""

        async def handle_enter_state(self, update, context):
            pass

        async def handle_on_user_message(self, update, context):
            pass

        def find_provider_name(self, keyboard_layout, callback_data):
            for row in keyboard_layout:
                for button in row:
                    if button.callback_data == callback_data:
                        return button.text
            return None

        async def handle_callback_query(self, update, context):
            self.shared_data.set_provider_code(update.callback_query.data)
            keyboard = update.effective_message.reply_markup.inline_keyboard

            # Find the text variable using the callback_data
            provider_name = self.find_provider_name(keyboard, update.callback_query.data)

            # Make sure provider_name is not None before proceeding
            if provider_name is None:
                LOG_PAY_STATE.raise_exception_with_log(RuntimeError("Provider not found for callback_data: " + str(update.callback_query.data)))

            next_state = BotPayState.ChooseCurrency(self.state)
            next_state.set_shared_data(self.shared_data)

            self.state.change_state(update, context, next_state)

            available_currencies = TariffManager.get_provider_currencies(provider_name)
            self.state._keyboard = self.state._instantiate_default_keyboard(
                {curr: curr for curr in available_currencies})

            # Immediately transition to pay state
            await self.state.transition_to_state(update, context, self.state.state_name)

    class ChooseCurrency(BasePayState):
        async def handle_enter_state(self, update, context):
            pass

        async def handle_on_user_message(self, update, context):
            pass

        async def handle_callback_query(self, update, context):
            self.shared_data.set_currency(update.callback_query.data)
            next_state = BotPayState.PayState(self.state)
            next_state.set_shared_data(self.shared_data)

            self.state.change_state(update, context, next_state)

            # Immediately transition to pay state
            await self.state.current_sub_state.handle_callback_query(update, context)

    class PayState(BasePayState):
        """State for paying"""

        async def handle_enter_state(self, update, context):
            pass

        async def handle_on_user_message(self, update, context):
            pass

        async def handle_callback_query(self, update, context):
            # Make locale
            lang_id = ChatManager.get_chat_language(update.effective_chat.id)
            ln_code = TranslationManager.get_language_code_by_id(lang_id)
            locale = await make_localized_text(ln_code)

            # Gather localized data for the invoice message
            chat_id = update.effective_chat.id
            title = await locale.get_text(f"states.{self.state.state_name}.title")
            description = await locale.get_text(f"states.{self.state.state_name}.description")

            exchange_rate = TariffManager.get_exchange_rate(self.shared_data.get_currency())
            tariff = self.shared_data.get_tariff()
            tariff_price = TariffManager.get_tariff_price(tariff)

            # Convert the price to the selected currency and then to its smallest denomination
            converted_price = tariff_price / exchange_rate
            smallest_denomination_price = int(converted_price * 100)

            self.shared_data.set_prices(
                [
                    LabeledPrice("Subscription for 1 month", smallest_denomination_price)
                ]
            )

            # TODO discount and promocode calculation

            # Gather data for the invoice
            js_str = {
                "tariff": self.shared_data.get_tariff(),
                "currency": self.shared_data.get_currency(),  # TODO: process the currency
                "price": self.shared_data.get_prices()[0].amount
            }

            payload = json.dumps(js_str)

            try:

                await context.bot.sendInvoice(chat_id, title, description, payload,
                                              self.shared_data.get_provider_code(),
                                              self.shared_data.get_currency(),
                                              self.shared_data.get_prices())  # Send invoice

                return await self.state.transition_to_state(update, context,
                                                            "chat")  # Return to chat, after payment is completed!
            except Exception as e:
                LOG_PAY_STATE.log(logging.ERROR, "Error sending invoice: " + str(e))

    class _SharedData(IPaySharedState):
        # Implementation of the pay shared data interface

        def __init__(self):
            self.chosen_provider = None
            self.chosen_tariff = None
            self.chosen_provider_code = None
            self.currency = 'USD'
            self.prices = None

        def set_tariff(self, data):
            self.chosen_tariff = data

        def set_provider_code(self, data):
            self.chosen_provider_code = data

        def set_currency(self, data):
            self.currency = data

        def set_prices(self, data):
            self.prices = data

        def get_tariff(self):
            return self.chosen_tariff

        def get_provider_code(self):
            return self.chosen_provider_code

        def get_provider(self):
            return self.chosen_provider

        def get_currency(self):
            return self.currency

        def get_prices(self):
            return self.prices

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._inter()

    def _inter(self):
        # Get provider list
        provider_dict = TariffManager.get_tariffs_dict()

        # Create initial state and pass a new shared data object
        initial_start = self.ChooseTariff(self)
        initial_start.set_shared_data(self._SharedData())

        self.change_state(None, None, initial_start)  # Set the initial state.

        # Form a keyboard of providers to show
        self._keyboard = self._instantiate_default_keyboard(provider_dict)

    async def enter_state(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        return await super().enter_state(update, context)

    async def callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        from telegram import InlineKeyboardMarkup

        # Skip if it's navigational data
        if self.input_handler.is_navigational_data(update.callback_query.data):
            return await super().callback_query(update, context)

        if update.callback_query.data == self.FALLBACK:
            self._inter()
            _current_keyboard = update.callback_query.message.reply_markup.inline_keyboard[:-1]
            _keyboard = await self._keyboard.get_keyboard()
            _current_wait_keyboard = tuple(tuple(sublist) for sublist in _keyboard[:-1])
            if _current_keyboard == _current_wait_keyboard:
                return await super().callback_query(update, context)
            return await self.enter_state(update, context)

        if self.current_sub_state:
            return await self.current_sub_state.handle_callback_query(update, context)

    async def _transition_to_next_state(self, context, query_data, update):
        pass

    async def _get_display_message(self, locale):
        query = ""

        if isinstance(self.current_sub_state, self.ChooseTariff):
            query = f"states.{self.state_name}.description"
        elif isinstance(self.current_sub_state, self.ChooseProvider):
            query = f"states.{self.state_name}.provider_display_message"
        elif isinstance(self.current_sub_state, self.ChooseCurrency):
            query = f"states.{self.state_name}.currency_display_message"
        elif isinstance(self.current_sub_state, self.PayState):
            query = f"states.{self.state_name}.pay_display_message"
        else:
            state.LOG_STATE_INSTANCE.raise_exception_with_log(ValueError("Incorrect state is currently chosen!"))

        return await locale.get_text(query)


class BotPayToPashaState(state.State):
    async def enter_state(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        from app.misc.admin.management import ManagementManager

        await self._update_keyboard_language(update)
        button_text = await BotPayToPashaState.get_locale_text_by_chat_id(update.effective_chat.id,
                                                                          "misc", "keyboard", "pay_to_pasha_button")
        message_text = await BotPayToPashaState.get_locale_text_by_chat_id(update.effective_chat.id,
                                                                           "misc", "keyboard", "pay_to_pasha_text")
        user_id = update.callback_query.from_user.id
        user_name = update.callback_query.from_user.first_name
        user_surname = update.callback_query.from_user.last_name
        username = update.callback_query.from_user.username if update.callback_query.from_user.username else "`without nickname`"
        await ManagementManager.send_admin_message(f"User {user_id}, {user_name} {user_surname} ({username}) "
                                                   f"is about to send us a message offering to donate!")
        developer_id = await ManagementManager.get_managers()
        if developer_id:
            telegram_link = f"tg://user?id={developer_id[0]}&text={message_text}"
            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(button_text, url=telegram_link)]])
            reply_string: str = await self.get_display_message(update, context)
            await self._respond(update.effective_chat, reply_string, reply_markup)
        return self.get_state_id()


class BotInfoLimitsState(state.State):
    # Defines info/limits state
    pass


class BotManageSubscriptionState(state.State):
    # Defines manage subscription state
    pass
