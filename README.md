# Baserow Emailer Utility
Utility for sending email using Microsoft365. 
Requires a configuration database with the schema described below.


# Emailer Utility Configuration Database Schema

## 1. Templates Table
- **Template Name** (string)
  - Description: Name of the email template.
- **Subject** (string)
  - Description: Subject used for the email template.
- **From** (email)
  - Description: Email address to be used as the "from" address.
- **Message Template** (array of files)
  - Description: Template files used for message content.
- **Configurations** (link to Configurations table)
  - Description: Linked configurations from the Configurations table.
- **CC** (string)
  - Description: CC email addresses.

## 2. Source Tables Table
- **Source Table Name** (string)
  - Description: Name of the source table.
- **TableID** (number)
  - Description: ID of the source table.
- **Configurations** (link to Configurations table)
  - Description: Linked configurations using this table.
- **Message Template Fields** (multi-line text)
  - Description: Custom fields for the message template.

## 3. Configurations Table
- **Configuration Name** (string)
  - Description: Name of the configuration.
- **Source Table** (link to Source Tables table)
  - Description: Linked source table.
- **Active** (boolean)
  - Description: Indicates if the configuration is active.
- **Email Trigger Field** (string)
  - Description: Field that triggers the email.
- **Template** (link to Templates table)
  - Description: Linked email template.
- **Email Recipient Field** (string)
  - Description: Field that contains email addresses.
- **Trigger On Blank** (boolean)
  - Description: Trigger email when the value is blank.
