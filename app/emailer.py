import logging
from baserowapi import Filter
import requests
from jinja2 import Template
from jinja2 import Environment, TemplateError, TemplateSyntaxError
from send_email import send_email


def get_active_configurations(baserow, config_table_id):
    """
    Retrieve active email configurations from the specified Baserow table.

    This function queries the Baserow table for rows where the "Active" field is set to `true`,
    indicating active configurations for email sending.

    Parameters
    ----------
    baserow : Baserow
        The Baserow client instance used to interact with the Baserow API.
    config_table_id : int
        The ID of the Baserow table containing the email configurations.

    Returns
    -------
    list
        A list of dictionaries representing the active configurations.
        Returns an empty list if no active configurations are found.

    Logs
    ----
    Logs errors and information about the process using the configured logger.
    """
    logger = logging.getLogger(__name__)

    try:
        # Access the configuration table using the provided table ID
        logger.info(f"Fetching configurations from table ID {config_table_id}.")
        configuration_table = baserow.get_table(config_table_id)

        # Create filter to get only active configurations
        active_filter = Filter("Active", "true", "boolean")

        # Retrieve the rows that are marked as active
        active_configuration_rows = configuration_table.get_rows(filters=[active_filter])

        if not active_configuration_rows:
            logger.warning(
                f"No active configurations found in table ID {config_table_id}. Returning an empty list."
            )
            return []

        logger.info(
            f"Found {len(active_configuration_rows)} active configurations in table ID {config_table_id}."
        )

        # Convert the rows to a list of dictionaries with error handling for empty lists
        active_configurations = []

        for row in active_configuration_rows:
            row_dict = row.to_dict()
            new_row = {}
            for key, value in row_dict.items():
                if isinstance(value, list):
                    if value:
                        # The list is not empty; take the first element
                        new_row[key] = value[0]
                    else:
                        # The list is empty; handle the error
                        raise ValueError(f"Expected a non-empty list for key '{key}', but got an empty list.")
                else:
                    new_row[key] = value
            active_configurations.append(new_row)

        return active_configurations

    except Exception as e:
        logger.error(f"An error occurred while fetching configurations: {e}")
        raise


