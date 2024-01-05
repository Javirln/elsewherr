import requests
import re
import yaml
import logging

from typing import List, Dict, Tuple


def setup_logging() -> None:
    """Set up logging based on the debug flag."""
    logging.basicConfig(level=logging.INFO, filename='elsewherr.log', filemode='w',
                        format='%(asctime)s :: %(levelname)s :: %(message)s')


def load_config(file_path: str) -> Dict:
    """Load configuration from a YAML file."""
    try:
        with open(file_path, 'r') as config_file:
            return yaml.safe_load(config_file)
    except Exception as e:
        logging.error(f"Error loading config file: {str(e)}")
        raise


def create_provider_tags(config: Dict) -> None:
    """Create tags for required providers within Radarr."""
    radarr_headers = {'Content-Type': 'application/json', "X-Api-Key": config["radarrApiKey"]}

    for required_provider in config["requiredProviders"]:
        provider_tag = (config["tagPrefix"] + re.sub('[^A-Za-z0-9]+', '', required_provider)).lower()
        new_tag_json = {'label': provider_tag, 'id': 0}

        try:
            radarr_tags_post = requests.post(config["radarrUrl"] + '/api/v3/tag', json=new_tag_json,
                                             headers=radarr_headers)
            logging.info(f'radarrTagsPost Response: {radarr_tags_post}')
        except Exception as e:
            logging.error(f"Error creating tag for provider {required_provider}: {str(e)}")


def get_provider_tags(config: Dict, required_providers_lower: List) -> Tuple[List[Dict], List[Dict]]:
    """Get all tags and create lists of those to remove and add."""
    radarr_headers = {'Content-Type': 'application/json', "X-Api-Key": config["radarrApiKey"]}

    try:
        radarr_tags_get = requests.get(config["radarrUrl"] + '/api/v3/tag', headers=radarr_headers)
        logging.info(f'radarrTagsGet Response: {radarr_tags_get}')
        existing_tags = radarr_tags_get.json()
        logging.info(f'existingTags: {existing_tags}')

        provider_tags_to_remove = [existing_tag for existing_tag in existing_tags if
                                   config["tagPrefix"].lower() in existing_tag["label"]]
        provider_tags_to_add = [existing_tag for existing_tag in existing_tags if
                                str(existing_tag["label"]).replace(config["tagPrefix"].lower(),
                                                                   '') in required_providers_lower]

        return provider_tags_to_remove, provider_tags_to_add
    except Exception as e:
        logging.error(f"Error getting tags: {str(e)}")
        raise


def process_movies(movies: List[Dict], config: Dict, provider_tags_to_remove: List[Dict],
                   provider_tags_to_add: List[Dict]) -> None:
    """Process each movie in turn."""
    radarr_headers = {'Content-Type': 'application/json', "X-Api-Key": config["radarrApiKey"]}
    tmdb_headers = {'Content-Type': 'application/json'}

    for movie in movies:
        update = movie
        logging.info(
            "-------------------------------------------------------------------------------------------------")
        logging.info("Movie: " + movie["title"])
        logging.info("TMDB ID: " + str(movie["tmdbId"]))
        logging.info(f'Movie record from Radarr: {movie}')

        try:
            tmdb_providers = get_tmdb_providers(movie["tmdbId"], config["tmdbApiKey"], config["providerRegion"],
                                                tmdb_headers)
            providers = tmdb_providers["results"][config["providerRegion"]]["flatrate"]
            logging.info(f'Flat Rate Providers: {providers}')
        except KeyError:
            logging.info("No Flatrate Providers")
            continue
        except Exception as e:
            logging.error(f"Error getting providers for movie {movie['title']}: {str(e)}")
            continue

        # update_tags = remove_provider_tags(movie.get("tags", []), provider_tags_to_remove)

        for provider in providers:
            provider_name = provider["provider_name"]
            tag_to_add = (config["tagPrefix"] + re.sub('[^A-Za-z0-9]+', '', provider_name)).lower()

            for provider_tag_to_add in provider_tags_to_add:
                if tag_to_add in provider_tag_to_add["label"]:
                    logging.info("Adding tag " + tag_to_add)
                    # update_tags.append(provider_tag_to_add["id"])

        # update["tags"] = update_tags
        logging.info(f'Updated Movie record to send to Radarr: {update}')

        try:
            pass
            # radarr_update = requests.put(config["radarrUrl"] + '/api/v3/movie', json=update, headers=radarr_headers)
            # logging.info(radarr_update)
        except Exception as e:
            logging.error(f"Error updating movie {movie['title']} in Radarr: {str(e)}")


def get_tmdb_providers(tmdb_id: int, api_key: str, region: str, headers: Dict) -> Dict:
    """Get available providers for a movie from TMDB."""
    tmdb_response = requests.get(f'https://api.themoviedb.org/3/movie/{tmdb_id}/watch/providers?api_key={api_key}',
                                 headers=headers)
    logging.info(f'tmdbResponse Response: {tmdb_response}')
    return tmdb_response.json()


def remove_provider_tags(update_tags: List[int], provider_tags_to_remove: List[Dict]) -> List[int]:
    """Remove all provider tags from movie."""
    logging.info("Remove all provider tags from movie")
    for provider_id_to_remove in (provider_ids_to_remove["id"] for provider_ids_to_remove in provider_tags_to_remove):
        try:
            update_tags.remove(provider_id_to_remove)
            logging.info(f'Removing providerId: {provider_id_to_remove}')
        except ValueError:
            continue
    return update_tags


def get_movies_from_radarr(config: Dict) -> List[Dict]:
    """Get all Movies from Radarr."""
    radarr_headers = {'Content-Type': 'application/json', "X-Api-Key": config["radarrApiKey"]}
    radarr_url = f"{config['radarrUrl']}/api/v3/movie"

    logging.info(f'Getting all Movies from Radarr at {radarr_url}')

    try:
        radarr_response = requests.get(radarr_url, headers=radarr_headers)
        radarr_response.raise_for_status()  # Raise an exception for bad responses (4xx or 5xx)
        movies = radarr_response.json()
        logging.info(f'Number of Movies: {len(movies)}')
        return movies
    except requests.RequestException as e:
        logging.error(f"Error getting movies from Radarr: {str(e)}")
        return []


def main() -> None:
    """Main entry point of the script."""
    setup_logging()

    logging.info('Loading Config and setting the list of required Providers')

    try:
        config = load_config("config.yaml")
        required_providers_lower = [re.sub('[^A-Za-z0-9]+', '', x).lower() for x in config["requiredProviders"]]
        logging.info(f'requiredProvidersLower: {required_providers_lower}')

        create_provider_tags(config)

        provider_tags_to_remove, provider_tags_to_add = get_provider_tags(config, required_providers_lower)

        movies = get_movies_from_radarr(config)

        logging.info('Working on all movies in turn')
        process_movies(movies, config, provider_tags_to_remove, provider_tags_to_add)
    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")


if __name__ == "__main__":
    main()
