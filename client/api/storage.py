from loguru import logger
from requests import Response
from starlette import status

from client.api.settings import ApiClientSettings
from client.api_client import APIClient


class APIStorage(APIClient):
    """API storage service methods."""

    limit: int = 100

    def __init__(self, data_partition: str, token: str) -> None:
        super().__init__(ApiClientSettings().service_host_storage, "", "", data_partition, token)

    def create_or_update_records(self, records: list, **kwargs) -> Response:
        """Method to create records."""
        logger.info("Creating records in storage")
        return self.put(
            path="/records",
            json=records,
            allowed_codes=[status.HTTP_201_CREATED, status.HTTP_200_OK],
            **kwargs,
        )

    def purge_record(self, record_id: str, **kwargs) -> None:
        """Method to delete record completely from storage service."""
        logger.info(f"Deleting record from Storage service with ID {record_id}")
        self.delete(
            path=f"/records/{record_id}",
            allowed_codes=[status.HTTP_204_NO_CONTENT, status.HTTP_404_NOT_FOUND],
            **kwargs,
        )