def process_emailer_config(baserow, configuration, access_token):
    """
    Process the emailer configuration, send emails, and update the status of rows in the source table.

    This function processes the provided emailer configuration, fetches rows from the source table
    that have an email trigger field set to "Queued" or blank (if configured), sends emails, and
    updates the trigger field to "Sent".

    Parameters
    ----------
    baserow : object
        The Baserow client instance for interacting with the API.
    configuration : dict
        The configuration settings for the emailer, including table IDs, email template, and trigger settings.
    access_token : str
        The access token used for authenticating email sending requests.

    Raises
    ------
    Exception
        If there is an issue sending the email or updating the row in Baserow.
    """
    logger = logging.getLogger(__name__)

    try:
        # Fetch configuration settings
        source_table_id = configuration["Source Table ID"]
        trigger_field = configuration["Email Trigger Field"]
        trigger_on_blank = bool(configuration["Trigger On Blank"])
        recipient_field = configuration["Email Recipient Field"]
        cc_recipients = comma_delimited_to_list(configuration["CC Recipients"])

        source_table = baserow.get_table(source_table_id)

        # Fields to include in the query
        include_fields = [
            trigger_field,
            recipient_field,
            *comma_delimited_to_list(configuration["Message Template Fields"]),
        ]

        source_table_fields = source_table.field_names

        # Validate that the required fields exist in the source table
        for field in include_fields:
            if field not in source_table_fields:
                logger.error(
                    f"Field '{field}' not found in source table (ID: {source_table_id})."
                )
                return

        # Validate the trigger field type
        trigger_field_type = source_table.fields[trigger_field].TYPE
        if trigger_field_type != "single_select":
            logger.error(
                f"Trigger field '{trigger_field}' must be of type 'single_select'."
            )
            return

        # Get the option ID for "Queued" status
        queued_option_id = get_option_id(
            source_table.fields[trigger_field].options_details, "Queued"
        )
        if not queued_option_id:
            logger.error(
                f"Queued option not found in field '{trigger_field}' of source table (ID: {source_table_id})."
            )
            return

        # Get the option ID for "In Progress" status
        inprogress_option_id = get_option_id(
            source_table.fields[trigger_field].options_details, "In Progress"
        )
        if not inprogress_option_id:
            logger.error(
                f"In Progress option not found in field '{trigger_field}' of source table (ID: {source_table_id})."
            )
            return

        # Get the option ID for "Sent" status
        sent_option_id = get_option_id(
            source_table.fields[trigger_field].options_details, "Sent"
        )
        if not sent_option_id:
            logger.error(
                f"Sent option not found in field '{trigger_field}' of source table (ID: {source_table_id})."
            )
            return

        # Create filters for queued and blank rows
        queued_rows_filter = Filter(
            trigger_field, queued_option_id, "single_select_equal"
        )
        blank_rows_filter = Filter(trigger_field, "", "empty")

        # Apply filters to get rows that are either queued or blank, depending on the config
        filter_list = [queued_rows_filter]
        if trigger_on_blank:
            filter_list.append(blank_rows_filter)

        # Fetch the rows from the source table
        queued_rows = source_table.get_rows(
            include=include_fields, filters=filter_list, filter_type="OR"
        )

        logger.info(f"Found {len(queued_rows)} queued rows to process.")

        # Validate and fetch the email template URL
        email_template_url = configuration["Message Template"].get("url", None)
        if not email_template_url:
            logger.error("Email template URL is missing in the configuration.")
            return

        # Process each queued row
        for row in queued_rows:

            # Update the trigger field to "In Progress"
            try:
                row.update({trigger_field: inprogress_option_id})
                logger.debug(f"Updated row ID {row.id} to 'In Progress' status.")
            except Exception as e:
                logger.error(f"Failed to update row ID {row.id}: {e}")
                continue

            # Create the email message
            try:
                email_message = create_email_message(row.to_dict(), email_template_url)
            except Exception as e:
                logger.error(f"Failed to create email message for row ID {row.id}: {e}")
                continue

            # Define email parameters
            subject = configuration.get("Subject", "No Subject")
            recipients = comma_delimited_to_list(row[recipient_field])
            if not recipients:
                logger.error(f"No recipients found for row ID {row.id}.")
                continue
            body = email_message

            # Send the email
            try:
                send_email(access_token=access_token, subject=subject, recipients=recipients, body=body, cc=cc_recipients)
                logger.info(f"Email sent to {recipients} for row ID {row.id}.")
            except Exception as e:
                logger.error(f"Failed to send email for row ID {row.id}: {e}")
                continue

            # Update the trigger field to "Sent"
            try:
                row.update({trigger_field: sent_option_id})
                logger.debug(f"Updated row ID {row.id} to 'Sent' status.")
            except Exception as e:
                logger.error(f"Failed to update row ID {row.id}: {e}")
                continue

    except Exception as e:
        logger.error(
            f"An error occurred while processing the emailer configuration: {e}"
        )
        raise


def build_index(rows, index_field_name):
    """
    Builds an index (dictionary) from a list of Baserow row objects using the specified field as the key.

    Args:
        rows (list): A list of Baserow row objects (dictionaries).
        index_field_name (str): The field name to use as the index key.

    Returns:
        dict: A dictionary where keys are the values of the specified field, and values are the row objects.

    Raises:
        KeyError: If a row does not contain the specified index field.
    """

    logger = logging.getLogger(__name__)

    index = {}
    for row in rows:
        # Check if the index field exists in the row
        if index_field_name not in row:
            logger.error(f"Row {row.get('id', 'Unknown ID')} is missing the '{index_field_name}' field.")
            raise KeyError(f"The index field '{index_field_name}' is missing in a row.")

        index_value = row[index_field_name]

        # Handle None or empty index values
        if index_value is None or (isinstance(index_value, str) and index_value.strip() == ''):
            logger.error(f"Row {row.get('id', 'Unknown ID')} has an invalid index value: {index_value}")
            raise ValueError(f"Invalid index value '{index_value}' in row with ID {row.get('id', 'Unknown ID')}.")

        # Check for duplicate index values
        if index_value in index:
            # Log a warning for duplicate index values
            logger.warning(f"Duplicate index value '{index_value}' found in row with ID {row.get('id', 'Unknown ID')}.")

        index[index_value] = row

    # logger.info(f"Index built successfully with {len(index)} entries.")
    return index


def comma_delimited_to_list(input_string):
    """
    Utility function to convert a comma-delimited string into a list,
    trimming any whitespace from each item.

    If the input_string is None, an empty list is returned.

    Parameters:
    ----------
    input_string : str or None
        A comma-delimited string. If None, an empty list will be returned.

    Returns:
    -------
    list
        A list of strings with whitespace trimmed from each item.
        If input_string is None, an empty list is returned.
    """
    if input_string:
        return [item.strip() for item in input_string.split(",")]
    else:
        return []


