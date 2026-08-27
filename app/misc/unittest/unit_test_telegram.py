from unittest.mock import MagicMock
from telegram import Update

from app.misc.admin.admin_commands import AdminCommands

if __name__ == "__main__":
    # create telegram context
    context = MagicMock()

    # create telegram update
    update = MagicMock(spec=Update)
    update.effective_user.id = 466001259
    update.effective_message.text = "/execute print(2+2)"

# call the function for test
    AdminCommands.execute_dynamic_command(update, context)

# check results
#assert context.method_called == expected_result