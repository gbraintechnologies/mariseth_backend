import requests
from django.conf import settings
from requests import Response


class MeshManagerAPIClient:
    """
    A client for interacting with the Meshsuites Manager.io API.
    """

    def __init__(self):
        self.api_key = settings.MANAGER_IO_API_KEY
        self.headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }

    def _post(self, endpoint: str, payload: dict) -> Response:
        """
        Internal method to handle POST requests.
        """
        print("--- Manager.io POST Request ---")
        print(f"URL: {endpoint}")
        print(f"Payload: {payload}")
        print("-----------------------------")
        response = requests.post(endpoint, headers=self.headers, json=payload, timeout=30)
        print("--- Manager.io POST Response ---")
        print(f"Status Code: {response.status_code}")
        try:
            print(f"Response JSON: {response.json()}")
        except requests.exceptions.JSONDecodeError:
            print(f"Response Text: {response.text}")
        print("------------------------------")
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        return response

    def create_customer(self, customer_data: dict) -> dict:
        """
        Creates a customer in Manager.io.

        Args:
            customer_data: A dictionary representing the customer payload.
                         Example:
                         {
                             "code": "C-01006",
                             "name": "Spektra Global Limited",
                             "billingAddress": "Tumu",
                             ...
                         }

        Returns:
            The JSON response from the API.
        """
        endpoint = "https://meshsuites.manager.io/api2/customer-form"
        response = self._post(endpoint, customer_data)
        return response.json()

    def create_employee(self, employee_data: dict) -> dict:
        """
        Creates an employee in Manager.io.

        Args:
            employee_data: A dictionary representing the employee payload.

        Returns:
            The JSON response from the API.
        """
        endpoint = "https://meshsuites.manager.io/api2/employee-form"
        response = self._post(endpoint, employee_data)
        return response.json()

    def create_inventory_item(self, item_data: dict) -> dict:
        """
        Creates an inventory item in Manager.io.

        Args:
            item_data: A dictionary representing the inventory item payload.

        Returns:
            The JSON response from the API.
        """
        endpoint = "https://meshsuites.manager.io/api2/inventory-item-form"
        response = self._post(endpoint, item_data)
        return response.json()

    def create_supplier(self, supplier_data: dict) -> dict:
        """
        Creates a supplier in Manager.io.

        Args:
            supplier_data: A dictionary representing the supplier payload.

        Returns:
            The JSON response from the API.
        """
        endpoint = "https://meshsuites.manager.io/api2/supplier-form"
        response = self._post(endpoint, supplier_data)
        return response.json()

    def create_purchase_invoice(self, invoice_data: dict) -> dict:
        """
        Creates a purchase invoice in Manager.io.

        Args:
            invoice_data: A dictionary representing the purchase invoice payload.

        Returns:
            The JSON response from the API.
        """
        endpoint = "https://meshsuites.manager.io/api2/purchase-invoice-form"
        response = self._post(endpoint, invoice_data)
        return response.json()

    def create_sales_invoice(self, invoice_data: dict) -> dict:
        """
        Creates a sales invoice in Manager.io.

        Args:
            invoice_data: A dictionary representing the sales invoice payload.

        Returns:
            The JSON response from the API.
        """
        endpoint = "https://meshsuites.manager.io/api2/sales-invoice-form"
        response = self._post(endpoint, invoice_data)
        return response.json()

