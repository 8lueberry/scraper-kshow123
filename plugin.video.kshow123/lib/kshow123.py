from collections import namedtuple
import re
import string
from time import gmtime, strftime
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
    def __init__(self, level=1):
        self.level = level

    def log(self, level, txt):
        """Logs to the logger"""
        if level <= self.level:
            line = strftime("%Y-%m-%d %H:%M:%S", gmtime()) + ' (' + str(level) + ') ' + txt
            print line

    def warn(self, message):
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

Show = namedtuple('Show', 'name url')
Episode = namedtuple('Episode', 'name number url has_sub cover release')
Video = namedtuple('Video', 'id url subUrl')
File = namedtuple('File', 'file label type default kind cover')

###################################################################################################

def decrypt(data, salt):
    password = private_key = PRIVATE_KEY + salt
    return openssl.decrypt(data, password)

class Lib:
    def __init__(self, logger):
        if logger is not None:
            self.logger = logger
        else:
            self.logger = Logger(LOG_LEVEL)

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
                    name=a.get_text(), 
                    url=a.get('href'),
                )
                result.append(show)
        return result

    def get_episodes(self, show):
        """Retrieve the list of episodes for a show"""
        result = []
        soup = self.get_soup(show.url)
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

            episode = Episode(name=name,
                            number=number,
                            cover=cover, 
                            url=a.get('href'), 
                            has_sub=(sub != None),
                            release=release,
            )
            result.append(episode)
        return result

    def get_video(self, episode):
        """Retrieve the video url for an episode"""
        soup = self.get_soup(episode.url)
        container = soup.find(id='content')

        if container is None:
            raise StructureException(episode.url, 'id=content not found')

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

        videos = []

        if videos_m is not None:
            for item in videos_m:
                video = Video(
                    item[0], 
                    item[1].replace('\\/', '/'), 
                    item[2].replace('\\/', '/'),
                )
                videos.append(video)

        video = next((v for v in videos if v.id == current_video_id), None)

        if len(videos) == 0:
            return []

        headers = DEFAULT_HEADER.copy()
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        
        data = urllib.urlencode({ 
            'link': video.url,
            'subUrl': video.subUrl,
            'imageCover': cover,
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

            file = File(
                file=file_path, 
                label=label,
                type=type_str,
                default=default,
                kind=kind,
                cover=cover,
            )
            files.append(file)
        
        return files

def create(logger=None):
    return Lib(logger=logger) 
