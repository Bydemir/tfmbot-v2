class Events():

    def __init__(self):
        pass

    def set_bot(self, bot):
        self.bot = bot

    def on_login(self, name):
        """Called when bot successfuly logs in.

        name -- the bot's username
        """
        pass

    def on_whisper(self, mouse, direction, message):
        """Called when the bot sends or receives a whisper.

        mouse -- the name of the mouse that whispered
        direction -- 0 for sent, 1 for received. If 0, mouse is own username
        message -- the content of the whisper
        """
        pass

    def on_tribe_invite(self, mouse, tribe, tribe_id):
        """Called when the bot receives a tribe invite.

        mouse -- the name of the mouse that invited
        tribe -- the name of the tribe
        tribe_id -- the ID of the tribe, used to join the tribe
        """
        pass

    def on_tribe_chat(self, mouse, message):
        """Called when the bot receives a tribe chat message.

        mouse -- the name of the mouse that sent the message
        message -- the content of the tribe message
        """
        pass
            
    def on_tribe_connect(self, mouse):
        """Called when a player connects in the bot's tribe.

        mouse -- the name of the mouse that connected
        """
        pass

    def on_tribe_disconnect(self, mouse):
        """Called when a player disconnects in the bot's tribe.

        mouse -- the name of the mouse that disconnected
        """
        pass

    def on_tribe_join(self, mouse):
        """Called when a player joins the bot's tribe.

        mouse -- the name of the mouse that joined the tribe
        """
        pass

    def on_self_tribe_join(self):
        """Called when the bot joins a tribe."""
        pass

    def on_tribe_leave(self, mouse):
        """Called when a player leaves the bot's tribe.

        mouse - the name of the player that left the tribe
        """
        pass

    def on_self_tribe_leave(self):
        """Called when the bot leaves a tribe."""
        pass
