import mysql.connector
import json

def get_order_and_customer_details(order_id: int):
    print(" Fetching order details...")

    try:
        mydb = mysql.connector.connect(
            host="localhost",
            user="",
            password="",
            database=""
        )

        cursor = mydb.cursor(dictionary=True)

        query = """
        SELECT o.OrderID, o.ProductID, o.CustomerID, o.Quantity, o.Price, o.Orderreturn, o.PurchaseDate,
               c.Name AS CustomerName, c.EmailID AS CustomerEmail
        FROM Orders o
        JOIN Customers c ON o.CustomerID = c.CustomerID
        WHERE o.OrderID = %s
        """

        cursor.execute(query, (order_id,))
        result = cursor.fetchone()

        if not result:
            return json.dumps({"error": " Order ID not found"})

        return json.dumps(result, default=str)

    except mysql.connector.Error as err:
        return json.dumps({"error": f" DB error: {str(err)}"})

    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'mydb' in locals() and mydb.is_connected():
            mydb.close()

