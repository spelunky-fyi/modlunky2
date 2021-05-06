import logging
from builtins import staticmethod
from urllib.parse import urljoin

import requests
from requests import HTTPError

logger = logging.getLogger("modlunky2")


class SpelunkyFYIClient:
    def __init__(self, api_root, api_token):
        self.api_root = api_root
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Token {api_token}",
            }
        )

    def url(self, url):
        return urljoin(self.api_root, url)

    def get(self, url, *args, **kwargs):
        return self.session.get(self.url(url), *args, **kwargs)

    def get_mod(self, slug):
        response = self.get(f"api/mods/{slug}/")

        if response.status_code == 401:
            logger.critical(
                "Request was unauthorized. Make sure you have a valid API token."
            )
            return

        if response.status_code == 404:
            logger.critical("No mod found with install code: %s", slug)
            return

        try:
            response.raise_for_status()
        except HTTPError:
            logger.critical("Failed to download mod. Try again later.")
            return

        return response.json()

    @staticmethod
    def get_mod_file_from_details(details, mod_file_id=None):
        if not details["mod_files"]:
            logger.critical("Mod `%s` has no files to download.", details["slug"])
            return

        mod_files = details["mod_files"]
        if mod_file_id is None:
            return mod_files[0]

        for mod_file in mod_files:
            if mod_file["id"] == mod_file_id:
                return mod_file

        return None
