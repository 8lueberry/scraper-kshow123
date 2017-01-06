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
    def log(self, message):
        xbmc.log(message)
    def warn(self, message):
        return self.log(message)

logger = Logger()

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
if sys.platform in ('linux2', 'linux4'):
    uname = os.uname()
    if uname[4] == 'armv7l':
        cmd_subfolder = os.path.realpath(os.path.abspath(os.path.join(os.path.split(inspect.getfile(inspect.currentframe()))[0], 'arm')))
    else:
        cmd_subfolder = os.path.realpath(os.path.abspath(os.path.join(os.path.split(inspect.getfile(inspect.currentframe()))[0], 'linux')))

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

def kodi_menu():
    li = xbmcgui.ListItem('Latest')
    li.setArt({
        'icon': 'DefaultRecentlyAddedEpisodes.png',
    })
    xbmcplugin.addDirectoryItem(handle=addon_handle,
                                url=build_url({ 'category': 'latest' }),
                                listitem=li,
                                isFolder=True)

    li = xbmcgui.ListItem('Popular')
    li.setArt({
        'icon': 'DefaultTVShows.png',
    })
    xbmcplugin.addDirectoryItem(handle=addon_handle,
                                url=build_url({ 'category': 'popular' }),
                                listitem=li,
                                isFolder=True)

    li = xbmcgui.ListItem('Top Rated')
    li.setArt({
        'icon': 'DefaultMusicTop100.png',
    })
    xbmcplugin.addDirectoryItem(handle=addon_handle,
                                url=build_url({ 'category': 'rated' }),
                                listitem=li,
                                isFolder=True)

    li = xbmcgui.ListItem('All shows')
    li.setArt({
        'icon': 'DefaultVideoPlaylists.png',
    })
    xbmcplugin.addDirectoryItem(handle=addon_handle,
                                url=build_url({ 'category': 'all' }),
                                listitem=li,
                                isFolder=True)

    li = xbmcgui.ListItem('Search')
    li.setArt({
        'icon': 'DefaultFolder.png',
    })
    xbmcplugin.addDirectoryItem(handle=addon_handle,
                                url=build_url({ 'category': 'search' }),
                                listitem=li,
                                isFolder=True)

def kodi_list_x_shows(page, episode_list, category, link_category='episode'):
    for episode in episode_list:
        url = build_url({ 'category': link_category, 'episode': serialize(episode), 'show': serialize(episode) })
        li = xbmcgui.ListItem(get_episode_name(episode))
        li.setArt(get_episode_cover(episode))
        xbmcplugin.addDirectoryItem(handle=addon_handle,
                                    url=url,
                                    listitem=li,
                                    isFolder=True)

    next_page = str(page + 1)
    li = xbmcgui.ListItem('Next page (page ' + next_page + ')', iconImage='DefaultVideo.png')
    xbmcplugin.addDirectoryItem(handle=addon_handle,
                                url=build_url({ 'category': category, 'page': next_page }),
                                listitem=li,
                                isFolder=True)

def kodi_list_all_shows():
    show_list = kshow.get_shows()
    for show in show_list:
        url = build_url({ 'category': 'episodes', 'show': serialize(show) })
        li = xbmcgui.ListItem(show.show_name)
        li.setArt({
            'icon': 'DefaultFolder.png',
            'fanart': '../backgrounds/tv.jpg',
        })
        xbmcplugin.addDirectoryItem(handle=addon_handle,
                                    url=url,
                                    listitem=li,
                                    isFolder=True)

def kodi_list_episodes(show):
    episode_list = kshow.get_episodes(show)
    for episode in episode_list:
        url = build_url({ 'category': 'episode', 'episode': serialize(episode) })
        li = xbmcgui.ListItem(get_episode_name(episode))
        li.setArt(get_episode_cover(episode))
        xbmcplugin.addDirectoryItem(handle=addon_handle,
                                    url=url,
                                    listitem=li,
                                    isFolder=True)

