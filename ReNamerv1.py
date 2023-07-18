import os
import re
import json
import shutil
import subprocess
import requests
import logging
import datetime
from tqdm import tqdm
import tvdb_api
import omdb

# Set the base directories
PLEX_BASE_DIR = "M:\\PlexShares"
CACHE_DIR = "M:\\Plexshares\\MediaCache"

# Set up logging
timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
log_file = f'process_log_{timestamp}.log'
logging.basicConfig(filename=log_file, level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger().addHandler(logging.StreamHandler())  # Also log to console

class TqdmToLogger(tqdm):
    def __init__(self, iterable=None, desc=None, total=None, **kwargs):
        class DummyFile(object):
            def write(self, x): pass

        kwargs['file'] = DummyFile()
        super(TqdmToLogger, self).__init__(iterable, desc, total, **kwargs)

    def update_to(self, b=1, bsize=1, tsize=None):
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)

def copy_with_progress(src, dst):
    with open(src, 'rb') as fsrc, open(dst, 'wb') as fdst:
        pbar = TqdmToLogger(unit='B', unit_scale=True, miniters=1, desc=os.path.split(src)[1])
        shutil.copyfileobj(fsrc, fdst, callback=pbar.update_to)
        pbar.close()

def move_with_progress(src, dst):
    copy_with_progress(src, dst)
    os.remove(src)

def sanitize_name(name):
    return re.sub(r'[\\/:"*?<>|]', '', name)

def create_show_and_season_directories(show_name, season, year=None):
    sanitized_show_name = sanitize_name(show_name)
    if year:
        sanitized_show_name += f" ({year})"
    show_dir = os.path.join(PLEX_BASE_DIR, "Series", "Shows", sanitized_show_name)
    season_dir = os.path.join(show_dir, f'Season {int(season):02d}')

    os.makedirs(season_dir, exist_ok=True)
    return season_dir

def create_movie_directory(formatted_name, year=None):
    sanitized_name = sanitize_name(formatted_name)
    if year:
        sanitized_name += f" ({year})"
    movie_dir = os.path.join(PLEX_BASE_DIR, "Movies", sanitized_name)

    os.makedirs(movie_dir, exist_ok=True)
    return movie_dir

def check_and_install(package):
    try:
        __import__(package)
    except ImportError:
        print(f'{package} module not found.')
        choice = input(f'Do you want to install it? (y/n): ')
        if choice.lower() == 'y':
            subprocess.run(['pip', 'install', package])
        else:
            print(f'Please install {package} to use this script.')
            exit()

required_packages = ['pandas', 'numpy', 'tvdb_api', 'omdb', 'requests']
for package in required_packages:
    check_and_install(package)

def get_tv_show_info(api_key, show_name, season, episode):
    if not api_key:
        raise ValueError('TVDB API key is missing')

    cache_path = os.path.join(CACHE_DIR, f'tv_show_{sanitize_name(show_name)}.json')
    if os.path.exists(cache_path):
        with open(cache_path, 'r') as cache_file:
            cached_show_info = json.load(cache_file)
            try:
                episode_info = cached_show_info['seasons'][str(season)][str(episode)]
                return {
                    'name': cached_show_info['name'],
                    'first_aired': cached_show_info['first_aired'],
                    'episode_name': episode_info['episode_name']
                }
            except KeyError:
                logging.error(f"Failed to find episode information in cache for {show_name} S{season}E{episode}")
                # Continue below to fetch data from the API
                
    t = tvdb_api.Tvdb(apikey=api_key)
    try:
        search_result = t.search(show_name)
        if search_result:
            show = search_result[0]
            show_id = show['id']
            t_show = t[show_id]
            try:
                episode_info = t_show[int(season)][int(episode)]
                show_info = {
                    'name': show['seriesName'],
                    'first_aired': show['firstAired'],
                    'seasons': {
                        str(season): {
                            str(episode): {
                                'episode_name': episode_info['episodeName']
                            }
                        }
                    }
                }
                # Save to cache
                with open(cache_path, 'w') as cache_file:
                    json.dump(show_info, cache_file)
                    
                return {
                    'name': show_info['name'],
                    'first_aired': show_info['first_aired'],
                    'episode_name': show_info['seasons'][str(season)][str(episode)]['episode_name']
                }
            except KeyError:
                logging.error(f"Failed to find episode information for {show_name} S{season}E{episode}")
                return None
    except (tvdb_api.tvdb_shownotfound, tvdb_api.tvdb_seasonnotfound, tvdb_api.tvdb_episodenotfound) as e:
        logging.error(f"Failed to find show, season, or episode information for {show_name}: {e}")
        return None

