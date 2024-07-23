import discord
import os
import asyncio
import yt_dlp
import apikeys as APPKEYS
from discord.ext import commands
from dotenv import load_dotenv
import urllib.parse, urllib.request, re
from discord import AudioSource as aus

load_dotenv()

intents = discord.Intents.all()
intents.members = True
intents.message_content = True

load_dotenv()
TOKEN = APPKEYS.SPOTTER
intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix="!", intents=intents)

result = []
song = []
queues = {}
voice_clients = {}
youtube_base_url = 'https://www.youtube.com/'
youtube_results_url = youtube_base_url + 'results?'
youtube_watch_url = youtube_base_url + 'watch?v='
yt_dl_options = {"format": "bestaudio/best"}
ytdl = yt_dlp.YoutubeDL(yt_dl_options)
number_songs = 0
Current_song = ''
loop = False

ffmpeg_options = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5','options': '-vn -filter:a "volume=0.25"'}

@client.event
async def on_ready():
    print("Ready Status: Ok")

async def play_next(ctx):

    global Current_song
    global loop

    if loop == True:
        link = Current_song
        await playing(ctx, link=link)

    elif queues[ctx.guild.id] != []:
        link = queues[ctx.guild.id].pop(0)
        await playing(ctx, link=link)
    else: 
        Current_song = "There is no song currently playing."

# Creating a command for the bot to play audio

@client.command(name="playing")
async def playing(ctx, *, link):
        global Current_song

        try:
            voice_client = await ctx.author.voice.channel.connect()
            voice_clients[voice_client.guild.id] = voice_client
        except Exception as e:
            print(e)

        try:
            Current_song = link

            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(link, download=False))

            song = data['url']
            player = discord.FFmpegOpusAudio(song, **ffmpeg_options)

            voice_clients[ctx.guild.id].play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), client.loop))

            print(song)
        except Exception as e:
            print(e)

#Testing command to implement playlist reproduction to spotter

@client.command(name="play")
async def play(ctx, *, link):
        global Current_song

        #Connecting to the voice channel and retrieving the required data (link)
        try:
            voice_client = await ctx.author.voice.channel.connect()
            voice_clients[voice_client.guild.id] = voice_client
        except Exception as e:
            print(e)

        #Filtering to determine the data collected (video tittle, video link or playlist link)
        try:
            if youtube_base_url not in link:

                #Searching video by tittle name and retrieving it's link
                query_string = urllib.parse.urlencode({
                    'search_query': link
                })
                content = urllib.request.urlopen(
                    youtube_results_url + query_string
                )
                search_results = re.findall(r'/watch\?v=(.{11})', content.read().decode())
                link = youtube_watch_url + search_results[0]

                Current_song = link

                #Playing the determined link
                loop = asyncio.get_event_loop()
                data = await loop.run_in_executor(None, lambda: ytdl.extract_info(link, download=False))

                song = data['url']

                player = discord.FFmpegOpusAudio(song, **ffmpeg_options)
                voice_clients[ctx.guild.id].play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), client.loop))

            elif "list" in link:
                ydl = yt_dlp.YoutubeDL({'outtmpl': '%(id)s%(ext)s', 'quiet':True,})
                video = ""

                with ydl:
                    result = ydl.extract_info \
                    (link,
                    download=False) #We just want to extract the info

                    if 'entries' in result:
                    # Can be a playlist or a list of videos
                        video = result['entries']

                    #loops entries to grab each video_url
                        for i, item in enumerate(video):
                            video = result['entries'][i]
                            url = result['entries'][i]['webpage_url']
                            if ctx.guild.id not in queues:
                                queues[ctx.guild.id] = []
                            queues[ctx.guild.id].append(url)
                    Current_song = queues[ctx.guild.id][0]
                    link = queues[ctx.guild.id].pop(0)
                    await ctx.send("The playlist has been processed!\nUse !repair if Spotter left the voice chat :)")
                    await playing(ctx, link=link)
            else:
                Current_song = link

                #Playing the determined link
                loop = asyncio.get_event_loop()
                data = await loop.run_in_executor(None, lambda: ytdl.extract_info(link, download=False))

                song = data['url']

                player = discord.FFmpegOpusAudio(song, **ffmpeg_options)
                voice_clients[ctx.guild.id].play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), client.loop))

        except Exception as e:
            print(e)

#Creating a command for pausing audio

@client.command(pass_context = True)
async def pause(ctx):

    #Obtaining current song being played

    voice = discord.utils.get(client.voice_clients,guild=ctx.guild)

    #Verifying if a song is being played

    if (ctx.voice_client):
        if (voice.is_playing()):
            try:
                voice_clients[ctx.guild.id].pause()
                await ctx.send("The audio is now paused.")
            except Exception as e:
                print(e)
        else: 
            await ctx.send("There is no audio playing at the moment.")
    else:
        await ctx.send("Spotter is not in any voice chat at the moment.")

#Creating a command for resuming the audio after a pause.

@client.command(pass_context = True)
async def resume(ctx):

    #Obtaining current song being played

    voice = discord.utils.get(client.voice_clients,guild=ctx.guild)

    #Verifying audio status

    if (ctx.voice_client):
        if (voice.is_paused()):
            try:
                voice_clients[ctx.guild.id].resume()
            except Exception as e:
                print(e)
        else: 
            await ctx.send("There is no audio paused at the moment.")
    else:
        await ctx.send("Spotter is not in any voice chat at the moment.")

#Creating a command for skipping a song in the Queue

