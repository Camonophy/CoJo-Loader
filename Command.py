import os
from JSONLoader import getJSONFile
import discord

discordData = getJSONFile("Calem.json")
os.system("mkdir Source")
TOKEN = discordData["BOT_TOKEN"]

class Bot(discord.Client):

    def __init__(self):
        super().__init__()

    async def on_ready(self):
        print("Command bot has connected to Discord!")

    async def on_message(self, message):
        if message.author == self.user:
            return

        # Get attachment
        elif message.content.startswith("%"):
            command = message.content[1:]
            text = ""
            os.system("{} > Output.txt".format(command))

            with open("Output.txt", 'r') as file:
                text = file.read()
        
            if len(text) > 0:
                await message.channel.send("Beep Boop command executed with: ")
                await message.channel.send(str(text))
            else:
                await message.channel.send("Beep Boop command executed!")


b = Bot()
b.run(TOKEN)
