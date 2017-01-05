from collections import namedtuple
import re
import string
import time
import urllib
import urllib2
import zlib

from bs4 import BeautifulSoup
import openssl

###################################################################################################
# VARIABLES
###################################################################################################

SOURCE_URL = {
    'site': 'http://kshow123.net',
    'api': 'http://api.kshow123.net/ajax/proxy.php',
    'list': 'http://kshow123.net/show/',
    'popular': 'http://kshow123.net/show/popular/',
    'latest': 'http://kshow123.net/show/latest/',
    'rated': 'http://kshow123.net/show/rated/',
    'search': 'http://kshow123.net/search/',
}

PRIVATE_KEY = 'kshow123.net' + '4590481877' # + '8080'

###################################################################################################
# DO NOT MODIFY
###################################################################################################

UTF8 = 'utf-8'
USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:25.0) Gecko/20100101 Firefox/25.0'
DEFAULT_HEADER = {
    'User-Agent': USER_AGENT,
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'en-US,en;q=0.8',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
    'Connection': 'keep-alive',
    'Referer': SOURCE_URL['site'],
}

RETRY_AMOUNT = 5 # number of time to retry
SLEEP_S = 1 # sleep between request retry

# 5: debug
# 4: network
# 3: 
# 2: 
# 1:
LOG_LEVEL = 4

printable = set(string.printable)

class Logger:
    def __init__(self, logger=None):
        self.logger = logger

    def log(self, level, txt):
        """Logs to the logger"""
        if level <= LOG_LEVEL:
            if self.logger is not None:
                self.logger.log(txt)
            else:
                line = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()) + ' (' + str(level) + ') ' + txt
                print line

    def warn(self, message):
        if self.logger is not None:
            self.logger.warn(message)
        else:
            self.log(1, message)

class StructureException(Exception):
    def __init__(self, page_url='', hint=''):
        super(StructureException, self).__init__()
        self.message = 'Seems like the page structure changed'
        self.url = page_url
        self.hint = hint

    def __str__(self):
        return self.message + '. ' + self.hint + ' (' + self.url + ')'
    def __repr__(self):
        return self.__str__()

###################################################################################################

Show = namedtuple('Show', 'show_name episodes_url has_sub cover')
Episode = namedtuple('Episode', 'show_name episode_name episode_number episode_url has_sub cover release')
Server = namedtuple('Server', 'show_name episode_name episode_number server_name video_id video_name file_url sub_url cover')
File = namedtuple('File', 'show_name episode_name episode_number server_name video_id video_name file_url label type default kind cover')

###################################################################################################

Source = namedtuple('Source', 'name video_id video_name')

def decrypt(data, salt):
    password = private_key = PRIVATE_KEY + salt
    return openssl.decrypt(data, password)

