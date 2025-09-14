from crewai import Agent, Task, Crew, LLM
from email.mime.text import MIMEText
import base64
from gmail_auth import authenticate_gmail

GEMINI_API_KEY = ""

customer_agent = Agent(
    role="Customer Support Agent",
    goal="Write professional customer emails about return requests and refund processing.",
    backstory="Friendly support agent explaining policy decisions and refund process.",
    llm=LLM(
        model="gemini/gemini-1.5-flash",
        api_key=GEMINI_API_KEY
    ),
    verbose=True
)

def send_email(to_email: str, subject: str, body: str):
    service = authenticate_gmail()
    message = MIMEText(body)
    message['to'] = to_email
    message['from'] = "me"
    message['subject'] = subject
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service.users().messages().send(
        userId="me",
        body={'raw': raw_message}
    ).execute()
    print(f" Email sent to {to_email}")

def create_and_send_customer_email(policy_result: dict, price_info: dict, customer_name: str, customer_email: str):
    task = Task(
        description=f"""
Policy Result: {policy_result}
Customer Name: {customer_name}

Requirements:
- Polite greeting
- Clearly explain if return is accepted or rejected 
- Mention reason in plain language
- Friendly closing
""",
        agent=customer_agent,
        expected_output="A well-written customer email"
    )
    crew = Crew(agents=[customer_agent], tasks=[task], verbose=False)
    crew_output = crew.kickoff()
    policy_email_body = str(crew_output)

    send_email(
        to_email=customer_email,
        subject="Regarding Your Return Request",
        body=policy_email_body
    )

    if policy_result.get("eligible"):
        refund_body = f"""
Dear {customer_name},

We are pleased to inform you that your return request has been approved .
The amount of {price_info.get('price', 'N/A')} {price_info.get('currency', '')} will be refunded to your original payment method within 5-7 business days.

Thank you for your patience and understanding.

Sincerely,
The Customer Support Team
"""
        send_email(
            to_email=customer_email,
            subject="Refund Processing Notification",
            body=refund_body
        )

    return policy_email_body
