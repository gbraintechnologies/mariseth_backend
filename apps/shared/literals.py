APP_NAME = 'mariseth'
REFRESH_TOKEN = 'refresh_token'
ACCESS_TOKEN = 'access_token'
EMAIL = 'email'
PASSWORD = 'password'
VERIFICATION_CODE = 'verification_code'
NEW_PASSWORD = 'new_password'
OLD_PASSWORD = 'old_password'
VERIFICATION_EMAIL_TEMPLATE = 'verification_email.html'
FORGOTTEN_PASSWORD_EMAIL_TEMPLATE = 'forgotten_password_email.html'

VIEW_GROUPS_AND_ROLES = 'account_management|list_groups_and_roles'
CREATE_GROUPS_AND_ROLES = 'account_management|create_group_and_assign_roles'
UPDATE_GROUPS_AND_ROLES = 'account_management|update_groups_and_roles'
DELETE_GROUPS_AND_ROLES = 'account_management|delete_groups_and_roles'

ADD_ADMIN = 'account_management|create_admin'
LIST_ADMINS = 'account_management|list_admins'
DELETE_ADMIN = 'account_management|delete_admin'
UPDATE_ADMIN = 'account_management|update_admin'

# FARMS
UPDATE_FARM = 'farm|update_farm'
CREATE_FARM = 'farm|create_farm'
DELETE_FARM = 'farm|delete_farm'
VIEW_FARM = 'farm|view_farm'
LIST_FARMS = 'farm|list_farms'
DELETE_FARM_PRODUCTS = 'farm|delete_farm_products'
UPLOAD_FARMS = 'farm|upload_farms'

# Farmer
CREATE_FARMER = 'farmer|create_farmer'
UPDATE_FARMER = 'farmer|update_farmer'
DELETE_FARMER = 'farmer|delete_farmer'
VIEW_FARMER = 'farmer|view_farmer'
LIST_FARMERS = 'farmer|list_farmers'
UPLOAD_FARMERS = 'farmer|upload_farmers'
GET_SMALLHOLDERS_BY_LEAD = 'farmer|get_smallholders_by_lead'
GET_FARMER_CREDIT_HISTORY = 'farmer|get_farmer_credit_history'

# Farmer
CREATE_PRODUCT = 'product|create_product'
UPDATE_PRODUCT = 'product|update_product'
DELETE_PRODUCT = 'product|delete_product'
VIEW_PRODUCT = 'product|view_product'
LIST_PRODUCTS = 'product|list_products'
UPLOAD_PRODUCTS = 'product|upload_products'
GET_PRODUCT_MOVEMENT = 'product|get_product_movement'

# Credits
CREATE_CREDIT = 'credit|create_credit'
UPDATE_CREDIT = 'credit|update_credit'
DELETE_CREDIT = 'credit|delete_credit'
VIEW_CREDIT = 'credit|view_credit'
LIST_CREDITS = 'credit|list_credits'
UPLOAD_CREDITS = 'credit|upload_credits'
APPROVE_OR_DENY_CREDIT = 'credit|approve_deny_credit'

# PAYBACKS
CREATE_PAYBACK = 'payback|create_payback'
UPDATE_PAYBACK = 'payback|update_payback'
LIST_PAYBACKS = 'payback|list_paybacks'

# warehouse
CREATE_WAREHOUSE = 'warehouse|create_warehouse'
UPDATE_WAREHOUSE = 'warehouse|update_warehouse'
DELETE_WAREHOUSE = 'warehouse|delete_warehouse'
VIEW_WAREHOUSE = 'warehouse|view_warehouse'
LIST_WAREHOUSES = 'warehouse|list_warehouses'
UPLOAD_WAREHOUSES = 'warehouse|upload_warehouses'
GET_WAREHOUSE_INVENTORY = 'warehouse|get_warehouse_inventory'
GET_PRODUCT_WAREHOUSE_MOVEMENT = 'warehouse|get_product_warehouse_movement'
ADD_REMOVE_WAREHOUSE_MANAGER = 'warehouse|add_remove_warehouse_manager'

# Customers
CREATE_CUSTOMER = 'customer|create_customer'
UPDATE_CUSTOMER = 'customer|update_customer'
DELETE_CUSTOMER = 'customer|delete_customer'
LIST_CUSTOMERS = 'customer|list_customers'
VIEW_CUSTOMER = 'customer|view_customer'