@client.command(name="skip")
async def skip(ctx):

    if queues[ctx.guild.id] != []:
        voice_clients[ctx.guild.id].pause()
        link = queues[ctx.guild.id].pop(0)
        await play(ctx, link=link)
    else:
        ctx.send("There are no songs in the queue.")

#Creating a command for stopping the bot completely

@client.command(name="stop")
async def stop(ctx):
    try:
        voice_clients[ctx.guild.id].stop()
        await voice_clients[ctx.guild.id].disconnect()
        del voice_clients[ctx.guild.id]
    except Exception as e:
        print(e)
    
#Creating a command for Queue's

@client.command(name="queue")
async def queue(ctx, *, url):

    global queues

    if ctx.guild.id not in queues:
        queues[ctx.guild.id] = []

    if ("list" in url):
        ydl = yt_dlp.YoutubeDL({'outtmpl': '%(id)s%(ext)s', 'quiet':True,})
        video = ""

        with ydl:
            result = ydl.extract_info \
            (url,
            download=False) #We just want to extract the info

            if 'entries' in result:
                # Can be a playlist or a list of videos
                video = result['entries']

                #loops entries to grab each video_url
                for i, item in enumerate(video):
                    video = result['entries'][i]
                    url = result['entries'][i]['webpage_url']
                    if ctx.guild.id not in queues:
                        queues[ctx.guild.id] = []
                    queues[ctx.guild.id].append(url)
    else:
        queues[ctx.guild.id].append(url)
    await ctx.send("Added to queue!")



#Creating a command to print the list currently in queue

@client.command(name="queuelist")
async def queuelist(ctx):

    number_songs = len(queues[ctx.guild.id])

    if number_songs == 0:
        await ctx.send("There are currently no songs in queue.")
    else:
        for n in range(number_songs): 
            songlink = str(queues[ctx.guild.id][n])
            if "https" not in songlink:
                songlink = songlink.capitalize()
            nt = str(n+1)
            await ctx.send(nt+". "+songlink)

#Creating a command to clear the queue

@client.command(name="clear_queue")
async def clear_queue(ctx):
    if ctx.guild.id in queues:
        queues[ctx.guild.id].clear()
        await ctx.send("Queue cleared!")
    else:
        await ctx.send("There is no queue to clear")

#Creating a command to display the current song      
  
@client.command(name="current")
async def current(ctx):
    global Current_song
    await ctx.send(Current_song)

#Creating a command that displays all the other commands

@client.command(name="sHelp")
async def sHelp(ctx):
    text = "The following are the commands for this bot and the correct syntax and way of using them:\n\n!join\nNote: This command will make the bot join the voice channel you are in at the moment.\n\n!play <insert tittle or link>\nNote: The link can refer to a single video or even a playlist.\n\n!pause\nNote: This command will pause the music and it doesn't require any input.\n\n!resume\nNote: Similarly to pause it doesn't require any input, and it will resume the music if you have paused it beforehand.\n\n!current\nNote: This command doesn't require any input and it will show the song that is currently being played.\n\n!queue <insert tittle or link>\nNote: The link can refer to a single video or even a playlist.\n\n!queuelist\nNote: This command doesn't require input and it will show you the entire queue ahead as a list.\n\n!clear_queue\nNote: This command will clear the current queue.\n\n!stop\nNote: this command doesn't require any input and it will stop the music and make the bot leave the voice chat.\n\n!repair\nNote: This command is intended to only be used in case a playlist was being processed and the bot left the voice chat.\n\n!loop\nNote: This command turns on a loop cycle for the song that is currently being played.\n\n!loop_off\nNote: This commmand turns off the loop cycle for the song being looped.\n\nFor more information on how to properly operate Spotter use the command !userGuide"
    await ctx.send(text)

#Creating a command to display user guide

@client.command(name="userGuide")
async def userGuide(ctx):
    text = "Here are some considerations when using Spotter:\n\n- Whenever a playlist is added either through !play or !queue, when using the !queuelist to inspect the list in the queue it will display each song within the playlist individually.\n\n- If you use !stop to make the bot pause the music and leave the voice chat, once it has left using the !resume command will not work for resuming the music and the queue will be cleaned so no songs will remain in queue. In order for the bot to play music you will have to use the !play command as described in !spotterCommands.\n\n- To use the !repair command properly please wait for the playlist is finished processing (Spotter will let you know once this happens) before using the repair command.\n\n- When using the !loop command remember to then use !loop_off once you want to move on to the next song in the queue or want to turn off the bot.\n\n- If for any reason Spotter stops playing music but does not leave the voice chat first use !pause to ensure the song you were playing stops correctly and then use !repair to restart that same song; if you would like to ignore that song and continue to the next one use !skip as usual."
    await ctx.send(text)

#Creating a command for the bot to join a vc

@client.command(name="join")
async def join(ctx):
    try:
        voice_client = await ctx.author.voice.channel.connect()
        voice_clients[voice_client.guild.id] = voice_client
    except Exception as e:
        print(e)

#Adding a patch fix "repair" command

@client.command(name="repair")
async def repair(ctx):
    link= Current_song
    await play(ctx, link=link)

#Creating a loop command
@client.command(name="loop")
async def loop(ctx):
    global loop
    loop = True
    await ctx.send("The song is now looped!")

#Creating a command to turn off the loop
@client.command(name="loop_off")
async def loop_off(ctx):
    global loop
    loop = False
    await ctx.send("The song is no longer being looped.")

client.run(APPKEYS.SPOTTER)
