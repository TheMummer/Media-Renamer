# Media-Renamer
Media Enhancement and Directory Integration Assistant: MEDIA: 

This script is designed to automate the organizing and renaming of media files for a Plex Media Server. It works with both TV shows and movies. Here's a breakdown of what it does:

1. **Imports necessary modules**: The script imports various Python libraries that it needs to run, such as `os`, `re`, `json`, `shutil`, `subprocess`, `requests`, `logging`, `datetime`, `tqdm`, `tvdb_api`, and `omdb`.

2. **Sets up directories and logging**: It sets up base directories for Plex and a cache directory. It also sets up a logging system to track what the script does.

3. **Defines helper classes and functions**: These include a custom tqdm class for logging progress, functions for copying and moving files with progress tracking, a function to sanitize names by removing invalid characters, functions to create directories for shows and movies, and a function to check and install missing Python packages.

4. **Defines functions to get TV show and movie information**: These functions use the TVDB and OMDb APIs to get information about TV shows and movies. They also cache this information to speed up future requests.

5. **Defines functions to match and process TV show and movie names**: These functions use regular expressions to match the names of TV shows and movies in directory names and then process these matches to get the formatted names.

6. **Lists directories and finds the largest file**: The script lists all directories in a given root directory and finds the largest file in a directory.

7. **Saves TV show directories to a file**: It saves a list of TV show directories and their new names to a file.

8. **Moves and renames the largest file in a directory**: It moves the largest file from the source directory to the destination directory and renames it.

9. **Removes the source directory**: After moving and renaming the largest file, it removes the source directory.

10. **Main script execution**: In the main part of the script, it checks and installs the tqdm package if necessary, gets the TVDB and OMDb API keys from environment variables, lists all directories, saves TV show directories to a file, and then processes each directory. If the directory is a TV show, it moves and renames the largest file and then removes the directory. If the directory is a movie, it does the same.

In summary, this script is a comprehensive tool for organizing and renaming media files for a Plex Media Server, making it easier to manage large collections of TV shows and movies.
