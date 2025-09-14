import os
import json
import re
from dotenv import load_dotenv
from crewai import LLM, Agent, Task, Crew, tools
from Order import get_order_and_customer_details  # Custom tool
from planner_agent import process_email_with_planner

# Load environment variables
dotenv_path = r""
load_dotenv(dotenv_path)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize main LLM
llm = LLM(
    model="gemini/gemini-1.5-flash",
    api_key=GEMINI_API_KEY
)

# Pure function implementations
import re

def extract_order_id_logic(email_body: str) -> int:
    match = re.search(r"order id[: ]+(\d+)", email_body, re.IGNORECASE)
    return int(match.group(1)) if match else None



def order_and_customer_details_logic(order_id: int) -> dict:
    """
    Given an order ID, return the order and customer details as a dictionary.
    """
    details = get_order_and_customer_details(order_id)
    print(f"[DEBUG] get_order_and_customer_details output for order_id {order_id}: {details}")
    return details


# Register tools for Crew AI
@tools.tool
def extract_order_id(email_body: str) -> int:
    """
    Tool to extract order ID from the customer email body.
    Returns the order ID as an integer, or None if not found.
    """
    return extract_order_id_logic(email_body)


@tools.tool
def order_and_customer_details_tool(order_id: int) -> dict:
    """
    Tool to retrieve order and customer details given an order ID.
    Returns a dictionary with order and customer information.
    """
    return order_and_customer_details_logic(order_id)


# Define Planner Agent
planner_agent = Agent(
    role="Planner Agent",
    goal="""
Based on the provided order ID and order/customer details, decide return eligibility using the Policy Agent,
generate customer email messages, calculate refund amount if eligible, and respond in a structured JSON.
""",
    backstory="""
You are responsible for automating product return workflows.
Respond strictly in a structured JSON format.
""",
    llm=llm,
    verbose=True
)

# Main Planner Process Function
def process_email_with_planner1(email_body: str, sender_email: str = None):
    print(f"\nProcessing incoming email:\n{email_body}")

    # Step 1: Extract order ID
    order_id = extract_order_id_logic(email_body=email_body)
   # order_id=104
    if not order_id:
        result = {"error": "Failed to extract order ID", "order_id": None}
        print("\nPlanner Agent Output:")
        print(json.dumps(result, indent=2))
        return result

    print(f"[DEBUG] Extracted order ID: {order_id}")

    # Step 2: Get order and customer details
    order_and_customer_details = order_and_customer_details_logic(order_id=order_id)
    if not order_and_customer_details:
        result = {"error": "Failed to get order and customer details"}
        print("\nPlanner Agent Output:")
        print(json.dumps(result, indent=2))
        return result

    print(f"[DEBUG] Order and customer details: {order_and_customer_details}")

    # Step 3: Pass data to Planner Agent to orchestrate the refund process
    task = Task(
        description=f"""
You are a Planner Agent responsible for orchestrating the refund process.

Order ID: {order_id}
Order and Customer Details: {json.dumps(order_and_customer_details)}

Autonomously perform the following steps:
1. Check return eligibility using the Policy Agent.
2. Generate an initial customer email about eligibility.
3. Calculate refund amount if eligible.
4. Generate final customer email.

Respond ONLY with a structured JSON:
{{
    "order_id": {order_id},
    "order_and_customer_details": {json.dumps(order_and_customer_details)},
    "eligibility_status": true/false,
    "refund_amount": amount_if_eligible_or_null,
    "initial_customer_email_message": "...",
    "final_customer_email_message": "...",
    "error": null_or_error_description
}}
""",
        agent=planner_agent,
        expected_output="Structured JSON with refund process result"
    )

    crew = Crew(agents=[planner_agent], tasks=[task], verbose=True)
    planner_output = crew.kickoff()
    planner_output_dict = planner_output.to_dict()

    try:
        result = json.loads(planner_output_dict.get('output', ''))
    except Exception:
        result = {
            "error": "Planner agent failed to provide structured output.",
            "raw_output": planner_output_dict.get('output', ' ')
        }

    print("\nPlanner Agent Output:")
    print(json.dumps(result, indent=2))

    return result


# Debug Entry Point
if __name__ == "__main__":
    sample_email = """
    Hello Support Team,

    I would like to return my recent purchase. The order id is 12345.

    Thank you.
    """

    process_email_with_planner(sample_email, sender_email="customer@example.com")