def get_movie_info(api_key, movie_name):
    if not api_key:
        raise ValueError('OMDb API key is missing')

    cache_path = os.path.join(CACHE_DIR, f'movie_{sanitize_name(movie_name)}.json')
    if os.path.exists(cache_path):
        with open(cache_path, 'r') as cache_file:
            cached_movie_info = json.load(cache_file)
            return {
                'title': cached_movie_info["title"],
                'year': cached_movie_info["year"],
                'director': cached_movie_info["director"],
                'imdb_rating': cached_movie_info["imdb_rating"]
            }
            
    url = f"http://www.omdbapi.com/?apikey={api_key}&t={movie_name}"
    response = requests.get(url)
    if response.ok:
        data = response.json()
        if data['Response'] == 'True':
            movie_info = {
                'title': data["Title"],
                'year': data["Year"],
                'director': data["Director"],
                'imdb_rating': data["imdbRating"]
            }
            # Save to cache
            with open(cache_path, 'w') as cache_file:
                json.dump(movie_info, cache_file)
            return movie_info
            
    logging.error(f"Failed to find movie information for {movie_name}")
    return None

def match_tv_show(dir_name):
    tv_show_pattern = re.compile(r'^(.+?)(?:\.(\d{4}))?\.S(\d{2})E(\d{2})(?:\.(.*))?$', re.IGNORECASE)
    return tv_show_pattern.match(dir_name)

def match_movie(dir_name):
    movie_pattern = re.compile(r'^(.+)\.(\d{4})\.(.+)', re.IGNORECASE)
    return movie_pattern.match(dir_name)

def process_tv_show_match(match, tvdb_api_key):
    original_show_name, year, season, episode, additional_text = match.groups()
    original_show_name = original_show_name.replace('.', ' ')
    show_info = get_tv_show_info(tvdb_api_key, original_show_name, int(season), int(episode))
    if show_info:
        show_name = show_info['name']
        episode_name = show_info['episode_name']
        season_episode = f'S{season}E{episode}'
        formatted_name = f'{show_name} - {season_episode} - {episode_name}'
        logging.debug(f"Formatted name: {formatted_name}")
        return show_name, formatted_name, season, episode
    return None, None, None, None

def process_movie_match(match, omdb_api_key):
    original_movie_name = match.group(1).replace('.', ' ')
    year = match.group(2)
    movie_info = get_movie_info(omdb_api_key, original_movie_name)
    if movie_info:
        movie_name = movie_info['title']
        formatted_name = f'{movie_name} ({year})'
        return formatted_name
    logging.error(f"Failed to process movie match for {original_movie_name} ({year})")
    return None

