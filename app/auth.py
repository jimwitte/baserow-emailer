import msal
import os
import logging


# def authenticate(client_id, tenant_id):
#     """
#     Authenticate with Azure AD and return an access token.

#     Parameters:
#     - client_id: The application (client) ID from Azure AD.
#     - tenant_id: The directory (tenant) ID from Azure AD.

#     Returns:
#     - access_token: The access token for Microsoft Graph API.
#     """

#     logger = logging.getLogger(__name__)

#     # Initialize token cache
#     cache = msal.SerializableTokenCache()
#     token_cache_file = "token_cache.bin"

#     if os.path.exists(token_cache_file):
#         logger.debug("Loading token cache from file.")
#         with open(token_cache_file, "r") as f:
#             cache.deserialize(f.read())
#     else:
#         logger.debug("No existing token cache found.")

#     # Create the PublicClientApplication
#     app = msal.PublicClientApplication(
#         client_id=client_id,
#         authority=f"https://login.microsoftonline.com/{tenant_id}",
#         token_cache=cache,
#     )

#     scopes = ["Mail.Send", "Mail.ReadWrite"]

#     # Attempt silent authentication
#     accounts = app.get_accounts()
#     if accounts:
#         logger.debug(
#             f"Found accounts in token cache: {[account['username'] for account in accounts]}"
#         )
#         result = app.acquire_token_silent(scopes, account=accounts[0])
#     else:
#         logger.debug("No accounts found in token cache.")
#         result = None

#     if not result:
#         logger.info(
#             "Silent authentication failed, attempting interactive authentication."
#         )
#         # Interactive authentication via Device Code Flow
#         flow = app.initiate_device_flow(scopes=scopes)
#         if "user_code" not in flow:
#             logger.error("Failed to create device flow.")
#             raise ValueError("Failed to create device flow")

#         logger.info(flow["message"])  # Display authentication instructions to the user

#         # Wait for user to complete authentication
#         result = app.acquire_token_by_device_flow(flow)
#         if "access_token" in result:
#             logger.info("Authentication successful.")
#         else:
#             error = result.get("error")
#             error_description = result.get("error_description")
#             logger.error(f"Authentication failed: {error} - {error_description}")
#             raise Exception("Authentication failed. Could not obtain access token.")

#         # Save the token cache
#         with open(token_cache_file, "w") as f:
#             f.write(cache.serialize())
#             logger.debug("Token cache saved to file.")
#     else:
#         logger.info("Token acquired silently from cache.")

#     access_token = result["access_token"]
#     return access_token


def authenticate(client_id, tenant_id):
    """
    Authenticate with Azure AD and return an access token.
    """
    logger = logging.getLogger(__name__)

    # Initialize token cache
    cache = msal.SerializableTokenCache()
    token_cache_file = "token_cache.bin"

    # Load token cache from file
    if os.path.exists(token_cache_file):
        logger.debug("Loading token cache from file.")
        try:
            with open(token_cache_file, "r") as f:
                cache.deserialize(f.read())
        except Exception as e:
            logger.error(f"Failed to load token cache: {e}")
    else:
        logger.debug("No existing token cache found.")

    # Create the PublicClientApplication
    app = msal.PublicClientApplication(
        client_id=client_id,
        authority=f"https://login.microsoftonline.com/{tenant_id}",
        token_cache=cache,
    )

    scopes = ["Mail.Send", "Mail.ReadWrite"]

    # Attempt silent authentication
    accounts = app.get_accounts()
    if accounts:
        logger.debug(
            f"Found accounts in token cache: {[account['username'] for account in accounts]}"
        )
        result = app.acquire_token_silent(scopes, account=accounts[0])
        if result:
            logger.info(
                f"Token expires in {result.get('expires_in', 'unknown')} seconds."
            )
        else:
            logger.error("Silent authentication failed.")
    else:
        logger.debug("No accounts found in token cache.")
        result = None

    # If silent auth fails, perform interactive auth
    if not result:
        logger.info(
            "Silent authentication failed, attempting interactive authentication."
        )
        flow = app.initiate_device_flow(scopes=scopes)
        if "user_code" not in flow:
            logger.error("Failed to create device flow.")
            raise ValueError("Failed to create device flow")

        logger.info(flow["message"])  # Display authentication instructions to the user

        # Wait for user to complete authentication
        result = app.acquire_token_by_device_flow(flow)
        if "access_token" in result:
            logger.info("Authentication successful.")
        else:
            error = result.get("error")
            error_description = result.get("error_description")
            logger.error(f"Authentication failed: {error} - {error_description}")
            raise Exception("Authentication failed. Could not obtain access token.")

        # Save the token cache
        try:
            with open(token_cache_file, "w") as f:
                f.write(cache.serialize())
                logger.debug("Token cache saved to file.")
        except Exception as e:
            logger.error(f"Failed to save token cache: {e}")

    access_token = result["access_token"]
    return access_token
