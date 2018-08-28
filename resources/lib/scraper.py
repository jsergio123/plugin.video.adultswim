# -*- coding: utf-8 -*-
# KodiAddon (Adult Swim)
#
import json
import re
import sys
import time
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
# from operator import itemgetter

from metahandler import MetaData
from t1mlib import t1mAddon

lang = xbmcaddon.Addon().getLocalizedString
addon_name = xbmcaddon.Addon().getAddonInfo("name")


class myAddon(t1mAddon):
    def getAddonMenu(self, url, ilist):
        xbmcplugin.setContent(int(sys.argv[1]), 'tvshows')
        response = self.getRequest('http://www.adultswim.com/videos')
        data = re.search("""__AS_INITIAL_STATE__\s*=\s*({.*?})</script>""", response).groups()[0]
        data = json.loads(data.replace("\/", "/"))
        shows = data.get("showsIndex").get("shows")
        getmeta = xbmcaddon.Addon().getSetting("getmeta")

        blacklist = ["live simulcast", "music videos", "on cinema", "promos", "shorts", 'williams street swap shop',
                     "stupid morning bullshit", 'last stream on the left', 'fishcenter live', 'convention panels']

        if getmeta == 'true':
            i = 0
            total = len(shows)
            p_dialog = xbmcgui.DialogProgressBG()
            p_dialog.create(lang(34001).encode('utf-8'), '')
            p_dialog.update(i, lang(34001).encode('utf-8'), lang(34002).encode('utf-8'))

        for show in shows:
            name = show.get("title", "No Title").encode("utf-8")
            if not any(x in name.lower() for x in blacklist):
                context_menu = []
                if getmeta == 'true':
                    info_list = MetaData().get_meta(name=name)
                    context_menu.append((lang(34003).encode('utf-8'), 'Action(Info)'))
                    poster = info_list.get('cover_url')
                    if poster == '':
                        poster = show.get("poster", self.addonIcon)
                    fanart = info_list.get('backdrop_url')
                    if fanart == '':
                        fanart = self.addonFanart
                    i += 1
                    percent = int((i / float(total)) * 100)
                    p_dialog.update(percent, lang(34001).encode('utf-8'), lang(34002).encode('utf-8'))
                else:
                    poster = show.get("poster", self.addonIcon)
                    fanart = self.addonFanart
                    info_list = {'Title': name, 'TVShowTitle': name, 'mediatype': 'tvshow', 'Studio': 'Adult Swim',
                                 'cover_url': poster, 'backdrop_url': fanart}

                response = 'http://www.adultswim.com%s' % show.get("url")
                ilist = self.addMenuItem(name, 'GE', ilist, response, poster, fanart, info_list, isFolder=True,
                                         cm=context_menu)
            else:
                continue

        if getmeta == 'true':
            try: p_dialog.close()
            except: pass

        return ilist

    def getAddonEpisodes(self, url, ilist):
        html = self.getRequest(url)
        data = re.search("""__AS_INITIAL_DATA__\s*=\s*({.*?});""", html).groups()[0]
        data = json.loads(data.replace("\/", "/"))
        show = data.get("show")
        episodes = show.get("videos")
        # episodes = sorted(episodes, key=itemgetter('launch_date'))
        display_locked = xbmcaddon.Addon().getSetting("display_locked")

        for episode in episodes:
            if episode.get("type") == 'episode':
                if display_locked == 'false' and episode.get("auth", False):
                    continue
                else:
                    name = episode.get('title').encode("utf-8")
                    name = name if not episode.get("auth", False) else "[COLOR red]%s[/COLOR]" % name
                    fanart = show.get("heroImage", self.addonFanart)
                    thumb = episode.get("poster", show.get("metadata").get("thumbnail"))
                    infoList = {}
                    infoList['Date'] = time.strftime('%Y-%m-%d', time.localtime(int(episode.get('launch_date', episode.get('auth_launch_date', 0)))))
                    infoList['Aired'] = infoList['Date']
                    infoList['Duration'] = str(int(episode.get('duration', '99999')))
                    infoList['MPAA'] = episode.get('tv_rating', 'N/A')
                    infoList['TVShowTitle'] = episode.get('collection_title')
                    infoList['Title'] = name
                    infoList['Episode'] = episode.get("episode_number")
                    infoList['Season'] = episode.get("season_number")
                    infoList['Plot'] = episode.get("description", "").encode("utf-8")
                    infoList['mediatype'] = 'episode'
                    url = episode.get("id")
                    ilist = self.addMenuItem(name, 'GV', ilist, url, thumb, fanart, infoList, isFolder=False)

        if len(ilist) == 0:
            ilist = self.addMenuItem(lang(34004).encode('utf-8'), 'GV', ilist, '', self.addonIcon,
                                     self.addonFanart, '', isFolder=False)

        return ilist

    def getAddonVideo(self, url):
        api_url = 'http://www.adultswim.com/videos/api/v3/videos/%s?fields=title,type,duration,collection_title,poster,stream,segments,title_id' % url
        api_data = self.getRequest(api_url)
        api_data = json.loads(api_data)
        urls = api_data.get('data').get('stream').get('assets')
        url = [url.get('url') for url in urls if url.get('mime_type') == 'application/x-mpegURL' and (url.get('url').endswith("stream_full.m3u8") or url.get('url').endswith("/stream.m3u8"))][0]
        sources = self.getRequest(url)
        sources = re.findall('BANDWIDTH=(\d+).+?\n([^#\s]+)', sources, re.I)
        sources = sorted(sources, key=lambda x: int(x[0]), reverse=True)
        autoplay = xbmcaddon.Addon().getSetting("autoplay")
        total_srcs = len(sources)
        if total_srcs > 1 and autoplay == 'false':
            dialog = xbmcgui.Dialog()
            src = dialog.select(lang(34005).encode('utf-8'), [str(i[0]).encode("utf-8") for i in sources])
            if src == -1:
                dialog.notification(addon_name, lang(34006).encode('utf-8'), xbmcgui.NOTIFICATION_WARNING, 3000)
                return
            else:
                u = '%s/%s' % (url.rsplit('/', 1).pop(0), sources[src][1].strip())
        elif total_srcs == 1 or (total_srcs > 1 and autoplay == 'true'):
            u = '%s/%s' % (url.rsplit('/', 1).pop(0), sources[0][1].strip())
        else:
            dialog = xbmcgui.Dialog()
            dialog.notification(addon_name, lang(34007).encode('utf-8'), xbmcgui.NOTIFICATION_WARNING, 3000)
            return
        liz = xbmcgui.ListItem(path = u)
        info_list = {'mediatype': xbmc.getInfoLabel('ListItem.DBTYPE'), 'Title': xbmc.getInfoLabel('ListItem.Title'),
                     'TVShowTitle': xbmc.getInfoLabel('ListItem.TVShowTitle'),
                     'Year': xbmc.getInfoLabel('ListItem.Year'), 'Premiered': xbmc.getInfoLabel('Premiered'),
                     'Plot': xbmc.getInfoLabel('ListItem.Plot'), 'Studio': xbmc.getInfoLabel('ListItem.Studio'),
                     'Genre': xbmc.getInfoLabel('ListItem.Genre'), 'Duration': xbmc.getInfoLabel('ListItem.Duration'),
                     'MPAA': xbmc.getInfoLabel('ListItem.Mpaa'), 'Aired': xbmc.getInfoLabel('ListItem.Aired'),
                     'Season': xbmc.getInfoLabel('ListItem.Season'), 'Episode': xbmc.getInfoLabel('ListItem.Episode')}
        liz.setInfo('video', info_list)
        xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, liz)