def list_directories(root_dir, tvdb_api_key, omdb_api_key):
    directories = []
    dirs = next(os.walk(root_dir))[1]
    with open('error_log.txt', 'a') as error_log:
        for dir_name in tqdm(dirs, desc='Scanning directories'):  # Add progress bar
            try:
                tv_show_match = match_tv_show(dir_name)
                movie_match = match_movie(dir_name)
                if tv_show_match:
                    logging.info(f"Matched TV Show: {dir_name}")
                    formatted_name = process_tv_show_match(tv_show_match, tvdb_api_key)
                    if formatted_name:
                        show_name, season, episode = tv_show_match.groups()[:3]
                        formatted_name = f"{formatted_name} S{season}E{episode}"
                        directories.append(('tv_show', formatted_name, os.path.join(root_dir, dir_name)))
                elif movie_match:
                    logging.info(f"Matched Movie: {dir_name}")
                    formatted_name = process_movie_match(movie_match, omdb_api_key)
                    if formatted_name:
                        directories.append(('movie', formatted_name, os.path.join(root_dir, dir_name)))
            except Exception as e:
                # Write the name of the problematic directory and the error message to the log file
                error_log.write(f"Error processing directory {dir_name}: {str(e)}\n")
                # Continue with the next directory
                continue
    return directories

def find_largest_file(directory):
    max_size = -1
    largest_file = None
    file_extensions = ('.mkv', '.mp4', '.avi', '.mov', '.flv', '.wmv')

    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(file_extensions):
                file_path = os.path.join(root, file)
                file_size = os.path.getsize(file_path)

                if file_size > max_size:
                    max_size = file_size
                    largest_file = file

    return largest_file

def save_tv_show_directories_to_file(directories, output_file):
    with open(output_file, 'w') as file:
        file.write("New Name,Old Name\n")
        for dir_type, formatted_name, source_directory in directories:
            if dir_type == 'tv_show':
                file.write(f'{formatted_name},{os.path.basename(source_directory)}\n')

def move_and_rename_largest_file(source_directory, destination_directory, new_name):
    largest_file = find_largest_file(source_directory)
    if largest_file:
        file_extension = os.path.splitext(largest_file)[1]  # Extract file extension
        source_file_path = os.path.join(source_directory, largest_file)
        destination_file_path = os.path.join(destination_directory, f'{new_name}{file_extension}')
        logging.info(f"Moving file from {source_file_path} to {destination_file_path}")
        try:
            shutil.move(source_file_path, destination_file_path)
        except Exception as e:
            logging.error(f"Error moving and renaming file: {e}")

def remove_directory(directory):
    try:
        shutil.rmtree(directory)
    except OSError as e:
        logging.error(f"Error removing directory {directory}: {e}")

if __name__ == '__main__':
    check_and_install('tqdm')
    tvdb_api_key = os.getenv('TVDB_API_KEY')
    omdb_api_key = os.getenv('OMDB_API_KEY')
    root_directory = os.getcwd()
    output_file = 'tv_show_list.txt'

    directories = list_directories(root_directory, tvdb_api_key, omdb_api_key)
    save_tv_show_directories_to_file(directories, output_file)

    for dir_type, formatted_name, source_directory in directories:
        print(f"Processing: {dir_type}, {formatted_name}, {source_directory}")  # Debugging line
        if dir_type == 'tv_show':
            tv_show_match = match_tv_show(os.path.basename(source_directory))
            if tv_show_match:
                show_name, formatted_name, season, episode = process_tv_show_match(tv_show_match, tvdb_api_key)

                if show_name and formatted_name:
                    season_dir = create_show_and_season_directories(show_name, season)

                    new_file_name = formatted_name
                    print(f"Moving and renaming TV show: {source_directory} to {season_dir}")  # Debugging line
                    move_and_rename_largest_file(source_directory, season_dir, new_file_name)
                    remove_directory(source_directory)

        elif dir_type == 'movie':
            movie_match = match_movie(os.path.basename(source_directory))
            if movie_match:
                formatted_name = process_movie_match(movie_match, omdb_api_key)
                if formatted_name:
                    movie_dir = create_movie_directory(formatted_name)

                    new_file_name = formatted_name
                    print(f"Moving and renaming Movie: {source_directory} to {movie_dir}")  # Debugging line
                    move_and_rename_largest_file(source_directory, movie_dir, new_file_name)
                    remove_directory(source_directory)