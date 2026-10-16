class AIProvider:
    def get_chat_response(self, messages: list) -> tuple:
        """
        :param messages: [{'role': 'system'|'user'|'assistant', 'content': str}, ...]
        :return: (response_text, meta_dict)
        """
        raise NotImplementedError("Each provider must implement this method")
