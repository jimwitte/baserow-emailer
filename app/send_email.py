import requests
import logging


def send_email(access_token, subject, recipients, body, from_email=None, cc=None):
    """
    Send an email using Microsoft Graph API.

    :param access_token: The access token obtained from Azure AD authentication.
    :type access_token: str
    :param subject: The subject of the email.
    :type subject: str
    :param recipients: A list of recipient email addresses.
    :type recipients: list of str
    :param cc: A list of CC email addresses. Defaults to None.
    :type cc: list of str, optional
    :param body: The body content of the email.
    :type body: str
    :param from_email: The email address of the shared mailbox to send the email from. Defaults to None.
    :type from_email: str, optional
    :raises Exception: If the email fails to send.
    """
    logger = logging.getLogger(__name__)

    # Set up the headers for the API call
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    # Prepare the recipient list
    to_recipients = [{"emailAddress": {"address": email}} for email in recipients]

    # Prepare the CC recipient list (if any)
    cc_recipients = [{"emailAddress": {"address": email}} for email in cc] if cc else []

    # Prepare the email message data
    message = {
        "subject": subject,
        "body": {"contentType": "Text", "content": body},
        "toRecipients": to_recipients,
    }

    # Add CC recipients to the message if provided
    if cc_recipients:
        message["ccRecipients"] = cc_recipients

    if from_email:
        # Include the 'from' field in the message
        message["from"] = {"emailAddress": {"address": from_email}}
        # Use the shared mailbox email in the API endpoint
        endpoint = f"https://graph.microsoft.com/v1.0/users/{from_email}/sendMail"
    else:
        # Use the '/me/sendMail' endpoint
        endpoint = "https://graph.microsoft.com/v1.0/me/sendMail"

    # Prepare the email data payload
    email_data = {"message": message, "saveToSentItems": "true"}

    # Log the email attempt
    recipient_list = ", ".join(recipients)
    cc_list = ", ".join(cc) if cc else "None"
    sender = from_email if from_email else "your account"
    logger.info(
        f"Attempting to send email from {sender} to {recipient_list} with CC: {cc_list} and subject: {subject[:50]}"
    )

    # Send the email
    try:
        response = requests.post(endpoint, headers=headers, json=email_data)

        if response.status_code == 202:
            logger.info("Email sent successfully.")
        else:
            logger.error(f"Failed to send email: {response.status_code}")
            logger.error(f"Response: {response.text}")
            response.raise_for_status()

    except requests.exceptions.RequestException as e:
        logger.exception("An error occurred while sending the email.")
        raise Exception("Failed to send email.") from e
