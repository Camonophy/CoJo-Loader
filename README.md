# CoJo-Loader

![Coraline](Title.png?raw=true "")

Low key application to download, manage and play videos from _any_ URL source.
Primarily designed to run on RaspberryPi 3 or higher with Pi-OS, it can turn your Pi into a Google Chromecast kinda device, but focusing more on functionality than proprietary.

## Installation
### Disclaimer
This guide is based on the Pi-OS64 with desktop (*not* the lite version). If you choose to pick any other Linux distribution, especially a non Debian based one, chances are that you will encounter minor issues (minor at best). 
In that case, you need to rely on your own skill to navigate through each step and adapt them to your individual setup!

### Discord
This application is supposed to be controlled remotely via your own <a href="https://discord.com/developers">Discord bot</a>. I would suggest to create a new Discord server whose only purpose is to interact with your bot. Please provide CoJo-Loader the informations about your server and your bot by replacing the **EXAMPLE** placeholder in _Calem.json_ with the corresponding keys.

### Guide
First you have to <a href="https://www.raspberrypi.com/software/">set up your Raspberry Pi</a>. 
Just to be sure run:

```sh
sudo apt update && sudo apt upgrade -y && sudo apt install openjdk-11-jre openjdk-11-jdk vlc 
```

after booting up your Pi for the first time. 
Next we need a convenient tool to download videos from any given URL. Luckily, JDownloader seems just right for this job (at least for me). They even provide a pretty easy-to-use installation script  on their <a href="https://jdownloader.org/download/index">official webpage</a> (_JDownloader does not seem to work with Pi-Zero and any Pi Version below 2_). 
You can run the script by typing the following command in the same directory as the script:

```sh
sh JDownloader2Setup_unix_nojre.sh
```

Start JDownloader and connect to your <a href="https://my.jdownloader.org">MyJDownloader account</a> (This is necessary to establish the connection between CoJo-Loader and your JDownloader).
Finally you need to install the required Python packages by simply run:

```sh
pip3 install -r requirements.txt
```
and replace your credentials found on the MyJDownloader website with the **EXAMPLE** placeholder in _Calem.json_.
If everything goes smoothly without errors, you should now be ready to run 

```sh
python3 Caster.py
```
