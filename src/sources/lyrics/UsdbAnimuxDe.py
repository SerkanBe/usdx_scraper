import time

import requests, zipfile, io, os, re
from requests.adapters import HTTPAdapter, Retry
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from math import ceil, floor

from .LyricsSourceBase import LyricsSourceBase
from ...ColorPrint import ColorPrint
from ...EventManager import event_manager
from ...dataObjects.Song import Song


class UsdbAnimuxDe(LyricsSourceBase):

    LOGIN_URL = 'https://usdb.animux.de/index.php?&link=login'
    SONG_URL = 'https://usdb.animux.de/index.php?link=detail&id='
    SEARCH_URL = 'https://usdb.animux.de/?link=list'
    ZIP_URL = 'https://usdb.animux.de/index.php?&link=ziparchiv'
    ZIP_SAVE_URL = 'https://usdb.animux.de/index.php?&link=ziparchiv&save=1'
    DOWNLOAD_URL = "https://usdb.animux.de/data/downloads"

    STRINGS = {
        "en": {
            "LOGIN_FAILED": "Login or Password invalid, please try again."
        },
        "de": {
            "LOGIN_FAILED": "Login or Password invalid, please try again."
        }
    }

    REGEXES = {
        "en": {
            "NUMBER_RESULTS": r'There\s*are\s*(\d+)\s*results\s*on\s*\d+\s*page',
            "NUMBER_PAGES": r'There\s*are\s*\d+\s*results\s*on\s*(\d+)\s*page',
            "SEARCH_RESULT_SONG_ID": r'data-songid="(\d+)"'
        },
        "de": {
            "NUMBER_RESULTS": r'Es gibt\s+(\d)+\s+Resultate auf\s+\d+\s+Seite',
            "NUMBER_PAGES": r'Es gibt\s+\d+\s+Resultate auf\s+(\d+)\s+Seite',
            "SEARCH_RESULT_SONG_ID": r'data-songid="(\d+)"'
        }
    }

    username = ''
    password = ''
    session = None
    logged_id = False
    language = 'en'

    def __init__(self):
        event_manager.register('post_parser_init', self.event_post_parser_init)
        event_manager.register("parser_parse_args", self.event_parser_parse_args)

        self.username = os.getenv("LYRICS_SOURCE__USDB_ANIMUX_DE__USERNAME").split(",") or self.username
        self.password = os.getenv("LYRICS_SOURCE__USDB_ANIMUX_DE__PASSWORD").split(",") or self.password
        self.session = self._create_session()
        self.logged_id = False
        self.language = os.getenv("LYRICS_SOURCE__USDB_ANIMUX_DE__LANGUAGE") or self.language

    @staticmethod
    def event_post_parser_init(parser):
        parser.add_argument("--usdb_animux_user", action="store", help="The user to use on http://usdb.animux.de/, required")
        parser.add_argument("--usdb_animux_pass", action="store", help="The password for the user, required")

    def event_parser_parse_args(self, args):
        self.username = args.usdb_animux_user or self.username
        self.password = args.usdb_animux_pass or self.password

    def _create_session(self):
        if not self.session:
            session = requests.Session()
            retries = Retry(total=5, backoff_factor=1, status_forcelist=[502, 503, 504])
            session.mount('https://', HTTPAdapter(max_retries=retries))
            self.session = session

        return self.session


    def search_songs(self, songs: list[Song]) -> list[Song]:
        missing_lyrics_songs = []
        try:
            if not self.logged_id:
                self._login()
        except Exception as e:
            ColorPrint.raise_error(f"Could not login: {e}")

        for song in songs:
            source_urls = self._search_exact(artists=song.artists, title=song.title)
            if not source_urls:
                missing_lyrics_songs.append(song)
            else:
                song.add_lyrics_source(self.__class__.__name__, set(source_urls))

        return missing_lyrics_songs


    def _login(self):
        login_payload ={
            'user': self.username,
            'pass': self.password,
            'login': 'Login'
        }
        login_payload = login_payload
        response = self.session.post(self.LOGIN_URL, data=login_payload)

        if self.STRINGS[self.language]['LOGIN_FAILED'] in response.text:
            raise Exception("Could not authenticate")

    def _search_exact(self, artists: list[str], title: str) -> str|None:
        # Just stick the artists together
        interpret = " ".join(artists)
        search_payload = {
            'interpret': interpret,
            'title': title
        }
        search_response = self.session.post(self.SEARCH_URL, data=search_payload)
        html = search_response.text
        #html = self.__html()
        num_results = re.findall(self.REGEXES[self.language]['NUMBER_RESULTS'], html)

        if not num_results or num_results[0] == '0':
            # ColorPrint.print(ColorPrint.WARNING, f"No results found for '{title}' by '{interpret}'")
            return None
        elif num_results[0] != '1':
            ColorPrint.print(ColorPrint.WARNING, f"Found {num_results[0]} results for '{title}' by '{interpret}'")
            return None
        else:
            source_url = self._extract_source_url(html)

        return source_url

    def _extract_source_url(self, search_results):
        id = re.findall(self.REGEXES[self.language]['SEARCH_RESULT_SONG_ID'], search_results)[0]
        return self.SONG_URL + id


    ######################################################################################################################################################
    ######################################################################################################################################################
    ######################################################################################################################################################
    ######################################################################################################################################################

    def _search_exact__(self, artists: list[str], title: str) -> dict[LyricsSourceBase, str]:
        # todo: Figure out what to do if we have multiple artists...
        artist_string = " ".join(artists)
        payload = self.create_search_payload(interpret=artist_string, title=title)
        search_string_representation = f"(artist_string: {artist_string}, title_string: {title})"

        response = self.session.post(self.SEARCH_URL, data=payload)
        html = response.text
        search_soup = BeautifulSoup(response.text, 'html5lib')

        if "There are  0  results on  0 page(s)" in response.text:
            ColorPrint.print(ColorPrint.WARNING, f"No results found for '{title}' by '{artist_string}'")
            return {self.__class__: ''}

        # Check for next pages
        results_strings = [

        ]
        # Look for the string in different languages, take the first one found.
        counter = 0
        for regex in results_strings:
            counter_string = re.findall(pattern=string_regex,string=html,flags=re.DOTALL)
            if counter_string is None:
                continue

            counter = int(re.search(r'\d+', counter_string).group(0))
            if counter > 0:
                print(f"Found counter: {counter}")
                break

        no_of_pages = ceil(counter / 100)
        # print(f"No of Pages: {no_of_pages}")

        search_results = []
        for i in range(no_of_pages):
            if i != 0:
                # print(f"Changing pages to : {i*100}")
                payload = self.create_search_payload(interpret=artist_string, title=title, start=i * 100)
                response = self.session.post(self.SEARCH_URL, data=payload)

            search_soup = BeautifulSoup(response.text, 'html5lib')

            result_regex = re.compile(r'list_tr1|list_tr2')
            href_regex = re.compile(r'\?link=detail&id=')
            result_tags = search_soup.findAll("tr",
                                              attrs={"class": result_regex, "onmouseover": "this.className='list_hover'"})

            for tag in result_tags:
                a_tag = tag.find("a", recursive=True, href=href_regex)
                id = parse_qs(urlparse(a_tag.get("href")).query)['id'][0]
                title = a_tag.contents[0]
                artist = tag.find("td").contents[0]

                print(f"Found match: {search_string_representation} -> {artist} - {title}")
                search_results.append([id, f"{artist} - {title}"])

        return search_results

    # Download all Textfiles for USDX from http://usdb.animux.de/
    def _download_lyrics(self, cookie: str, download_url: str, directory: str) -> str:

        # Use the websites cookies to trick the site into putting all of the IDs into one download ZIP
        self.session.cookies.set('counter', '1')
        self.session.cookies.set('ziparchiv', cookie)

        # An authorized request.
        r = self.session.get(self.ZIP_URL)
        if not r.ok: raise ConnectionError
        r = self.session.get(self.ZIP_SAVE_URL)
        if not r.ok: raise ConnectionError
        r = self.session.get(download_url)
        if not r.ok: raise ConnectionError

        # Get ZIP and unpack
        z = zipfile.ZipFile(io.BytesIO(r.content))
        filename, _ = os.path.split(z.namelist()[0])
        z.extractall(directory)

        return filename

    def download_all_lyrics(self, song_list: list) -> list[str]:
        cookie_list = self.create_cookies(song_list)
        download_url = self.create_personal_download_url(self.username)

        folder_list = []

        # Run function for each cookie in cookie_list
        for count, cookie in enumerate(cookie_list):
            print(f"[{(count + 1):04d}/{len(cookie_list):04d}] Downloading .txt files with cookie = {cookie[:-1]}")
            # Download txt files with cookie
            try:
                folder = self.download_lyrics(cookie, download_url, self.output_directory)
                if not folder in folder_list:
                    folder_list.append(folder)
                else:
                    print(f"[{(count + 1):04d}/{len(cookie_list):04d}] This song already exists, skipping...")
                    folder_list.append(None)
            except ConnectionError or requests.exceptions.RetryError:
                print(
                    f"[{(count + 1):04d}/{len(cookie_list):04d}] Error while downloading .txt files, skipping {cookie[:-1]}...")
                folder_list.append(None)

        log_file = open('./download_all_lyrics.log', 'a')
        log_file.writelines(f"{folder_list.__str__()}\n")

        return folder_list


    # Create personal download URL for http://usdb.animux.de/
    def create_personal_download_url(self, user:str) -> str:
        zip_name = f"{user.lower()}-playlist.zip?t={floor(time.time())}"
        return f"{self.DOWNLOAD_URL}/{zip_name}"

    # Create a list of cookies which contain all song IDs
    def create_cookies(self, song_list: list) -> list:
        cookie_list = []
        i = 0
        for song in song_list:
            cookie_list.append("")
            cookie_part = song[0] + "|"
            cookie_list[i] += cookie_part
            i += 1

        return cookie_list


    def get_song_url(self, song_id):
        return self.SONG_URL + song_id




    @staticmethod
    def __html():
        return """
        <html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset="utf-8">
<link rel="SHORTCUT ICON" href="images/browser_icon.ico">
<link title="USDB" href="https://usdb.animux.de/scripts/opensearch_desc.xml" type="application/opensearchdescription+xml" rel="search"/>
<link rel="stylesheet" href="style/css.css?ts=1719929515" type="text/css" />
<link rel="stylesheet" href="style/niksac.css" type="text/css" />
<link rel="stylesheet" href="style/l19g2004.css" type="text/css" />
<link rel="alternate" type="application/rss+xml" title="US New Songs Top 10" href="rss/rss_new_top10.php">
<link rel="alternate" type="application/rss+xml" title="US Downloads Top 10" href="rss/rss_downloads_top10.php">

<title>USDB - Suchresultate</title>
</head>
<body>


<table width='100%' cellspacing='0' cellpadding='0' border='0'>
	<tr>

			<td width='20%' valign='top'>
    <table class='tablebg' width='100%' cellspacing='1'>

		<tr><th><span class='syntaxcomment style3'><b>Options</b></span></th></tr>
			<tr>

				<td class='row1'><b class='nav'>Options</b>

			<ul class='nav' style='margin: 0px; padding: 0px; list-style-type: none; line-height: 175%;'>

	
			<li>&#187; <a href=?link=home class='Linkz'>Start</a></li>
			<li>&#187; <a href=?link=browse class='Linkz'>Songs durchsuchen</a></li>
			<li>&#187; <a href=?link=singstar_editions class='Linkz'>Singstar Editionen</a></li>
			<li>&#187; <a href=?link=addsongs class='Linkz'>Songs hinzufügen</a></li>
			<li>&#187; <a href=?link=calendar class='Linkz'>Song Kalender</a></li>
			<li>&#187; <a href=?link=pm class='Linkz'>Private Nachrichten</a></li>
			<li>&#187; <a href=?link=profil class='Linkz'>Profil</a></li>
			<li>&#187; <a href=?link=profil&edit=Einstellungen class='Linkz'>Einstellungen</a></li>
			<li>&#187; <a href=?link=userlist class='Linkz'>Benutzerliste</a></li>
			<li>&#187; <a href=?link=logout class='Linkz'><font color='red'>Ausloggen</font></a></li>
			<li>&#187; <a href=?link=feature_request class='Linkz'>Verbesserungs- & Fehlerliste</a></li>
			<li>&#187; <a href=?link=say_smthng class='Linkz'>Sag Etwas</a></li>
			<li>&#187; <a href=?link=wishlist class='Linkz'>Wunschliste</a></li></ul>
			</td>
		</tr>
	</table>
</td><Center></Center><td><img src='images/spacer.gif' width='4' alt='' /></td>

<td width='80%' valign='top'>

<script src='scripts/ziparchiv.js' type='text/javascript'></script>

<body onload='getCookieCounter("Songs im Archiv")'>

<table class='tablebg' width='100%' cellspacing='1' id='tablebg'>

	<tr>
		<th colspan='2' valign='middle'><span class='syntaxcomment style3'><b>Suchresultate</b></span></th>
	</tr>

	<tr>
		<td class='row3' colspan='2'>
		<span class='gen'>Willkommen <b>FragDenWayne</b>, du hast <a href="?link=pm"><span class="style_pm">keine</span> Nachricht(en)</a><br><br></span>
		</td>
	</tr>

<center><tr><td class='row1'>
	<body onLoad="vorladen()">
<script type="text/javascript">
function vorladen()
{
    var Bild  = new Image();
    Bild.src  = "images/rss-icon_over.png";
    var Bild2 = new Image();
    Bild2.src = "images/rss-icon.png";
}
function changepage(start)
{
document.getElementById('form_start').value = start; //Funktion setzt den Wert Start im Formular unten (hidden) auf parameter und
document.getElementById('oaform').submit();          //sendet das Ding ab
}

function show_detail(id) //tabellenzeilen haben onclick das hier und geben id mit (link)
{
window.location.href = '?link=detail&id='+id;
}
</script>

<br>Es gibt  1  Resultate auf  1 Seite(n)<a href="rss/rss_interpret.php?interpret=RIAN" onMouseOver="document.rss2.src='images/rss-icon_over.png';" onMouseOut="document.rss2.src='images/rss-icon.png';"><img src="images/rss-icon.png" name="rss2" alt="rss" border=0></a><br><br>

<table border="0" width="100%">
<tr class="list_head"><td><a href='?link=list&amp;start=0&amp;interpret=RIAN&amp;title=Verwandtschaftstreffen%20%28Weihnachtsversion%29&amp;order=interpret' id="list_artist">Interpret</a></td><td><a href='?link=list&amp;start=0&amp;interpret=RIAN&amp;title=Verwandtschaftstreffen%20%28Weihnachtsversion%29&amp;order=title' id="list_title">Titel</a></td><td><a href='?link=list&amp;start=0&amp;interpret=RIAN&amp;title=Verwandtschaftstreffen%20%28Weihnachtsversion%29&amp;order=genre' id="list_genre">Genre</a></td><td><a href='?link=list&amp;start=0&amp;interpret=RIAN&amp;title=Verwandtschaftstreffen%20%28Weihnachtsversion%29&amp;order=year' id="list_year">Jahr</a></td><td><a href='?link=list&amp;start=0&amp;interpret=RIAN&amp;title=Verwandtschaftstreffen%20%28Weihnachtsversion%29&amp;order=edition' id="list_edition">Edition</a></td><td><a href='?link=list&amp;start=0&amp;interpret=RIAN&amp;title=Verwandtschaftstreffen%20%28Weihnachtsversion%29&amp;order=golden' id="list_gnotes">Goldene Noten</a></td><td><a href='?link=list&amp;start=0&amp;interpret=RIAN&amp;title=Verwandtschaftstreffen%20%28Weihnachtsversion%29&amp;order=language' id="list_language">Sprache</a></td><td><a href='?link=list&amp;start=0&amp;interpret=RIAN&amp;title=Verwandtschaftstreffen%20%28Weihnachtsversion%29&amp;order=autor' id="list_autor">Creator</a></td><td><a href='?link=list&amp;start=0&amp;interpret=RIAN&amp;title=Verwandtschaftstreffen%20%28Weihnachtsversion%29&amp;order=rating' id="list_rating">Bewertung</a></td><td><a href='?link=list&amp;start=0&amp;interpret=RIAN&amp;title=Verwandtschaftstreffen%20%28Weihnachtsversion%29&amp;order=views' id="list_views">Aufrufe</a></td><td>&nbsp;</td><tr class="list_tr2" data-songid="31174" data-lastchange="1759444660" onmouseover="this.className='list_hover'" onmouseout="this.className='list_tr2'"><td onclick="show_detail(31174)">RIAN</td>
<td onclick="show_detail(31174)"><a href="?link=detail&id=31174">Verwandtschaftstreffen (Weihnachtsversion)</td>
<td onclick="show_detail(31174)">Pop</td>
<td onclick="show_detail(31174)">2024</td>
<td onclick="show_detail(31174)"></td>
<td onclick="show_detail(31174)">Ja</td>
<td onclick="show_detail(31174)">German</td>
<td onclick="show_detail(31174)">ultron, Edi316, bohning</td>
<td onclick="show_detail(31174)"><img src="images/star2.png"> <img src="images/star2.png"> <img src="images/star2.png"> <img src="images/star2.png"> <img src="images/star2.png"> </td>
<td onclick="show_detail(31174)">16</td>
<td><a  href="#" onClick="addToList(31174, 1)"><img src="images/mini-zip.png" border="0"></a></td>
</tr>
</tr>
</table>



<br>
<a href="javascript:changepage(0)"><b><u>[1]</u></b></a> 
<br><br>
<!-- Formular mit Standartwerden beladen -->

<form id="oaform" method='post' name='listform' action='?link=list'>
<input name='interpret' value="RIAN"> Interpret (leer für beliebig)<br>
<input name='title' value="Verwandtschaftstreffen (Weihnachtsversion)"> Titel (leer für beliebig)<br>
<input name='edition' value=""> Edition (leer für beliebig)<br>
<input name='language' value=""> Sprache (leer für beliebig)<br>
<input name='genre' value=""> Genre (leer für beliebig)<br>
<input name='year' value=""> Jahr (leer für beliebig)<br>
<input name='creator' value=""> Creator (leer für beliebig)<br>
<input type='hidden' name='user' value=''>sortieren nach <select name='order'>
<option value='id'>Datum</option>
<option value='interpret'>Interpret</option>
<option value='title'>Titel</option>
<option value='genre'>Genre</option>
<option value='year'>Jahr</option>
<option value='edition'>Edition</option>
<option value='golden'>Goldene Noten</option>
<option value='language'>Sprache</option>
<option value='autor'>Creator</option>
<option value='rating'>Bewertung</option>
<option value='views'>Aufrufe</option>
<option value='lastchange'>Zuletzt geändert</option>
</select> in<select name='ud'>
<option value='asc'>aufsteigender</option>
<option value='desc'>absteigender</option>
</select> Reihenfolge<br>
<input name='limit' value="30"> Einträge pro Seite<br>
<input type="checkbox" id="cb_golden" name="golden" value="1"><label for="cb_golden">nur mit goldenen Noten</label><br>
<input type="checkbox" id="cb_songcheck" name="songcheck" value="1"><label for="cb_songcheck">nur [SC]-Songs</label><br>
<input type="checkbox" id="cb_details" name="details" value="1"><label for="cb_details">Audio Sample und Cover anzeigen</label><br>
<input id="form_start" type='hidden' name="start" value='0'>
<input id="form_search" type='submit' name="newsearch" value='Suche starten'>
</form>


</td></tr></center>
<tr>
	<td class='cat' colspan='2' align='center'><input class='btnmain' type='hidden' name='submit' value='Submit' />&nbsp;&nbsp;
	  <input class='btnlite' type='hidden' value='Reset' name='reset' /></td>
</tr>
</table>
</td>
	</tr>
		</table>
	

<script type="text/javascript">
function artist(name)
{
document.getElementById('artistform_name').value = name;
document.getElementById('artistform').submit();
}
function title(name)
{
document.getElementById('titleform_name').value = name;
document.getElementById('titleform').submit();
}
</script>
<form id="artistform" action="?link=list" method="post">
<input id="artistform_name" type="hidden" name="interpret">
<input type="hidden" name="details" value="1">
</form>
<form id="titleform" action="?link=list" method="post">
<input id="titleform_name" type="hidden" name="title">
<input type="hidden" name="details" value="1">
</form>

<style type="text/css">
<!--
.style_pm {color: #990000}
.style4 {font-size: 12px}
-->
</style>


<script>
  var _paq = window._paq = window._paq || [];
  _paq.push(['setUserId', 'FragDenWayne']);
  _paq.push(['trackPageView']);
  _paq.push(['enableLinkTracking']);
  _paq.push(['setRequestMethod', 'GET']);
  (function() {
    _paq.push(['setTrackerUrl', '/stats/']);
    _paq.push(['setSiteId', 'yEplKJvn3znLGB5']);
    var d=document, g=d.createElement('script'), s=d.getElementsByTagName('script')[0];
    g.async=true; g.src='/stats/'; s.parentNode.insertBefore(g,s);
  })();
</script>
"""