def create_email_message(variables, template_url):
    """
    Generate an email message by rendering a Jinja2 template with the given variables.

    This function fetches a Jinja2 template from the specified URL and uses the
    provided dictionary of variables to render the final email message. Each key
    in the dictionary corresponds to a Jinja2 variable in the template, and each value
    is substituted in the template.

    Parameters
    ----------
    variables : dict
        A dictionary where keys are the names of Jinja2 variables to be substituted,
        and values are the values to replace them with in the email template. 
        Spaces in variable names will be replaced with underscores.
    template_url : str
        The URL pointing to the Jinja2 email template content. The content is expected
        to be in valid Jinja2 template format.

    Returns
    -------
    str
        The rendered email message as a string, with the variables substituted into the template.

    Raises
    ------
    requests.exceptions.RequestException
        If there is an error fetching the template from the URL.
    jinja2.exceptions.TemplateError
        If there is an error rendering the template with the provided variables.
    """
    logger = logging.getLogger(__name__)  # Set up logger

    try:
        # Fetch the template content from the URL
        logger.info(f"Fetching template from URL: {template_url}")
        response = requests.get(template_url)
        response.raise_for_status()  # Raises an HTTPError for bad responses
        template_content = response.text

        # Validate the Jinja2 template
        logger.info("Validating Jinja2 template.")
        valid_template = validate_jinja2_template(template_content)
        if not valid_template:
            logger.error("Invalid Jinja2 template.")
            raise ValueError("The Jinja2 template is not valid.")

        # Create a Jinja2 Template object from the fetched content
        logger.debug("Creating Jinja2 template object.")
        template = Template(template_content)

        # Replace spaces in variable names with underscores
        logger.debug("Replacing spaces in variable keys with underscores.")
        variables = {key.replace(" ", "_"): value for key, value in variables.items()}

        # Render the template with the provided variables
        logger.debug("Rendering the template with provided variables.")
        rendered_message = template.render(variables)

        logger.info("Email message successfully created.")
        return rendered_message

    except requests.exceptions.RequestException as e:
        # Log and handle network-related issues when fetching the template
        logger.error(f"Failed to fetch template from {template_url}: {e}")
        raise

    except TemplateError as e:
        # Log and handle any rendering issues with Jinja2
        logger.error(f"Error rendering the email template: {e}")
        raise

    except Exception as e:
        # Catch any other unexpected exceptions
        logger.error(f"An unexpected error occurred: {e}")
        raise


def validate_jinja2_template(template_content):
    """
    Validates a Jinja2 template to check for syntax errors.

    Parameters
    ----------
    template_content : str
        The Jinja2 template as a string.

    Returns
    -------
    bool
        Returns True if the template is valid.

    Raises
    ------
    TemplateSyntaxError
        If the template contains syntax errors.
    """
    # Set up logger for this module
    logger = logging.getLogger(__name__)

    try:
        # Create a Jinja2 environment
        env = Environment()

        # Compile the template to validate it (this will raise an error if invalid)
        env.parse(template_content)

        # If compilation succeeds, the template is valid
        return True

    except TemplateSyntaxError as e:
        # Log the specific syntax error
        logger.error(f"Template syntax error: {e}")
        raise

    except Exception as e:
        # Catch any other unexpected exceptions
        logger.error(f"An unexpected error occurred during template validation: {e}")
        raise


def get_option_id(options_details, option_value):
    """
    Retrieve the ID of a specific option from the options details of a single select field.

    Parameters
    ----------
    options_details : list
        A list of dictionaries, each representing an option with its details (including 'id' and 'value').
    option_value : str
        The value of the option for which to retrieve the corresponding ID.

    Returns
    -------
    str or None
        The ID of the option if found, otherwise None.

    Raises
    ------
    ValueError
        If the option value is not found in the options details.

    Example
    -------
    >>> options_details = [{'id': '1234', 'value': 'Queued'}, {'id': '5678', 'value': 'Sent'}]
    >>> get_option_id(options_details, 'Queued')
    '1234'
    """
    # Set up logger for this module
    logger = logging.getLogger(__name__)

    try:
        # Build an index where the 'value' is the key and the 'id' is part of the data
        options_index = {option["value"]: option for option in options_details}

        # Retrieve the desired option
        option_details = options_index.get(option_value, None)
        option_id = option_details.get("id", None) if option_details else None

        if not option_id:
            logger.error(
                f"The option '{option_value}' is not found in the provided options."
            )
            raise ValueError(
                f"The option '{option_value}' is not found in the provided options."
            )

        logger.debug(
            f"Successfully found option ID: {option_id} for value: {option_value}"
        )
        return option_id

    except Exception as e:
        logger.error(f"An error occurred while retrieving the option ID: {e}")
        raise
