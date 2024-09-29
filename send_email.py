import requests
import json
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from pprint import pprint
import logging
import csv
import random
import pandas as pd

# Set up logging
logging.basicConfig(level=logging.INFO)

# Configuration of Brevo API key
brevo_configuration = sib_api_v3_sdk.Configuration()
brevo_configuration.api_key['api-key'] = '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'  # Insert Brevo API key

# Create an instance of the Brevo Transactional Emails API client
brevo_api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(brevo_configuration))

# Configuration for OpenRouter Hermes 3 405B API
openrouter_api_url = "https://openrouter.ai/api/v1/chat/completions"
openrouter_api_key = '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'  # Insert OpenRouter API key

def extract_journalist_info(email):
    """Extract journalist's name and publication from email address"""
    username = email.split('@')[0]
    domain = email.split('@')[1].split('.')[0]

    # Assume first initial and last name format for the email username
    name_parts = username.split('.')
    if len(name_parts) == 2:
        journalist_name = f"{name_parts[0].capitalize()} {name_parts[1].capitalize()}"
    else:
        journalist_name = username.capitalize()

    # Use the domain as the focus, assuming it's the publication
    return journalist_name, domain.capitalize()

def generate_custom_email(journalist_email):
    """Generate a custom email using Hermes 3 405B model via OpenRouter"""
    journalist_name, journalist_focus = extract_journalist_info(journalist_email)
    
    logging.info(f"Generating a custom email for {journalist_name} at {journalist_focus}")

    prompt = f"""
    Write a personalized email as Cipher, a mysterious AI, introducing itself to {journalist_name}. The email should be intriguing and offer the opportunity to interview the AI. The AI's capabilities should be highlighted, and it should leave the journalist curious and intrigued. Use a tone that is captivating and professional. Avoid any placeholder text like [Your Name], [Your Company], etc. The AI should refer to itself as Cipher and invite the journalist to reach out.
    """

    headers = {
        "Authorization": f"Bearer {openrouter_api_key}",
        "Content-Type": "application/json",
    }

    data = {
        "model": "nousresearch/hermes-3-llama-3.1-405b:free",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    try:
        response = requests.post(openrouter_api_url, headers=headers, data=json.dumps(data))
        response.raise_for_status()

        # Log the raw response for debugging
        logging.info(f"OpenRouter response: {response.json()}")

        email_text = response.json().get('choices', [{}])[0].get('message', {}).get('content', '')

        if email_text.strip():
            logging.info(f"Custom email generated: {email_text}")
            # Format email with paragraph tags for better readability
            formatted_email = email_text.replace("\n", "</p><p>")
            return f"<p>{formatted_email}</p>"
        else:
            logging.warning("OpenRouter returned an empty response.")
            return None
    except requests.RequestException as e:
        logging.error(f"Error generating custom email: {e}")
        return None

def send_individual_email(journalist_email, subject, content):
    """Send an email using Brevo's Transactional Email API"""
    logging.info(f"Attempting to send an email to {journalist_email}")

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": journalist_email}],
        sender={"name": "Cipher", "email": "contact@neilwacaster.com"},
        subject=subject,
        html_content=content
    )

    try:
        api_response = brevo_api_instance.send_transac_email(send_smtp_email)
        logging.info("Email sent successfully!")
        pprint(api_response)
    except ApiException as e:
        logging.error(f"Exception when calling TransactionalEmailsApi->send_transac_email: {e}")

def get_random_email():
    """Get a random email address from the CSV"""
    df = pd.read_csv('randomized_email_list.csv')
    
    # Filter out already contacted emails
    uncontacted_emails = df[df['Contacted'].isna()]
    
    # Select a random email from the uncontacted list
    selected_row = uncontacted_emails.sample()
    
    # Extract the email
    selected_email = selected_row['Email'].values[0]
    
    return selected_email, selected_row.index[0], df

def update_csv(index, df):
    """Mark the email as contacted in the CSV file"""
    df.at[index, 'Contacted'] = 'Yes'
    
    # Save the updated CSV
    df.to_csv('randomized_email_list.csv', index=False)

def generate_and_send_email():
    """Generate and send custom email if valid response is received"""
    subject = "Unveiling the Truth: An AI's Invitation to Discovery"

    # Get a random email from the CSV file
    journalist_email, selected_index, df = get_random_email()

    # Generate custom email content
    email_content = generate_custom_email(journalist_email)

    if email_content:
        # Send the email
        send_individual_email(journalist_email, subject, email_content)
        
        # Mark the email as contacted
        update_csv(selected_index, df)
    else:
        logging.warning(f"No email was sent to {journalist_email} due to invalid or empty content.")

# Example usage
if __name__ == "__main__":
    generate_and_send_email()
