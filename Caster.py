import os
import discord
import psutil
import myjdapi
import time
from JSONLoader import getJSONFile

PJPATH = "/home/pi/Documents"
SRCPATH = "{}/Source".format(PJPATH)
os.system("mkdir {}".format(SRCPATH))
data = getJSONFile("EXMAPLE.json")
TOKEN = data["BOT_TOKEN"]
JKEYS = data["JKEYS"]
EMAIL = data["EMAIL"]
LOGIN = data["LOGIN"]

class Bot(discord.Client):

    # Constructor
    def __init__(self):
        self.__jd = myjdapi.Myjdapi()
        self.__jd.set_app_key(JKEYS)

        # Wait for JDownloader to start
        while 1:
            try:
                self.__jd.connect(EMAIL, LOGIN)
                self.device = self.__jd.get_device(device_name="EXAMPLE@EXAMPLE")
                break
            except:
                time.sleep(1)

        super().__init__()

    # Signalize startup
    async def on_ready(self):
        print(f'{self.user} has connected to Discord!')


    # Delete locally saved media
    async def _delete_videos(self, message, splitMessage: str, keyword: str):
        try:
            vanilla = " ".join(splitMessage[1:])
            deleteMedia = vanilla.replace(" ", "___").lower()
        except:
            await message.channel.send("Du hast vergessen mir einen Titel zu nennen!")

        mediaList = os.listdir(SRCPATH)
        mediaDict = {}

        for media in mediaList:
            parts = media.split(".")
            mediaDict[".".join(parts[:-1]).lower()] = parts[-1]

        try:
            os.system("rm -rf {}/{}.{}".format(SRCPATH, deleteMedia, mediaDict[deleteMedia]))
            await message.channel.send("Ich habe {} gelöscht!".format(vanilla))
        except:
            await message.channel.send("Ich konnte {} nicht finden!".format(vanilla))


    # Return list of playable videos
    async def _list_videos(self, message):
        mediaList = os.listdir(SRCPATH)
        mediaDict = {}

        for media in mediaList:
            parts = media.replace("___", " ").split(".")
            mediaDict[".".join(parts[:-1])] = parts[-1]

        if mediaList:
            mediaListText = "\n".join(mediaDict.keys())
            await message.channel.send("Folgende Medien hab ich für dich gespeichert:\n{}".format(mediaListText))
        else:
            await message.channel.send("Ich habe aktuell keine Medien für dich gespeichert!")


    # Download attachment from message message  
    async def _load_attachments(self, message):
        try:
            url = str(message.attachments).split('=')[3].split('\'')[1]
            dataFormat = url.split('.')[-1]
            if dataFormat == "py":
                file = url.split("/")[-1]
                os.system("rm {}".format(file))
                os.system("wget {}".format(url))
            else:
                os.system("wget {} -P {}".format(url, SRCPATH))
            await message.channel.send("Download erfolgreich!")
        except:
            await message.channel.send("Datei konnte nicht geladen werden (vielleicht zu groß?).")


    # Get youtube video TODO: Add support to shutdown after complete downloads    
    async def _load_videos(self, message, splitMessage: str, keyword: str):
        try:
            link = splitMessage[1]
        except:
            await message.channel.send("Mir fehlt ein Link zum Video!")

        try:
            self.device.linkgrabber.add_links([{"autostart" : False, "links" : link}])
        except:
            await message.channel.send("Das Video konnte nicht in die Downloadlist aufgenommen werden!")

        pkg_ids, vid_ids, cleanup = [], [], []
        name    = ""

        await message.channel.send("Ich lade jetzt das Video...")

        # Wait for query links to appear in the linkgrabber
        while not len(self.device.linkgrabber.query_links()):
            time.sleep(1)

        # TODO: Add support for more video formats
        # Find .mp4 files in the potential link mess
        for lem in self.device.linkgrabber.query_links():
            name = lem["name"] if ".mp4" in lem["name"] else name  # name contains ".mp4"?
            try:
                if "MP4" in lem["variant"]["name"] or "mp4" == lem["name"].split(".")[-1]:
                    vid_ids.append(lem["uuid"])
                    if lem["packageUUID"] not in pkg_ids:
                        pkg_ids.append(lem["packageUUID"])
                else:
                    cleanup.append(lem["uuid"])
            except:
                cleanup.append(lem["uuid"])

        # Clean the linkgrabber
        self.device.linkgrabber.cleanup(mode="REMOVE_LINKS_ONLY",
            selection_type="SELECTED", link_ids=cleanup, action="DELETE_ALL")

        try: # Start the download
            self.device.linkgrabber.move_to_downloadlist(link_ids=vid_ids, package_ids=pkg_ids)

            # Wait for downloads to finish
            while len(self.device.downloads.query_links()):
                time.sleep(1)

            # Rename downloaded video TODO: Add more video formats here too
            if len(splitMessage) > 3:
                newName = " ".join(splitMessage[3:]).replace(" ", "___").lower()
                os.system("mv {}/\"{}\" {}/\"{}\".mp4".format(SRCPATH, name, SRCPATH, newName))
            await message.channel.send("Dein Video \"{}\" ist fertig geladen!".format(name))
        except:
            await message.channel.send("Kein gültiger Video link!")


    # Stop, continue or kill a video
    async def _manage_open_video(self, message, signal: int):
        # Find PID of the vlc player
        outputShards = []
        response = ("Ich habe das Video angehalten!", "Weiter geht's!", "Ich habe das Video beendet!")
        flag = ("-STOP", "-CONT")
        os.system("ps -e | grep vlc > end.txt") 
        try:
            with open("end.txt", 'r') as file:
                outputShards = file.read().split(" ")
            for entry in outputShards:
                if entry != "":
                    if signal == 2:
                        os.system("kill -CONT {}".format(entry))
                        os.system("kill {}".format(entry))
                    else:
                        os.system("kill {} {}".format(flag[signal], entry))
                    break
            await message.channel.send(response[signal])
        except:
            await message.channel.send("Ich konnte kein offenes Video finden!")
        os.system("rm end.txt")


    # Play (or loop) a video
    async def _play_videos(self, message, splitMessage: str, keyword: str):
        try:
            media = "___".join(splitMessage[1:]).lower()
        except:
            await message.channel.send("Du hast vergessen mir zu sagen, welches Video ich starten soll!")

        mediaList = os.listdir(SRCPATH)
        mediaDict = {}

        for m in mediaList:
            parts = m.split(".")
            mediaDict[".".join(parts[:-1])] = parts[-1]

        name = "{}.{}".format(media, mediaDict[media])
        await message.channel.send("Das Video wird gleich starten!")
        if keyword in ["loop", "loope", "wiederhole", "wiederhol", "🔃", "🔄", "🔁"]:
            subprocess.Popen(["nohup vlc -Z {}/{} --play-and-exit --loop &".format(SRCPATH, name)], shell=True)
        else:
            subprocess.Popen(["nohup vlc -Z {}/{} --play-and-exit &".format(SRCPATH, name)], shell=True)


    # Rename locally saved media
    async def _rename_videos(self, message, splitMessage: str, keyword: str):
        mediaList = os.listdir(SRCPATH)
        mediaDict = {}

        for media in mediaList:
            parts = media.split(".")
            mediaDict[".".join(parts[:-1]).lower()] = parts[-1]

        try:
            oldName = splitMessage[1]
            oldNameIntern = oldName.lower()
            wordBlob = splitMessage[2:]
            newNameFirstIndex = 3

            for word in wordBlob:
                if oldNameIntern in mediaDict.keys():
                    break
                oldName = "{} {}".format(oldName, word)
                oldNameIntern = "{}___{}".format(oldNameIntern, word.lower())
                newNameFirstIndex += 1

            fmt = mediaDict[oldNameIntern]
            newName = splitMessage[newNameFirstIndex:]
            newInternName = "___".join(splitMessage[newNameFirstIndex:]).lower()
            os.system("mv {}/{}.{} {}/{}.{}".format(SRCPATH, oldNameIntern, fmt, SRCPATH, newInternName, fmt))
            await message.channel.send("\"{}\" wurde in \"{}\" umbenannt!".format(oldName, newName))
        except:
            await message.channel.send("Es ist ein Fehler aufgetreten! Schreib \"Hilfe\" und lies dir am besten \
                                        nochmal durch, wie du Videos umbenennen kannst.")


    # Stream a video TODO
    async def _stream_videos(self, message, splitMessage: str, keyword: str):
        print("TODO")


    # Respond to a message
    async def on_message(self, message):

        if message.author == self.user:     # Own message; do nothing
            return

        # Check for available disk space
        space = psutil.disk_usage("/")
        if space.percent > 99:
            await message.channel.send("Dein Speicherplatz ist voll! "
                                       "Lösche ein paar Videos und versuche es dann erneut.")
            return
        elif space.percent > 90:
            await message.channel.send("Dein Speicherplatz ist fast voll (Über 90%)!")

        splitMessage = message.content.split(" ")
        keyword = splitMessage[0].lower()

        # Remove double quotes around input
        if len(message.content) > 0:
            if message.content[0] == "\"":
                message.content = message.content[1:]
            if message.content[-1] == "\"":
                message.content = message.content[:-1]


        if message.attachments:
            await self._load_attachments(message)


        # Emoji: "NEW"-Button
        elif keyword in ("lade", "lad", "speicher", "ziehe", "zieh", 
                         "runterladen", "🆕"):
            await self._load_videos(message, splitMessage, keyword)
            #downloadThread = threading.Thread(target=self._load_videos, args=(keyword, splitMessage))
            #downloadThread.start()


        # Emoji: Pause-Button
        elif keyword in ("warte", "halt", "stopp", "stop", "stoppe", "pause", 
                         "pausiere", "pausieren", "⏸️"):
            await self._manage_open_video(message, 0)


        # Emoji: Media-In-Button
        elif keyword in ("spiele", "spiel", "starte", "start", "zeige", 
                         "nimm", "play", "öffne", "loop", "loope", "wiederhole",
                         "wiederhol", "⏏️"):
            await self._play_videos(message, splitMessage, keyword)


        # Emoji: Play-Button, three different Loop-Buttons
        elif keyword in ("weiter", "los", "fortfahren", "fahre", 
                         "fortführen", "mach", "▶️", "🔃", "🔄", "🔁"):
            await self._manage_open_video(message, 1)


        # Emoji: End-Button
        elif keyword in ("end", "ende", "schluss", "beende", "beenden", "aufhören", "hör", 
                         "schließen", "schließe", "kill", "⏹️"):
            await self._manage_open_video(message, 2)


        # Emoji: WiFi-Button
        elif keyword in ("stream", "streame", "live", "streamen", "📶"):
            await self._stream_videos(message, splitMessage, keyword)


        elif keyword in ("lösche", "lösch", "entferne", "entfern"):
            await self._delete_videos(message, splitMessage, keyword)


        
        elif keyword in ("änder", "ändere", "ändern", "umändern", "umbenennen", 
                         "neubenennen", "umbenenn", "name", "mach", "mache"):
            await self._rename_videos(message, splitMessage, keyword)


        elif keyword in ["list", "liste", "videos", "filme", "serien", "sammlung", "downloads", "medien"]:
            await self._list_videos(message)


        # Edit autostart scripts TODO: Update newbash
        elif keyword == "$inject":
            scripts = str(message.content).split(" ")[1:]
            os.system("cp .bashrc newbash")
            with open("newbash", 'a') as file:
                file.write("\n")
                for script in scripts:
                    file.write("nohup python3 {}.py & \n".format(script))
            os.system("cp newbash ~/.bashrc")
            await message.channel.send("Autostart scripts changed!")


        # Poweroff
        elif keyword in ("aus", "poweroff", "shutdown", "schlafen"):
            await message.channel.send("Bye bye!")
            os.system("sudo poweroff")


        # Reboot
        elif keyword in ("$r", "neustart", "reboot"):
            await message.channel.send("Hab bitte einen Moment Geduld, ich bin gleich wieder da!")
            os.system("sudo reboot")


        # Return a status report
        elif keyword in ("$s", "$status"):
            await message.channel.send("Total: {}GB; Used: {}GB, Free: {}GB; Percent: {}%".format(round(space.total / (2**30), 3),
                                                                                            round(space.used / (2**30), 3),
                                                                                            round(space.free / (2**30), 3),
                                                                                            space.percent))


        # Get help response TODO: Update text
        elif keyword == ("h", "hilfe", "help"):
            try:
                with open("HelpText.txt", 'r') as file:
                    text = file.read()
                    await message.channel.send(text)
            except:
                await message.channel.send("Es ist ein Fehler aufgetreten! HILFEEE!")

        # Stop Coraline
        #elif keyword == ["exit"]:
        #    exit(0)

        else:
            pass                # Nothing to do


b = Bot()
b.run(TOKEN)
