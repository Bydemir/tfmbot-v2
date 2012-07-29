from events import Events
from tfmbot import TFMBot

class ExampleBot(Events):

    def on_whisper(self, mouse, direction, message):
        if direction == 1: # 1 = received
            if mouse in self.bot.tribe_members:
                self.bot.whisper(mouse, "Hi %s, we are tribe mates!" % mouse)
            else:
                self.bot.whisper(mouse, "Hi %s!" % mouse)

    def on_tribe_invite(self, mouse, tribe, tribe_id):
        self.bot.whisper(mouse, "Thanks for the invite!")
        self.bot.accept_invite(tribe_id) # Join any tribe

    def on_tribe_chat(self, mouse, message):
        if self.bot.username.lower() in message.lower():
            self.bot.tribe_chat("Hi %s!" % mouse)

    def on_tribe_connect(self, mouse):
        self.bot.tribe_chat("Welcome back %s" % mouse)

    def on_tribe_disconnect(self, mouse):
        self.bot.tribe_chat("Bye %s" % mouse)

    def on_self_tribe_join(self):
        self.bot.tribe_chat("Thanks for inviting me to your tribe!")

# Use True if you have a botted account
# Almost no one does, use False
bot = TFMBot("username", "password", False, ExampleBot())
bot.go()
