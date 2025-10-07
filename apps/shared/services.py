import requests
from django.conf import settings
from requests import Response


class MeshManagerAPIClient:
    """
    A client for interacting with the Meshsuites Manager.io API.
    """

    def __init__(self):
        self.base_url = settings.MANAGER_IO_BASE_URL
        self.api_key = settings.MANAGER_IO_API_KEY
        self.headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }
        # The staging server uses a different endpoint naming convention.
        self.use_plural_endpoints = "af-south-1" in self.base_url

    def _get_endpoint(self, singular_form: str, plural_form: str) -> str:
        """
        Selects the correct API endpoint based on the environment.
        - Production/Local uses singular forms (e.g., 'customer-form').
        - Staging uses plural forms (e.g., 'customers').
        """
        if self.use_plural_endpoints:
            return f"/api2/{plural_form}"
        return f"/api2/{singular_form}"

    def _post(self, endpoint: str, payload: dict) -> Response:
        """
        Internal method to handle POST requests.
        """
        url = f"{self.base_url}{endpoint}"
        response = requests.post(url, headers=self.headers, json=payload, timeout=30)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        return response

    def create_customer(self, customer_data: dict) -> dict:
        """
        Creates a customer in Manager.io.

        Args:
            customer_data: A dictionary representing the customer payload.
        """
        endpoint = self._get_endpoint("customer-form", "customers")
        response = self._post(endpoint, customer_data)
        return response.json()

    def create_employee(self, employee_data: dict) -> dict:
        """
        Creates an employee in Manager.io.

        Args:
            employee_data: A dictionary representing the employee payload.
        """
        endpoint = self._get_endpoint("employee-form", "employees")
        response = self._post(endpoint, employee_data)
        return response.json()

    def create_inventory_item(self, item_data: dict) -> dict:
        """
        Creates an inventory item in Manager.io.

        Args:
            item_data: A dictionary representing the inventory item payload.
        """
        endpoint = self._get_endpoint("inventory-item-form", "inventory-items")
        response = self._post(endpoint, item_data)
        return response.json()

    def create_supplier(self, supplier_data: dict) -> dict:
        """
        Creates a supplier in Manager.io.

        Args:
            supplier_data: A dictionary representing the supplier payload.
        """
        endpoint = self._get_endpoint("supplier-form", "suppliers")
        response = self._post(endpoint, supplier_data)
        return response.json()

    def create_purchase_invoice(self, invoice_data: dict) -> dict:
        """
        Creates a purchase invoice in Manager.io.

        Args:
            invoice_data: A dictionary representing the purchase invoice payload.
        """
        endpoint = self._get_endpoint("purchase-invoice-form", "purchase-invoices")
        response = self._post(endpoint, invoice_data)
        return response.json()

    def create_sales_invoice(self, invoice_data: dict) -> dict:
        """
        Creates a sales invoice in Manager.io.

        Args:
            invoice_data: A dictionary representing the sales invoice payload.
        """
        endpoint = self._get_endpoint("sales-invoice-form", "sales-invoices")
        response = self._post(endpoint, invoice_data)
        return response.json()

