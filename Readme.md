# Mariseth360

## Features
- **User Accounts Management**: Create and manage user accounts with role-based access control.
- **Organization Management**: Create, update, and manage organizations and their structure.
- **Communication Tools**: Send notifications and messages to users within the platform.
- **Shareholder Management**: Manage shareholder information and track their interactions.
- **Dividend Management**: Create and manage dividend information and payouts.
- **Organization User Management**: Assign and manage users within organizations.

## Getting Started

### Prerequisites
- Docker installed on your machine.

### Installation
1. Clone the repository:
   ```bash
   git clone git@github.com:premiertechlab/mariseth-backend.git
   cd mariseth-backend
   ```

2. Create the main branch:
   ```bash
   git checkout development
   ```
3. Run the application:
   ```bash
   docker-compose -f docker-compose.local.yml up --build
   ```

4. Set up the organization:
   - Create the main branch.
   - Create the organization.
   - Create the user.
   - Create the organization user.
   - Create the custom types.
     1. **default_email**: Represents the default email address for communication.
     2. **organization_domain**: Represents the domain associated with the organization.
   - Create the app settings.
     1. **share_pricing**: Represents the share pricing for the organization.
     2. **tax_value**: Represents the tax value for the organization.
     3. **config**: Represents the configuration for the organization.

