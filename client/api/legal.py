import datetime
import secrets
import string

from loguru import logger
from starlette import status

from client.api.settings import ApiClientSettings
from client.api_client import APIClient

# Constants for random legal tag name generation
RANDOM_NUMBER_MIN = 11111
RANDOM_NUMBER_RANGE = 88889


class APILegal(APIClient):
    """API storage service methods."""

    def __init__(self, data_partition: str, token: str) -> None:
        super().__init__(ApiClientSettings().service_host_legal, "", "", data_partition, token)

    def create_tag(self, **kwargs) -> None:
        """Method to create a legal tag."""
        current_date = datetime.date.today()

        # Use the secrets module to generate a cryptographically secure random number.
        random_number = secrets.randbelow(RANDOM_NUMBER_RANGE) + RANDOM_NUMBER_MIN

        # Generate a random string using string.ascii_uppercase and string.digits.
        random_string = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(5))

        body = {
            "name": f"RAFS-Legal-Tag-{random_number}-{random_string}",
            "description": "Legal Tag added for RAFS DDMS",
            "properties": {
                "contractId": "123456",
                "countryOfOrigin": [
                    "US",
                    "CA",
                ],
                "dataType": "Public Domain Data",
                "exportClassification": "EAR99",
                "originator": "Autotest",
                "personalData": "No Personal Data",
                "securityClassification": "Private",
                "expirationDate": current_date.replace(year=current_date.year + 2).isoformat(),
            },
        }
        logger.info("Creating random Legal Tag")
        response = self.post(path="/legaltags", json=body, allowed_codes=[status.HTTP_201_CREATED], **kwargs).json()
        return response["name"]

    def delete_tag(self, legal_tag: str, **kwargs) -> None:
        """Method to delete a legal tag."""
        logger.info(f"Deleting the Legal Tag with ID {legal_tag}")
        self.delete(path=f"/legaltags/{legal_tag}", allowed_codes=[status.HTTP_204_NO_CONTENT], **kwargs)
