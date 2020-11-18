import re
import sys
import shlex
from subprocess import CalledProcessError, run
from pathlib import Path

from dlalbum.apps.base import BaseApp
from dlalbum import config_exists, config

class DownloadApp(BaseApp):
    @staticmethod
    def add_sub_parser_arguments(sub_parser):
        dl_parser = sub_parser.add_parser(name='get')
        dl_parser.add_argument('artist', help='The artist who created the album to download')
        dl_parser.add_argument('album', help='The name of the album to download')
        dl_parser.add_argument('urls', nargs='+',
                               help='One or more URLs to download audio from')

    INVALID_FILENAME_CHARS = re.compile(r'[^\w\-_\. ]')

    def __init__(self):
        self.artist_folder = None
        self.album_folder = None

    def start_execution(self, arg_parser, **kwargs):
        if not config_exists():
            print('Create a config before continuing with:')
            print('dlalbum config create')
            return

        artist_name = kwargs.get('artist')
        album_name = kwargs.get('album')
        urls = kwargs.get('urls')

        try:
            print('Downloading "{0}" by {1}'.format(album_name, artist_name))
            album_dir = self.create_album_dir(artist_name, album_name)
            self.download_music(album_dir, urls)
        except CalledProcessError as exc:
            self.print_exc(exc)
            print('Aborting.')
            sys.exit(1)
        finally:
            self.cleanup()

    def get_extra_youtube_dl_args(self):
        extra_args = []
        if 'youtube-dl' in config and 'options' in config['youtube-dl']:
            arg_str = config['youtube-dl']['options'].as_str()
            print('Using extra post processing arguments for youtube-dl:', arg_str)
            extra_args = shlex.split(arg_str)
        return extra_args

    def download_music(self, dir_: Path, urls: list):
        ''' Downloads one or more songs using youtube-dl in a subprocess into the dir_. Adds any
        extra args to the youtube-dl call (before the URLs) that may be in
        :code:`config['youtube-dl']['options']`.

        Embedding youtube-dl is not well documented. Calling youtube-dl, a Python program, from
        within Python makes the most sense, but there is no easy way to map from the command line
        options users know to a python dict youtube-dl uses. Embedding youtube-dl only seems to make
        sense if the argument list is static.

        Args:
            dir_ (Path): The directory to download files into
            urls (list): A list of URLs to download music from.
        '''
        default_args = ['--extract-audio', '--output', "%(title)s.%(ext)s"]
        extra_args = self.get_extra_youtube_dl_args()
        command = ['youtube-dl', *default_args, *extra_args, *urls]
        print(' '.join(command))
        result = run(
            args=command,
            check=True,
            shell=False,
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr,
            cwd=str(dir_))
        result.check_returncode()

    def clean_path_name(self, name):
        return self.INVALID_FILENAME_CHARS.sub('_', name)

    def create_album_dir(self, artist: str, album: str) -> Path:
        ''' Create the artist and album folders for the music to be moved into. If the album folder
        already exists and is not empty, an exception is raised as this may indicate that the album
        has already been downloaded.

        The directory structure is created under the current directory in this manner:

        .. code-block::

            . (current directory)
                |_ Artist
                    |_ Album

        Args:
            artist (str): The name of the artist whose music is being downloaded
            album (str): The name of album by the artist

        Returns:
            (Path): A path to the album folder
        '''
        root = Path('.')
        artist_folder = root / self.clean_path_name(artist)
        if not artist_folder.exists():
            artist_folder.mkdir()
        album_folder = artist_folder / self.clean_path_name(album)
        if album_folder.exists() and list(album_folder.glob('*')):
            raise FileExistsError('The album folder already exists and is not empty')
        if not album_folder.exists():
            album_folder.mkdir()
        return album_folder

    def cleanup(self):
        pass
