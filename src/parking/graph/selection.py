"""Conversation context for the question currently awaiting a space choice."""


def last_assistant_message(state):
    return next((message.content for message in reversed(state.get("messages", []))
                 if message.type == "ai" and isinstance(message.content, str)), "")


def awaiting_space_selection(state):
    value = state.get("awaiting_space_selection")
    if isinstance(value, bool):
        return value
    # Existing checkpoints predate this explicit channel. These are the
    # application's controlled prior prompts, not keywords in customer input.
    text = last_assistant_message(state)
    return text.endswith(("Which space would you like?", "Please choose one of the listed spaces."))
