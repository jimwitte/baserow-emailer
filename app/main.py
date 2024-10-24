import os
import logging
from dotenv import load_dotenv
from auth import authenticate
from emailer import get_active_configurations, process_emailer_config
from baserowapi import Baserow

def main():
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Load environment variables from .env file
    load_dotenv()

    # Access environment variables
    client_id = os.getenv("CLIENT_ID")
    tenant_id = os.getenv("TENANT_ID")
    baserow_url = os.getenv("BASEROW_URL")
    baserow_api_token = os.getenv("BASEROW_API_TOKEN")
    config_table_id = os.getenv("CONFIG_TABLE_ID")
    error_table_id = os.getenv("ERROR_TABLE_ID")

    if not any([client_id, tenant_id, baserow_url, baserow_api_token, config_table_id, error_table_id]):
        logger.error("Missing environment variables. Please check the configuration.")
        raise ValueError("Missing environment variables")

    # Authenticate and get the M365 access token
    access_token = authenticate(client_id, tenant_id)

    # Create baserow client
    baserow = Baserow(baserow_url, baserow_api_token)

    # Get the configuration data from the Baserow table
    active_configurations = get_active_configurations(baserow, config_table_id)

    # Process each active configuration
    for configuration in active_configurations:
        try:
            # Process the emailer configuration
            process_emailer_config(baserow, configuration, access_token)
        except Exception as e:
            logger.exception("An error occurred while processing the emailer configuration.")

if __name__ == "__main__":
    main()
