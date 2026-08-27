import asyncio
import logging

from telegram import Update
from telegram.ext import CommandHandler, MessageHandler
from telegram.ext import CallbackQueryHandler, filters

from app.bot.states.users_states import UsersStates
from app.misc import log_helper as log
from app.bot.states import state
import asyncio

from typing import Union

# Define logger for this module
LOG_STATE = log.LogHelper(__name__, "Bot States Thread")


class BotStateMachine:
    """
    Used to create states
    """

    # Define the statics
    __entry_points: list[CommandHandler] = []
    __states: dict[int, state.State] = {}

    __current_state = 0
    __previous_state = -1

    def add_entry(self, handler: CommandHandler):
        """Adds handler to entry points"""
        self.__entry_points.append(handler)

    def add_state(self, state: state.State):
        """
        Add a state and its corresponding message handler to the BotStateMachine.
        Nothing happens if the state and a handler already exist

        Args:
            state (State): The class of State instance that overrides the handlers
        Returns:
            None
        """
        try:

            if state not in self.__states.values():
                # Add state
                self.__states[state.get_state_id()] = state
                state._set_state_machine_ref(self)

        except Exception as e:
            LOG_STATE.log(logging.ERROR, f"There is an exception occurred when trying to add a state. Message is {e}")

    def add_states(self, states, parent_state: object = None):

        for state_name, (state_class, substates_dict) in states.items():

            keyboard_layout = {data.capitalize(): data for data in substates_dict.keys()}
            state_instance = state_class(keyboard_layout=keyboard_layout, state_name=state_name,
                                         parent_state=parent_state)

            # Add the instantiated state to the bot state machine.
            self.add_state(state_instance)

            # If there are substates, recursively add them as well.
            if substates_dict:
                self.add_states(substates_dict, parent_state=state_instance)

    async def transition_to_state(self, update: Update, context, state_name: str):
        # Triggers enter state function and return that next state id
        next_state: state.State = self.get_state_by_name(state_name)
        new_state = await next_state.enter_state(update, context)

        self.__previous_state = self.__current_state
        self.__current_state = new_state

        return self.__current_state

    async def transition_to_state_with_id(self, update, context, state_id):
        # Enters currents state again. Used to show the reply markup of buttons again if the message was lost
        current_state = self.get_state_by_id(state_id)
        await current_state.enter_state(update, context)
        return state_id

    def get_entry_points(self):
        # Returns a copy of the entry points list.
        return self.__entry_points.copy()

    def get_states(self):
        dict = {}
        for bot_state in self.__states.values():
            # TODO : Adapt for the new state architecture
            dict[bot_state.get_state_id()] = [
                MessageHandler(filters.TEXT & (~filters.COMMAND), bot_state.on_user_messaged),
                CallbackQueryHandler(bot_state.callback_query)]
        return dict

    def get_state_by_class(self, state_class):
        for __state in self.__states.values():
            if isinstance(__state, state_class):
                return __state

        # Throw exception if we are trying to get an unexisting state
        LOG_STATE.raise_exception_with_log(
            NotImplementedError(f"This state class isn't implemented! The class provided is {state_class}"))

    def get_state_by_name(self, state_name):
        for __state in self.__states.values():
            if __state.get_state_name() == state_name:
                return __state

    def get_state_by_id(self, index: int):
        # Ensure the index is within the arrays bounds
        if index in self.__states.keys():
            return self.__states[index]
        return None

    def get_current_state_id(self):
        return self.__current_state
