from random import randint

import lib.kshow123 as lib

default = lib.create()

def simulate():
    """Simulates a user action"""
    default.logger.log(2, 'Get list of shows')
    shows = default.get_shows()
    default.logger.log(2, 'Got ' + str(len(shows)) + ' shows')
    for idx, show in enumerate(shows):
        default.logger.log(3, str(idx) + ' - ' + show.name)

    show_idx = randint(0, len(shows)-1)
    show = shows[show_idx]
    default.logger.log(2, 'Randomly choosing: ' + show.name + ' (' + show.url + ')')
    default.logger.log(2, 'Get list of episodes')    
    episodes = default.get_episodes(show)
    default.logger.log(2, 'Got ' + str(len(episodes)) + ' episodes')
    for idx, episode in enumerate(episodes):
        prefix = ''
        if episode.has_sub:
            prefix += 'SUB'
        default.logger.log(3, str(idx) + ' - ' + prefix + ' ' + episode.name)

    episode_idx = randint(0, len(episodes)-1)
    episode = episodes[episode_idx]
    default.logger.log(2, 'Randomly choosing: ' + episode.name + ' (' + episode.url + ')')
    default.logger.log(2, 'Get list of videos')
    videos = default.get_video(episode)
    default.logger.log(2, 'Got ' + str(len(videos)) + ' videos')

    for video in videos:
        default.logger.log(3, video.kind + ' ' + video.label + ' ' + video.file)

simulate()