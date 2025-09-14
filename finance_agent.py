from dotenv import load_dotenv
from crewai import Agent, Task, Crew, LLM
import mysql.connector

load_dotenv()

GEMINI_API_KEY = ""

llm = LLM(
    model="gemini/gemini-1.5-flash",
    api_key=GEMINI_API_KEY
)

finance_agent = Agent(
    role="Finance Agent",
    goal="Retrieve order price from the OrderManagement database by order ID.",
    backstory="You access the database to provide the order price.",
    llm=llm,
    verbose=True
)

def get_order_price(order_id: str):
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database=""
        )

        cursor = connection.cursor(dictionary=True)
        query = "SELECT Price FROM Orders WHERE OrderID = %s"
        cursor.execute(query, (order_id,))
        result = cursor.fetchone()

        if result:
            price = result['Price']
        else:
            price = "Not Found"

    except Exception as e:
        print(f" Database error: {e}")
        price = "Error"

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

    return {
        "order_id": order_id,
        "price": price,
        "currency": "USD"
    }