def kodi_list_servers(episode):
    server_list = kshow.get_episode(episode)
    for server in server_list:
        url = build_url({ 'category': 'file', 'server': serialize(server) })
        name = get_episode_name(episode)
        if server.server_name is not None:
            name = server.server_name + ' (' + server.video_name + ') - ' + name
        li = xbmcgui.ListItem(name)
        li.setArt(get_episode_cover(episode))
        xbmcplugin.addDirectoryItem(handle=addon_handle,
                                    url=url,
                                    listitem=li,
                                    isFolder=True)

def kodi_list_videos(server):
    video_list = kshow.get_video(server)
    for video in video_list:
        url = video.file_url
        name = get_video_name(video)
        li = xbmcgui.ListItem(name)
        li.setInfo('video', { 'title': name })
        li.setArt({
            'icon': video.cover,
            'fanart': video.cover,
        })
        xbmcplugin.addDirectoryItem(handle=addon_handle, 
                                    url=url, 
                                    listitem=li)

def get_episode_name(episode):
    name = episode.show_name + ' - ' + episode.episode_name
    suffix = ''
    if episode.has_sub:
        suffix = ' (SUB)'
    if episode.release is not None:
        suffix += ' - ' + episode.release
    return name + suffix

def get_episode_cover(episode):
    cover = {
        'icon': 'DefaultFolder.png',
        'fanart': 'fanart.jpg',
    }
    if episode.cover is not None:
        cover = {
            'icon': episode.cover,
            'fanart': episode.cover,
        }

    return cover

def get_video_name(video):
    return video.episode_name + ' (' + video.label + ')' + ' - ' + video.kind + ', ' + video.type

def GUIEditExportName(name=''):
    exit = True
    while (exit):
        kb = xbmc.Keyboard('default', 'heading', True)
        kb.setDefault(name)
        kb.setHeading('Search')
        kb.setHiddenInput(False)
        kb.doModal()
        if (kb.isConfirmed()):
            name_confirmed  = kb.getText()
            name_correct = name_confirmed.count(' ')
            if (name_correct):
                name = ''
            else:
                name = name_confirmed
                exit = False
        else:
            name = ''
    return name

base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
xbmcplugin.setContent(addon_handle, 'movies')
args = urlparse.parse_qs(sys.argv[2][1:])

arg_category = args.get('category', [''])[0]

# menu category
if arg_category == 'popular':
    arg_page = args.get('page', ['1'])[0]
    arg_page_int = int(arg_page)
    episode_list = kshow.get_popular_shows(arg_page_int)
    kodi_list_x_shows(arg_page_int, episode_list, arg_category)
elif arg_category == 'latest':
    arg_page = args.get('page', ['1'])[0]
    arg_page_int = int(arg_page)
    episode_list = kshow.get_latest_shows(arg_page_int)
    kodi_list_x_shows(arg_page_int, episode_list, arg_category)
elif arg_category == 'rated':
    arg_page = args.get('page', ['1'])[0]
    arg_page_int = int(arg_page)
    episode_list = kshow.get_rated_shows(arg_page_int)
    kodi_list_x_shows(arg_page_int, episode_list, arg_category)
elif arg_category == 'search':
    arg_query = GUIEditExportName()
    arg_page = args.get('page', ['1'])[0]
    arg_page_int = int(arg_page)
    episode_list = kshow.search_shows(arg_query, arg_page_int)
    kodi_list_x_shows(arg_page_int, episode_list, arg_category, 'episodes')
elif arg_category == 'all':
    kodi_list_all_shows()

# sub category
elif arg_category == 'episodes':
    arg_show_json = args.get('show', [None])[0]
    arg_show = deserialize('Show', arg_show_json)
    kodi_list_episodes(arg_show)
elif arg_category == 'episode':
    arg_episode_json = args.get('episode', [None])[0]
    arg_episode = deserialize('Episode', arg_episode_json)
    kodi_list_servers(arg_episode)
elif arg_category == 'file':
    arg_server_json = args.get('server', [None])[0]
    arg_server = deserialize('Server', arg_server_json)
    kodi_list_videos(arg_server)

else:
    kodi_menu()

xbmcplugin.endOfDirectory(addon_handle)
