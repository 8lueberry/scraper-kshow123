#!/usr/bin/python

from collections import namedtuple
import inspect
import os
import sys
import urllib
import urlparse

import simplejson as json

import xbmc
import xbmcgui
import xbmcplugin

class Logger:
    def log(self, level, message):
        xbmc.log(message)
    def warn(self, message):
        return self.log(1, message)

logger = Logger()

logger.log(1, 'Loading platform: ' + sys.platform)

# for windows add Crypto module folder
if sys.platform == 'win32':
    cmd_subfolder = os.path.realpath(os.path.abspath(os.path.join(os.path.split(inspect.getfile(inspect.currentframe()))[0], 'win32')))
    if cmd_subfolder not in sys.path:
        sys.path.insert(0, cmd_subfolder)

# for OSX add Crypto module folder
if sys.platform == 'darwin':
    cmd_subfolder = os.path.realpath(os.path.abspath(os.path.join(os.path.split(inspect.getfile(inspect.currentframe()))[0], 'osx')))
    if cmd_subfolder not in sys.path:
        sys.path.insert(0, cmd_subfolder)

# for linux add Crypto module folder
if sys.platform == 'linux4':
    cmd_subfolder = os.path.realpath(os.path.abspath(os.path.join(os.path.split(inspect.getfile(inspect.currentframe()))[0], 'linux')))
    if cmd_subfolder not in sys.path:
        sys.path.insert(0, cmd_subfolder)

# for rasberrypi add Crypto module folder
if sys.platform == 'linux2':
    cmd_subfolder = os.path.realpath(os.path.abspath(os.path.join(os.path.split(inspect.getfile(inspect.currentframe()))[0], 'linux2')))
    if cmd_subfolder not in sys.path:
        sys.path.insert(0, cmd_subfolder)

try:
    lib = __import__('lib.kshow123', globals(), locals(), ['kshow123'], -1)
except ImportError as e:
    xbmc.log(str(e), level=xbmc.LOGERROR)
    sys.exit();

kshow = lib.create(logger=logger)

def serialize(obj):
    return json.dumps(obj)

def deserialize(name, json_str):
    json_dict = json.loads(json_str)
    return namedtuple(name, json_dict.keys())(**json_dict)      

def build_url(query):
    return base_url + '?' + urllib.urlencode(query)

def kodi_list_shows():
    show_list = kshow.get_shows()
    for show in show_list:
        url = build_url({ 'show': serialize(show) })
        li = xbmcgui.ListItem(show.name, iconImage='DefaultVideo.png')
        xbmcplugin.addDirectoryItem(handle=addon_handle, 
                                    url=url, 
                                    listitem=li,
                                    isFolder=True)

def kodi_list_episodes(show):
    episode_list = kshow.get_episodes(show)
    for episode in episode_list:
        url = build_url({ 'episode': serialize(episode) })
        cover = 'DefaultVideo.png'
        if episode.cover is not None:
            cover = episode.cover
        name = episode.name
        if episode.number is not None:
            name = 'Episode ' + str(episode.number)
        suffix = ''
        if episode.has_sub:
            suffix = ' (SUB)'
        if episode.release is not None:
            suffix += ' - ' + episode.release
        li = xbmcgui.ListItem(name + suffix, 
                              iconImage=cover)
        xbmcplugin.addDirectoryItem(handle=addon_handle, 
                                    url=url, 
                                    listitem=li,
                                    isFolder=True)

def kodi_list_videos(episode):
    video_list = kshow.get_video(episode)
    for video in video_list:
        url = video.file
        name = episode.name
        if episode.number is not None:
            name = 'Episode ' + str(episode.number)
        li = xbmcgui.ListItem(name + ' (' + video.label + ')' + ' - ' + video.kind + ', ' + video.type, 
                              iconImage=video.cover,
        )
        xbmcplugin.addDirectoryItem(handle=addon_handle, 
                                    url=url, 
                                    listitem=li)

base_url = sys.argv[0]
addon_handle = int(sys.argv[1])

xbmcplugin.setContent(addon_handle, 'movies')

arg_show = None
arg_episode = None

args = urlparse.parse_qs(sys.argv[2][1:])
arg_show_json = args.get('show', None)
if arg_show_json is not None:
    arg_show = deserialize('Show', arg_show_json[0])
arg_episode_json = args.get('episode', None)
if arg_episode_json is not None:
    arg_episode = deserialize('Episode', arg_episode_json[0])

if arg_show is not None:
    kodi_list_episodes(arg_show)
elif arg_episode is not None:
    kodi_list_videos(arg_episode)
else:
    kodi_list_shows()

xbmcplugin.endOfDirectory(addon_handle)