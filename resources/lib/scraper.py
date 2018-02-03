# -*- coding: utf-8 -*-
# KodiAddon (Adult Swim)
#
from t1mlib import t1mAddon
from operator import itemgetter
from metahandler import metahandlers,metacontainers
import json, re, urllib, urllib2, xbmcaddon, xbmcplugin, xbmcgui, xbmc, time, sys, os

metaget = metahandlers.MetaData(preparezip=False)


class myAddon(t1mAddon):
    def getAddonMenu(self, url, ilist):
        xbmcplugin.setContent(int(sys.argv[1]), 'tvshows')
        epiHTML = self.getRequest('http://www.adultswim.com/videos')
        shows = re.search("""__AS_INITIAL_DATA__\s*=\s*({.*?});""", epiHTML).groups()[0]
        shows = json.loads(shows.replace("\/", "/"))
        shows = shows["shows"]
        getmeta = xbmcaddon.Addon().getSetting("getmeta")
        
        blacklist = ["live simulcast", "music videos", "on cinema", "promos", "shorts", 'williams street swap shop', 'stupid morning bullshit', 'last stream on the left', 'fishcenter live', 'convention panels']
        
        if getmeta == 'true':
            i = 0
            total = len(shows)
            pDialog = xbmcgui.DialogProgressBG()
            pDialog.create('MetaData Progress', '')
            pDialog.update(i, 'MetaData Progress', 'Retrieving MetaData Information')
        
        for show in shows:
            name = show["title"].encode("utf-8")
            if not any(x in name.lower() for x in blacklist):
                contextMenu = []
                if getmeta == 'true':
                    infoList = metaget.get_meta('tvshow', name=name)
                    contextMenu.append(('View TV Show Info', 'Action(Info)'))
                    poster = infoList['cover_url']
                    if poster == '': poster = self.addonIcon
                    fanart = infoList['backdrop_url']
                    if fanart == '': fanart = self.addonFanart
                    i += 1
                    percent = int( ( (i) / float(total) ) * 100)
                    pDialog.update(percent, 'MetaData Progress', 'Retrieving MetaData Information')
                else:
                    poster = self.addonIcon
                    fanart = self.addonFanart
                    infoList = {}
                    infoList['Title'] = name
                    infoList['TVShowTitle'] = name
                    infoList['mediatype'] = 'tvshow'
                    infoList['Studio'] = 'Adult Swim'
                    
                url = 'http://www.adultswim.com' + show["url"]
                ilist = self.addMenuItem(name, 'GE', ilist, url, poster, fanart, infoList, isFolder=True, cm=contextMenu)
            else:
                continue
                
        if getmeta == 'true':
            try: pDialog.close()
            except: pass
                
        return(ilist)

    def getAddonEpisodes(self, url, ilist):
        html = self.getRequest(url)
        epis = re.search("""__AS_INITIAL_DATA__\s*=\s*({.*?});""", html).groups()[0]
        epis = json.loads(epis.replace("\/", "/"))
        show = epis["show"]
        epis = show["videos"]
        #epis = sorted(epis, key=itemgetter('launch_date'))
        display_locked = xbmcaddon.Addon().getSetting("display_locked")

        for epi in epis:
            if epi["type"] == 'episode':
                if display_locked == 'false' and epi["auth"]: continue
                else:
                    name = epi['title'].encode("utf-8")
                    name = name if not epi.get("auth", False) else "[COLOR red]%s[/COLOR]" % name
                    try: fanart = show["heroImage"] if not show.get("heroImage", "") == "" else self.addonFanart
                    except: fanart = self.addonFanart
                    try: thumb = epi["poster"] if not epi.get("poster", "") == "" else show["metadata"]["thumbnail"]
                    except: thumb = self.addonIcon
                    infoList = {}
                    try: infoList['Date'] = time.strftime('%Y-%m-%d', time.localtime(int(epi['launch_date'])))
                    except: infoList['Date'] = time.strftime('%Y-%m-%d', time.localtime(int(epi['auth_launch_date'])))
                    infoList['Aired'] = infoList['Date']
                    infoList['Duration'] = str(int(epi.get('duration', '0')))
                    infoList['MPAA'] = epi.get('tv_rating', 'N/A')
                    try: infoList['TVShowTitle'] = epi['collection_title']
                    except: pass
                    infoList['Title'] = name
                    try: infoList['Episode'] = epi["episode_number"]
                    except: pass
                    try: infoList['Season'] = epi["season_number"]
                    except: pass
                    infoList['Plot'] = epi.get("description", "").encode("utf-8")
                    infoList['mediatype'] = 'episode'
                    url = epi["id"]
                    ilist = self.addMenuItem(name, 'GV', ilist, url, thumb, fanart, infoList, isFolder=False)

        if len(ilist) == 0:
            ilist = self.addMenuItem("No episodes available to stream", 'GV', ilist, '', self.addonIcon, self.addonFanart, '', isFolder=False)

        return(ilist)

    def getAddonVideo(self, url):
        ep_id = url
        api_url = 'http://www.adultswim.com/videos/api/v0/assets?platform=desktop&id=%s&phds=true' % ep_id
        api_data = self.getRequest(api_url)
        sources = re.findall("""<file .*?type="([^"]+).+?>([^<\s]+)""", api_data)
        from urlparse import urlparse
        sources = [(source[0], source[1]) for source in set(sources) if not urlparse(source[1]).path.split('/')[-1].endswith(".f4m")]
        sources = sorted(sources, key=itemgetter(0))
        autoplay = xbmcaddon.Addon().getSetting("autoplay")
        totalSrcs = len(sources)
        if totalSrcs > 1 and autoplay == 'false':
            dialog = xbmcgui.Dialog()
            src = dialog.select('Choose a stream', [str(i[0]).encode("utf-8") for i in sources])
            if src == -1:
                dialog.notification("Adult Swim", 'Stream selection canceled', xbmcgui.NOTIFICATION_WARNING, 3000)
                return
            else:
                u = sources[src][1]
        elif totalSrcs == 1 or (totalSrcs > 1 and autoplay == 'true'):
            u = sources[0][1]
        else: 
            dialog = xbmcgui.Dialog()
            dialog.notification("Adult Swim", 'No playable streams found', xbmcgui.NOTIFICATION_WARNING, 3000)
            return
        liz = xbmcgui.ListItem(path = u)
        infoList ={}
        infoList['mediatype'] = xbmc.getInfoLabel('ListItem.DBTYPE')
        infoList['Title'] = xbmc.getInfoLabel('ListItem.Title')
        infoList['TVShowTitle'] = xbmc.getInfoLabel('ListItem.TVShowTitle')
        infoList['Year'] = xbmc.getInfoLabel('ListItem.Year')
        infoList['Premiered'] = xbmc.getInfoLabel('Premiered')
        infoList['Plot'] = xbmc.getInfoLabel('ListItem.Plot')
        infoList['Studio'] = xbmc.getInfoLabel('ListItem.Studio')
        infoList['Genre'] = xbmc.getInfoLabel('ListItem.Genre')
        infoList['Duration'] = xbmc.getInfoLabel('ListItem.Duration')
        infoList['MPAA'] = xbmc.getInfoLabel('ListItem.Mpaa')
        infoList['Aired'] = xbmc.getInfoLabel('ListItem.Aired')
        infoList['Season'] = xbmc.getInfoLabel('ListItem.Season')
        infoList['Episode'] = xbmc.getInfoLabel('ListItem.Episode')
        liz.setInfo('video', infoList)
        xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, liz)
