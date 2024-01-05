import logging
import requests
import os
import yaml

TMDB_HEADERS = {'Content-Type': 'application/json'}
DEFAULT_PROVIDERS_FILENAME = 'providers.txt'

TMDB_REGIONS_ENDPOINT = "https://api.themoviedb.org/3/watch/providers/regions"
TMDB_PROVIDERS_ENDPOINT = "https://api.themoviedb.org/3/watch/providers/movie"


def load_config() -> dict[str, str]:
    """
    Loads the configuration from the 'config.yaml' file.

    Returns:
        dict: The configuration settings.
    """
    logging.info('Loading Config and setting the list of required Providers')
    return yaml.safe_load(open("config.yaml"))


def remove_existing_file(file_path: str) -> None:
    """
    Removes an existing file if it exists.

    Args:
        file_path (str): The path to the file to be removed.
    """
    if os.path.exists(file_path):
        logging.info(f'Removing existing {file_path}...')
        os.remove(file_path)


def fetch_data(api_endpoint: str, api_key: str) -> list[dict]:
    """
    Fetches data from a specified API endpoint using the provided API key.

    Args:
        api_endpoint (str): The API endpoint URL.
        api_key (str): The API key for authentication.

    Returns:
        list: The fetched data.

    Raises:
        requests.exceptions.RequestException: If the request to the API endpoint fails.
    """
    try:
        response = requests.get(f"{api_endpoint}?api_key={api_key}", headers=TMDB_HEADERS)
        response.raise_for_status()

        return response.json().get("results", [])
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch data from {api_endpoint}: {str(e)}")
        raise


def write_to_file(file_path: str, regions: list[dict], providers: list[str]) -> None:
    """
    Writes data to a file.

    Args:
        file_path (str): The path to the file.
        regions (list): The list of regions to be added.
        providers (list[str]): The list of providers to be added to the file.
    """
    with open(file_path, "a") as file:
        file.write("Regions\n-------\n")
        for r in regions:
            file.write(str(r["iso_3166_1"]) + "\t" + str(r["english_name"]) + "\n")
        file.write("\n\nProviders\n---------\n")

        for p in providers:
            file.write(str(p) + "\n")


def main() -> None:
    logging.basicConfig(level=logging.INFO, filename='providers-load.log', filemode='w',
                        format='%(asctime)s :: %(levelname)s :: %(message)s')

    config = load_config()
    api_key = config["tmdbApiKey"]

    remove_existing_file(DEFAULT_PROVIDERS_FILENAME)

    regions = fetch_data(TMDB_REGIONS_ENDPOINT, api_key)
    providers = fetch_data(TMDB_PROVIDERS_ENDPOINT, api_key)

    all_providers = sorted(set(p.get("provider_name", "") for p in providers))

    write_to_file(DEFAULT_PROVIDERS_FILENAME, regions, all_providers)


if __name__ == "__main__":
    main()