# custom type
CREATE_CUSTOM_TYPE = 'shared_custom_types|create_custom_type'
UPDATE_CUSTOM_TYPE = 'shared_custom_types|update_custom_type'
DELETE_CUSTOM_TYPE = 'shared_custom_types|delete_custom_type'
CREATE_OR_UPDATE_SETTINGS = 'shared_app_settings|create_or_update_settings'

# inflow orders
CREATE_INFLOW_ORDER = 'inflow_orders|create_inflow_order'
UPDATE_INFLOW_ORDER = 'inflow_orders|update_inflow_order'
VIEW_INFLOW_ORDER = 'inflow_orders|view_inflow_order'
DELETE_INFLOW_ORDER = 'inflow_orders|delete_inflow_order'
LIST_INFLOW_ORDERS = 'inflow_orders|list_inflow_orders'
APPROVE_INFLOW_DELIVERY_INSPECTION = 'inflow_orders|approve_inflow_delivery_inspection'
APPROVE_INFLOW_ORDER = 'inflow_orders|approve_inflow_order'

# OUTFLOW
#     SUPPLY CHAIN
CREATE_OUTFLOW_ORDER = 'outflow_orders|create_outflow_order'
UPDATE_OUTFLOW_ORDER = 'outflow_orders|update_outflow_order'
VIEW_OUTFLOW_ORDER = 'outflow_orders|view_outflow_order'
DELETE_OUTFLOW_ORDER = 'outflow_orders|delete_outflow_order'
LIST_OUTFLOW_ORDERS = 'outflow_orders|list_outflow_orders'
MARK_OUTFLOW_DELIVERED = 'outflow_orders|mark_outflow_delivered'
RECORD_OUTFLOW_PAYMENT = 'outflow_orders|record_outflow_payment'
MARK_OUTFLOW_COMPLETE = 'outflow_orders|mark_outflow_complete'
ASSIGN_DELIVERY_INFO = 'outflow_orders|assign_delivery_info'
#     APPROVALS
VIEW_OUTFLOW_APPROVAL = 'outflow_approvals|view_outflow_approval'
VERIFY_OUTFLOW_AVAILABILITY = 'outflow_approvals|verify_outflow_availability'
MARK_OUTFLOW_ORDER_PICKED = 'outflow_approvals|mark_outflow_order_picked'
LIST_OUTFLOW_APPROVAL = 'outflow_approvals|list_outflow_approvals'

# ACCOUNTING
LIST_EXPENSES = 'accounting|list_expenses'
LIST_WAYBILLS = 'accounting|list_waybills'
VIEW_WAYBILL = 'accounting|view_waybill'
DOWNLOAD_WAYBILL = 'accounting|download_waybill'
LIST_INVOICES = 'accounting|list_invoices'
VIEW_INVOICE = 'accounting|view_invoice'
DOWNLOAD_INVOICE = 'accounting|download_invoice'

# EVENT TYPES
CREATE_STRING = 'create'
UPDATE_FIELD_STRING = 'update_field'
DELETE_STRING = 'delete'
INCREASE_QUANTITY_STRING = 'increase_quantity'
DECREASE_QUANTITY_STRING = 'decrease_quantity'

# HR
LIST_DEPARTMENTS = "hr|list_departments"
CREATE_DEPARTMENT = "hr|create_department"
VIEW_DEPARTMENT = "hr|view_department"
UPDATE_DEPARTMENT = "hr|update_department"
DELETE_DEPARTMENT = "hr|delete_department"

LIST_JOB_TITLES = "hr|list_job_titles"
CREATE_JOB_TITLE = "hr|create_job_title"
VIEW_JOB_TITLE = "hr|view_job_title"
UPDATE_JOB_TITLE = "hr|update_job_title"
DELETE_JOB_TITLE = "hr|delete_job_title"

# Employee
CREATE_EMPLOYEE = 'employee|create_employee'
UPDATE_EMPLOYEE = 'employee|update_employee'
DELETE_EMPLOYEE = 'employee|delete_employee'
VIEW_EMPLOYEE = 'employee|view_employee'
LIST_EMPLOYEES = 'employee|list_employees'
ADD_EMPLOYEE_QUALIFICATION = 'employee|add_employee_qualification'
REMOVE_EMPLOYEE_QUALIFICATION = 'employee|remove_employee_qualification'
ADD_EMPLOYEE_DISCIPLINARY_ACTION = 'employee|add_employee_disciplinary_action'
LIST_EMPLOYEE_DISCIPLINARY_ACTIONS = 'employee|list_employee_disciplinary_actions'
