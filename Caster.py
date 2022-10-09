import os
import discord
import psutil
import myjdapi
import time
import subprocess
from JSONLoader import getJSONFile

PJPATH = "/home/pi/Documents"
SRCPATH = f"{PJPATH}/Source"
os.system(f"mkdir {SRCPATH}")
data = getJSONFile("Data.json")
TOKEN = data["BOT_TOKEN"]
JKEYS = data["JKEYS"]
DEVNAME = data["DEVICE_NAME"]
EMAIL = data["EMAIL"]
LOGIN = data["LOGIN"]
FORMATS = ("mp4", "webm", "mkv", "wmv", "m4v")

class Bot(discord.Client):

    # Constructor
    def __init__(self):
        self.__jd = myjdapi.Myjdapi()
        self.__jd.set_app_key(JKEYS)
        self.__channel = 0
        os.system("rm nohup.out Output.txt")

        # Wait for JDownloader to start
        while 1:
            try:
                self.__jd.connect(EMAIL, LOGIN)
                self.device = self.__jd.get_device(device_name=DEVNAME)
                break
            except:
                time.sleep(1)

        super().__init__()

    # Signalize startup
    async def on_ready(self):
        try:
            channel_id = int(self.guilds[0].text_channels[0].id)
            self.__channel = self.get_channel(channel_id)
            await self.__channel.send("Ich bin bereit!")
            print(f"{self.user} has connected to Discord!")
        except:
            print(f"No default text channel to join found!")
            exit()


    # Delete locally saved media
    async def _delete_videos(self, splitMessage: [str]):
        try:
            vanilla = " ".join(splitMessage[1:])
            deleteMedia = vanilla.replace(" ", "___").lower()
        except:
            await self.__channel.send("Du hast vergessen mir einen Titel zu nennen!")

        mediaList = os.listdir(SRCPATH)
        mediaDict = {}

        for media in mediaList:
            parts = media.split(".")
            mediaDict[".".join(parts[:-1]).lower()] = parts[-1]

        try:
            if deletedMedia in mediaDict.keys():
                os.system(f"rm -rf {SRCPATH}/{deleteMedia}.{mediaDict[deleteMedia]}")
                await self.__channel.send(f"Ich habe {vanilla} gelöscht!")
            else:
                raise FileNotFoundError()
        except:
            await self.__channel.send(f"Ich konnte {vanilla} nicht finden!")


    # Return list of playable videos
    async def _list_videos(self):
        mediaList = os.listdir(SRCPATH)
        mediaDict = {}

        for media in mediaList:
            parts = media.replace("___", " ").split(".")
            mediaDict[".".join(parts[:-1])] = parts[-1]

        if mediaList:
            mediaListText = "\n".join(mediaDict.keys())
            await self.__channel.send(f"Folgende Medien hab ich für dich gespeichert:\n{mediaListText}")
        else:
            await self.__channel.send("Ich habe aktuell keine Medien für dich gespeichert!")


    # Download attachment from message
    async def _load_attachments(self, message):
        try:
            url = str(message.attachments).split('=')[3].split('\'')[1]
            dataFormat = url.split('.')[-1]
            fi = url.split("/")[-1]
            if dataFormat == "py":
                os.system(f"rm {fi}")
                os.system(f"wget {url}")
            else:
                if message.content:
                    os.system(f"wget {url} && mv {fi} {SRCPATH}/{message.content}.{dataFormat}")
                else:
                    os.system(f"wget {url} -P {SRCPATH}")
            await self.__channel.send("Download erfolgreich!")
        except:
            await self.__channel.send("Datei konnte nicht geladen werden (vielleicht zu groß?).")


    # Get youtube video
    async def _load_videos(self, splitMessage: [str]):
        try:
            link = splitMessage[1]
        except:
            await self.__channel.send("Mir fehlt ein Link zum Video!")

        try:
            self.device.linkgrabber.add_links([{"autostart": False, "links": link}])
        except:
            await self.__channel.send("Das Video konnte nicht in die Downloadlist aufgenommen werden!")

        pkg_vid_id_dict = {}
        names = []

        await self.__channel.send("Ich lade jetzt das Video...")

        # Play loading screen
        subprocess.Popen([f"nohup vlc -Z {PJPATH}/Loading.mp4 --play-and-exit --loop &"], shell=True)

        # Wait for linkgrabber to collect all sources
        while self.device.linkgrabber.is_collecting():
            time.sleep(1)

        # Find video files in the potential link mess
        for pkg in self.device.linkgrabber.query_links():
            # pkg contains suiting file format?
            try:    
                if pkg["variant"]["name"].lower() in FORMATS or pkg["name"].split(".")[-1] in FORMATS:
                    names.append(pkg["name"])
                    if pkg["packageUUID"] in pkg_vid_id_dict.keys():
                        pkg_vid_id_dict[pkg["packageUUID"]].append(pkg["uuid"])
                    else:
                        pkg_vid_id_dict[pkg["packageUUID"]] = [pkg["uuid"]]
            except: pass

        # No downloadable video found
        if not len(pkg_vid_id_dict):
            await self.__channel.send("Kein Video im Link gefunden!")
            self.device.linkgrabber.clear_list()
            return

        try:  # Start the download
            vid_ids = []
            for ids in pkg_vid_id_dict.values():
                vid_ids += ids
            self.device.linkgrabber.move_to_downloadlist(link_ids=vid_ids,
                                                         package_ids=list(pkg_vid_id_dict.keys()))
            self.device.linkgrabber.clear_list()

            # Wait for downloads to finish
            while self.device.downloadcontroller.get_current_state() == "RUNNING":
                time.sleep(1)

            await self._manage_open_video(2, False)

            # Rename downloaded video
            if len(names) > 1:       # Multiple videos
                time.sleep(3)
                await self.__channel.send("Es wurden mehrere Videos runtergeladen, welche benannt werden können!")
                with open("unnamed.txt", 'w') as file:
                    for name in names:
                        file.write(f"{name}\n")
                await self.__channel.send(f"Unter welchen Namen soll das Video \"{names[0]}\" "
                                          f"gespeichert werden?")
                subprocess.Popen([f"nohup vlc -Z \"{SRCPATH}/{names[0]}\" --play-and-exit --loop &"], shell=True)
            
            elif len(names) == 1:    # One video
                if len(splitMessage) > 3:
                    newName = " ".join(splitMessage[3:]).replace(" ", "___").lower()
                    os.system(f"mv \"{SRCPATH}/{names[0]}\" \"{SRCPATH}/{newName}.{names[0].split('.')[-1]}\"")
                    await self.__channel.send("Der Download ist fertig geladen!")
           
            else:               # No video
                await self.__channel.send(
                    "Leider ist ein Fehler aufgetreten und ein Video konnte nicht gefunden werden!")
        
        except: await self.__channel.send("Kein gültiger Videolink!")
        self.device.linkgrabber.clear_list()


    # Stop (0), continue (1) or kill (2) a video 
    async def _manage_open_video(self, signal: int = 0, respond: bool = True):
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
                        os.system(f"kill -CONT {entry}")
                        os.system(f"kill {entry}")
                    else:
                        os.system(f"kill {flag[signal]} {entry}")
                    break
            if respond:
                await self.__channel.send(response[signal])
        except:
            await self.__channel.send("Ich konnte kein offenes Video finden!")
        os.system("rm end.txt")


    # Play (or loop) a video
    async def _play_videos(self, splitMessage: [str], keyword: str):
        try:
            media = "___".join(splitMessage[1:]).lower()
        except:
            await self.__channel.send("Du hast vergessen mir zu sagen, welches Video ich starten soll!")

        mediaList = os.listdir(SRCPATH)
        mediaDict = {}

        for m in mediaList:
            parts = m.split(".")
            mediaDict[".".join(parts[:-1])] = parts[-1]

        name = f"{media}.{mediaDict[media]}"
        await self.__channel.send("Das Video wird gleich starten!")
        if keyword in ["loop", "loope", "wiederhole", "wiederhol", "🔃", "🔄", "🔁"]:
            subprocess.Popen([f"nohup vlc -Z {SRCPATH}/{name} --play-and-exit --loop &"], shell=True)
        else:
            subprocess.Popen([f"nohup vlc -Z {SRCPATH}/{name} --play-and-exit &"], shell=True)


    # Rename locally saved media
    async def _rename_videos(self, splitMessage: [str]):
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
                oldName = f"{oldName} {word}"
                oldNameIntern = f"{oldNameIntern}___{word.lower()}"
                newNameFirstIndex += 1

            fmt = mediaDict[oldNameIntern]
            newName = splitMessage[newNameFirstIndex:]
            newInternName = "___".join(splitMessage[newNameFirstIndex:]).lower()
            os.system(f"mv \"{SRCPATH}/{oldNameIntern}.{fmt}\" \"{SRCPATH,}/{newInternName}.{fmt}\"")
            await self.__channel.send(f"\"{oldName}\" wurde in \"{newName}\" umbenannt!")
        except:
            await self.__channel.send("Es ist ein Fehler aufgetreten! Schreib \"Hilfe\" und lies dir am besten \
                                        nochmal durch, wie du Videos umbenennen kannst.")


    # Respond to a message
    async def on_message(self, message):

        if message.author == self.user:  # Own message; do nothing
            return

        # Continue download renaming process
        if os.path.exists("unnamed.txt"):
            await self._manage_open_video(2, False)
            remaining, name = "", ""
            with open("unnamed.txt", 'r') as file:
                name = file.readline().replace("\n", "")
                remaining = file.read()
            newName = message.content.replace(" ", "___").lower()
            os.system(f"mv \"{SRCPATH}/{name}\" \"{SRCPATH}/{newName}.{name.split('.')[-1]}\"")
            if remaining:
                with open("unnamed.txt", 'w') as file:
                    file.write(remaining)
                nextVideo = remaining.split("\n")[0]
                subprocess.Popen([f"nohup vlc -Z \"{SRCPATH}/{nextVideo}\" --play-and-exit --loop &"], shell=True)
                await self.__channel.send(f"Unter welchen Namen soll das Video \"{nextVideo}\" "
                                          f"gespeichert werden?")
            else:
                os.system("rm unnamed.txt")
                await self.__channel.send("Der Download ist fertig geladen!")
            return

        # Check for available disk space
        space = psutil.disk_usage("/")
        if space.percent > 99:
            await self.__channel.send("Dein Speicherplatz ist voll! "
                                      "Lösche ein paar Videos und versuche es dann erneut.")
            return
        elif space.percent > 90:
            await self.__channel.send("Dein Speicherplatz ist fast voll (Über 90%)!")

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
            await self._load_videos(splitMessage)


        # Emoji: Pause-Button
        elif keyword in ("warte", "halt", "stopp", "stop", "stoppe", "pause", 
                         "pausiere", "pausieren", "⏸️"):
            await self._manage_open_video(0)


        # Emoji: Media-In-Button
        elif keyword in ("spiele", "spiel", "starte", "start", "zeige", 
                         "nimm", "play", "öffne", "loop", "loope", "wiederhole",
                         "wiederhol", "⏏️"):
            await self._play_videos(splitMessage, keyword)


        # Emoji: Play-Button, three different Loop-Buttons
        elif keyword in ("weiter", "los", "fortfahren", "fahre", 
                         "fortführen", "mach", "▶️", "🔃", "🔄", "🔁"):
            await self._manage_open_video(1)


        # Emoji: End-Button
        elif keyword in ("end", "ende", "schluss", "beende", "beenden", "aufhören", "hör", 
                         "schließen", "schließe", "kill", "⏹️"):
            await self._manage_open_video(2)


        # Emoji: WiFi-Button
        # Deprecated: Does not seem feasible; play a local video instead
        elif keyword in ("stream", "streame", "live", "streamen", "📶"):
            await self._play_videos(splitMessage)


        elif keyword in ("lösche", "lösch", "entferne", "entfern"):
            await self._delete_videos(splitMessage)


        elif keyword in ("änder", "ändere", "ändern", "umändern", "umbenennen", 
                         "neubenennen", "umbenenn", "name", "mach", "mache"):
            await self._rename_videos(splitMessage)


        elif keyword in ["list", "liste", "videos", "filme", "serien", "sammlung", "downloads", "medien"]:
            await self._list_videos()


        # Edit autostart scripts
        elif keyword == "$inject":
            scripts = splitMessage[1:]
            os.system("cp updateProfile .profile")
            with open(".profile", 'a') as file:
                file.write("\n")
                for script in scripts:
                    file.write(f"nohup python3 {script}.py & \n")
            os.system("cp .profile ~/.profile")
            await self.__channel.send("Autostart scripts changed!")


        # Check for a last job to download and poweroff
        elif keyword in ("aus", "poweroff", "shutdown", "schlafen"):
            try:
                if len(splitMessage) - 1:
                    await self._load_videos(splitMessage)
            except: pass
            await self.__channel.send("Bye bye!")
            os.system("sudo poweroff")


        # Reboot
        elif keyword in ("$r", "neustart", "reboot", "$reboot"):
            await self.__channel.send("Hab bitte einen Moment Geduld, ich bin gleich wieder da!")
            os.system("sudo reboot")


        # Return a status report
        elif keyword in ("$s", "$status", "status"):
            await self.__channel.send(f"Total: {round(space.total / (2 ** 30), 3)}GB; " 
                                      f"Used: {round(space.used / (2**30), 3)}GB, " 
                                      f"Free: {round(space.free / (2**30), 3)}GB; " 
                                      f"Percent: {space.percent}%")


        # Get help response
        elif keyword == ("h", "hilfe", "help", "$h", "$help"):
            try:
                with open("HelpText.txt", 'r') as file:
                    text = file.read()
                    await self.__channel.send(text)
            except:
                await self.__channel.send("Es ist ein Fehler aufgetreten! HILFEEE!")

        else:
            await self.__channel.send(":)")


b = Bot()
b.run(TOKEN)
