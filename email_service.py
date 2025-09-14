import os
import base64
from email import message_from_bytes
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['']

def authenticate_gmail():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)

def get_latest_unread_email(service):
    results = service.users().messages().list(
        userId='me',
        labelIds=['INBOX', 'UNREAD'],
        maxResults=1
    ).execute()

    messages = results.get('messages', [])
    if not messages:
        return None, None

    msg_id = messages[0]['id']
    msg = service.users().messages().get(userId='me', id=msg_id, format='full').execute()

    headers = msg['payload'].get('headers', [])
    sender_email = None
    for header in headers:
        if header['name'].lower() == 'from':
            sender_email = header['value']
            break

    payload = msg['payload']
    body = ""

    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                data = part['body']['data']
                body = base64.urlsafe_b64decode(data).decode()
                break
    else:
        data = payload['body']['data']
        body = base64.urlsafe_b64decode(data).decode()

    # Mark email as read after fetching
    service.users().messages().modify(
        userId='me',
        id=msg_id,
        body={'removeLabelIds': ['UNREAD']}
    ).execute()

    return body.strip(), sender_email

def poll_gmail():
    service = authenticate_gmail()
    email_body, sender_email = get_latest_unread_email(service)

    if email_body:
        print("\n New Unread Email Received:\n", email_body)
        print(" Sender:", sender_email)
        from planner_agent import process_email_with_planner
        process_email_with_planner(email_body=email_body, sender_email=sender_email)
    else:
        print("No unread email found.")

if __name__ == '__main__':

    poll_gmail()