class Lib:
    def __init__(self, logger):
        self.logger = Logger(logger)

    def get_soup(self, url):
        data = self.make_request(url)
        if data:
            return BeautifulSoup(data, 'html.parser')

    def make_request(self, url, data=None, headers=None):
        for i in range(0, RETRY_AMOUNT):
            try:
                return self.do_make_request(url, data, headers)
            except urllib2.URLError as err:
                print 'Network error, retry #' + str(i+1) + ' in ' + str(SLEEP_S) + 's', '(' + str(err) + ')'
                time.sleep(SLEEP_S)
                continue
        raise Exception('Tried ' + str(RETRY_AMOUNT) + ' times, still failed')

    def do_make_request(self, url, data=None, headers=None):
        """Make a request to a server"""

        req_headers = headers
        if req_headers is None:
            req_headers = DEFAULT_HEADER

        req = urllib2.Request(url.encode(UTF8), data, req_headers)

        self.logger.log(4, 'make_request URL: ' + str(req.get_full_url()))
        self.logger.log(5, 'HEADER: ' + str(req.header_items()))
        self.logger.log(5, 'METHOD: ' + str(req.get_method()))
        self.logger.log(5, 'BODY: ' + str(data))
        
        response = urllib2.urlopen(req)
        page = response.read()
        if response.info().getheader('Content-Encoding') == 'gzip':
            self.logger.log(5, 'Response gzip')
            page = zlib.decompress(page, zlib.MAX_WBITS + 16)

        self.logger.log(5, 'RESPONSE: ' + page)
        return page

    def _get_x_shows(self, url, page=1):
        """Retrieve the list of popular shows"""
        result = []
        soup = self.get_soup(url)
        container = soup.find(id='featured')

        if container is None:
            raise StructureException(SOURCE_URL['list'], 'id=featured not found')

        for row in container.find_all('div', class_='row'):
            for col in row.find_all('div'):
                if col is None:
                    continue

                img = col.find('img')
                a = col.find('h2').find('a')
                sub = col.find('span', class_='info-overlay-sub')

                show_name = a.get_text()
                episode_number = '??'
                episode_name = show_name
                name_m = re.search(
                    r'([\s\S]*)episode\s*([\s\S]*)',
                    a.get_text(),
                    re.IGNORECASE
                )
                if name_m is not None:
                    show_name = name_m.group(1)
                    episode_number = name_m.group(2)
                    episode_name = 'Episode ' + episode_number

                episode = Episode(
                    show_name=show_name,
                    episode_name=episode_name,
                    episode_number=episode_number,
                    episode_url=a.get('href'),
                    cover=img.get('src'),
                    has_sub=sub is not None,
                    release=None,
                )
                result.append(episode)
        return result

    def get_popular_shows(self, page=1):
        return self._get_x_shows(url=SOURCE_URL['popular'] + str(page), page=page)

    def get_latest_shows(self, page=1):
        return self._get_x_shows(url=SOURCE_URL['latest'] + str(page), page=page)

    def get_rated_shows(self, page=1):
        return self._get_x_shows(url=SOURCE_URL['rated'] + str(page), page=page)

    def search_shows(self, query, page=1):
        return self._get_x_shows(url=SOURCE_URL['search'] + query + '/' + str(page), page=page)

    def get_shows(self):
        """Retrieve the list of shows"""
        result = []
        soup = self.get_soup(SOURCE_URL['list'])
        container = soup.find(id='content')

        if container is None:
            raise StructureException(SOURCE_URL['list'], 'id=content not found')

        for li in container.find_all('li'):
            for a in li.find_all('a'):
                show = Show(
                    show_name=a.get_text(),
                    episodes_url=a.get('href'),
                    cover=None,
                    has_sub=False,
                )
                result.append(show)
        return result

    def get_episodes(self, show):
        """Retrieve the list of episodes for a show"""
        result = []
        soup = self.get_soup(show.episodes_url)
        container = soup.find(id='list-episodes')

        if container is None:
            raise StructureException(show.url, 'id=list-episodes not found')

        cover = None
        cover_container = soup.find(id='info')
        if cover_container is not None:
            cover_img = cover_container.find('img')
        if cover_img is not None:
            cover = cover_img.get('src').strip()

        table = soup.find('table')
        if table is None:
            raise StructureException(show.url, 'table in id=list-episode not found')

        for tr in table.find_all('tr'):
            h2 = tr.find('h2')
            if h2 is None:
                continue

            release = None
            release_td = tr.find('td', class_='text-right')
            if release_td is not None:
                release = release_td.get_text()

            a = h2.a
            sub = h2.find('span', class_='label-sub')

            name = a.get_text()
            number_m = re.search(
                r'episode\s*(\d*)',
                name,
                re.IGNORECASE
            )
            number = None
            if number_m is not None:
                number = number_m.group(1)

            episode = Episode(
                show_name=show.show_name,
                episode_name=name,
                episode_number=number,
                cover=cover,
                episode_url=a.get('href'),
                has_sub=(sub != None),
                release=release,
            )
            result.append(episode)
        return result

    def get_episode(self, episode):
        """Retrieve the sources of videos"""

        soup = self.get_soup(episode.episode_url)
        container = soup.find(id='content')

        if container is None:
            raise StructureException(episode.url, 'id=content not found')

        # source name
        source_lookup = {}
        ul = soup.find(id='server_list')

        if ul is not None:
            for li in ul.find_all('li', class_='server_item'):
                ul_video_list = li.find('ul', class_='video_list')
                strong = li.find('strong').get_text()
                name_m = re.search(
                    r'([\s\S]*):',
                    strong
                )
                name=strong
                if name_m is not None:
                    name=name_m.group(1)

                if ul_video_list is None:
                    raise StructureException(episode.url, 'Could not get the server list class=video_list')
                for li_video in ul_video_list.find_all('li'):
                    a = li_video.find('a')
                    source_lookup[a.get('id')] = Source(
                        name=name,
                        video_id=a.get('id'),
                        video_name=a.get_text()
                    )

        # current videoid
        current_m = re.search(
            r'currentVideo\s*=\s*[\"\']([^\"\']*)[\"\'];',
            container.script.string
        )

        if current_m is None:
            raise StructureException(episode.url, 'Could not get the current video id')

        current_video_id = current_m.group(1)

        # image
        cover_m = re.search(
            r'imageCover\s*=\s*[\"\']([^\"\']+)[\"\'];',
            container.script.string
        )

        if cover_m is not None:
            cover = cover_m.group(1)
        else:
            warn('Could not retrieve imageCover')
            cover = ''

        # video list
        videos_m = re.findall(
            r'videoId\":(\d*)\s*,\s*\"url\"\s*:\s*\"([^\"]*)\"\s*,\s*\"subUrl\"\s*:\s*\"([^\"]*)\"',
            container.script.string
        )

        servers = []

        if videos_m is not None:
            for item in videos_m:
                source = Source(
                    '??',
                    '??',
                    '??',
                )

                if item[0] in source_lookup:
                    source = source_lookup[item[0]]

                server = Server(
                    show_name=episode.show_name,
                    episode_name=episode.episode_name,
                    episode_number=episode.episode_number,
                    server_name=source.name,
                    video_id=item[0],
                    video_name=source.video_name,
                    file_url=item[1].replace('\\/', '/'),
                    sub_url=item[2].replace('\\/', '/'),
                    cover=episode.cover,
                )
                servers.append(server)

        return servers

    def get_video(self, server):
        """Retrieve the video url for an episode"""

        headers = DEFAULT_HEADER.copy()
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        
        data = urllib.urlencode({
            'link': server.file_url,
            'subUrl': server.sub_url,
            'imageCover': server.cover,
        })

        # ajax call to get video URL
        res = self.make_request(
            SOURCE_URL['api'],
            data,
            headers,
        )

        iframe_m = re.search(
            r'<iframe>',
            res
        )

        if iframe_m is not None:
            warn('Iframe videos not supported')
            return []

        files_m = re.search(
            r'playerInstance\.setup\(([\s\S]*)\);playerInstance.onError',
            res
        )

        js = files_m.group(1)

        image_m = re.search(
            r'image\s*:\s*([^,]*)',
            js
        )

        files_m = re.findall(
            r'[\'\"]?file[\'\"]?\s*:\s*decodeLink\(\"([^\"]*)\"\s*,\s*(\d*)\)\s*,\s*([^}]*)',
            js
        )

        files = []
        for item in files_m:
            file_path = decrypt(item[0], item[1])
            file_path = filter(lambda x: x in printable, file_path)
            file_path = file_path.strip()
            
            info = item[2]
            label_m = re.search(
                r'[\'\"]?label[\'\"]?\s*:\s*\"([^\"]*)\"',
                info
            )
            label = '???'
            if label_m is not None:
                label = label_m.group(1)

            type_m = re.search(
                r'[\'\"]?type[\'\"]?\s*:\s*\"([^\"]*)\"',
                info
            )
            type_str = '???'
            if type_m is not None:
                type_str = type_m.group(1)        

            default_m = re.search(
                r'[\'\"]?default[\'\"]?\s*:\s*\"([^\"]*)\"',
                info
            )
            default = 'false'
            if default_m is not None:
                default = default_m.group(1)

            kind_m = re.search(
                r'[\'\"]?kind[\'\"]?\s*:\s*\"([^\"]*)\"',
                info
            )
            kind = 'video'
            if kind_m is not None:
                kind = kind_m.group(1)

            video = File(
                show_name=server.show_name,
                episode_name=server.episode_name,
                episode_number=server.episode_number,
                server_name=server.server_name,
                video_id=server.video_id,
                video_name=server.video_name,
                file_url=file_path,
                label=label,
                type=type_str,
                default=default,
                kind=kind,
                cover=server.cover,
            )
            files.append(video)
        
        return files

def create(logger=None):
    return Lib(logger=logger) 
