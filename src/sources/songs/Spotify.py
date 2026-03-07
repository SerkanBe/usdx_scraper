import os

import spotipy
from spotipy import SpotifyClientCredentials

from .SongsSourceBase import SongsSourceBase
from ...ColorPrint import ColorPrint
from ...EventManager import event_manager
from ...dataObjects.Song import Song


class Spotify(SongsSourceBase):

    spotify_client_id = ""
    spotify_secret = ""
    spotify_playlist_ids = []

    def __init__(self):
        event_manager.register('post_parser_init', self.event_post_parser_init)
        event_manager.register("parser_parse_args", self.event_parser_parse_args)

        self.spotify_client_id = os.getenv("SONG_SOURCES__SPOTIFY__CLIENT_ID") or self.spotify_client_id
        self.spotify_secret = os.getenv("SONG_SOURCES__SPOTIFY__CLIENT_SECRET") or self.spotify_secret
        self.spotify_playlist_ids = os.getenv("SONG_SOURCES__SPOTIFY__PLAYLIST_ID").split(",") or self.spotify_playlist_ids

    @staticmethod
    def event_post_parser_init(parser):
        parser.add_argument('-s', '--spotify', action="extend", nargs="+", default=[],
                            help="The URL/URI or ID of a Spotify playlist to search for songs, requires client_id and client_secret")
        parser.add_argument("-sid", "--spotifyClientId", action="store", help="The Client ID to be used for accessing Spotifies Web API")
        parser.add_argument("-ssc", "--spotifyClientSecret", action="store", help="The Client Secret to be used for accessing Spotifies Web API")

    def event_parser_parse_args(self, args):
        self.spotify_client_id = args.spotifyClientId or self.spotify_client_id
        self.spotify_secret = args.spotifyClientSecret or self.spotify_secret
        self.spotify_playlist_ids = args.spotify or self.spotify_playlist_ids

    def get_song_list(self) -> list[str]:
        if not (self.spotify_client_id and self.spotify_secret):
            return [] # No spotify credentials given
        elif not self.spotify_client_id:
            ColorPrint.print(ColorPrint.FAIL, "No Spotify Client ID given. Skipping...")
            return [] # We've got a secret, but no client id. Can't do anything.
        elif not self.spotify_secret:
            ColorPrint.print(ColorPrint.FAIL, "No Spotify Client Secret given. Skipping...")
            return [] # We've got a client id, but no secret. Can't do anything.
        elif not self.spotify_playlist_ids:
            ColorPrint.print(ColorPrint.FAIL, "No Spotify Playlist ID given. Skipping...")
            return [] # We've got a client id and secret, but no playlist id. Can't do anything.

        song_list = []
        for playlist_id in self.spotify_playlist_ids:
            playlist_name, playlist_tracks = self.get_playlist(playlist_id)
            for track in playlist_tracks:
                track = track["track"]
                artists = [artist["name"] for artist in track["artists"]]
                song = track["name"]
                song_list.append(Song(artists=artists, title=song, _source=f"Spotify:{playlist_name}"))

            ColorPrint.print(ColorPrint.OKGREEN, f"Spotify: Loaded {len(playlist_tracks)} Songs from Playlist '{playlist_name}'")

        return song_list


    def get_playlist(self, playlist_id):
        auth_manager = SpotifyClientCredentials(self.spotify_client_id, self.spotify_secret)
        spotify_client = spotipy.Spotify(auth_manager=auth_manager)
        playlist_identifier = playlist_id

        # Load the songs in the playlist.
        tracks = []
        offset = 0
        limit = 100

        while True:
            playlist_tracks = spotify_client.playlist_items(
                playlist_id=playlist_identifier,
                fields="items(track(artists(name), name, album(name, release_date, release_date_precision))",
                offset=offset,
                limit=limit
            )
            items = playlist_tracks["items"] or []

            if not items:
                break

            tracks.extend(items)
            offset += limit

        # Get the playlist name, just to show the user what playlist we're working with.
        playlist = spotify_client.playlist(
            playlist_id=playlist_identifier,
            fields="name",
        )

        return playlist['name'], tracks