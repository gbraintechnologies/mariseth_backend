import sentry_sdk
from celery import shared_task
from django.contrib.auth import get_user_model
from django.template.loader import get_template

from apps.hr.models import Training, TrainingAttendee
from apps.shared.tasks.utils import get_organization_default_sender_id, get_organization_email
from apps.shared.utils.email_client import EmailClient
from apps.shared.utils.sms_client import SMSClient
from mariseth.logging import logger

User = get_user_model()


@shared_task
def send_training_notification(training_id):
    print("sending training notification")
    try:
        training = Training.objects.select_related('organization').get(pk=training_id)
        attendees = TrainingAttendee.objects.filter(training=training).select_related('employee')

        sms_message = (
            f"You have been invited to a training: {training.title}. "
            f"Date: {training.start_date.strftime('%Y-%m-%d %H:%M')}. "
            f"Location: {training.location or 'Not available at this time'}."
        )

        sms_client = SMSClient()
        email_client = EmailClient()
        for attendee in attendees:
            employee = attendee.employee

            if employee.notification == 'sms':
                if not employee.phone_number:
                    logger.warning(f"Employee {employee.first_name} {employee.last_name} has no phone number")
                    continue

                try:
                    organization = employee.organization
                    sender_id = get_organization_default_sender_id(organization)

                    sms_client.send_sms(
                        phone_number=employee.phone_number,
                        message=sms_message,
                        sender_id=sender_id
                    )
                    logger.info(f"SMS sent to {employee.phone_number} for training {training.title}")

                except Exception as e:
                    logger.error(f"Failed to send SMS to {employee.phone_number}: {str(e)}")
                    sentry_sdk.capture_exception(e)

            elif employee.notification == 'email':
                if not employee.email:
                    logger.warning(f"Employee {employee.first_name} {employee.last_name} has no email")
                    continue

                try:
                    context = {
                        'user_fullname': f"{employee.first_name} {employee.last_name}",
                        'employee': employee,
                        'training': training,
                    }
                    template = get_template('training_invite.html')
                    email_html = template.render(context)
                    email_text = f"You have been invited to training: {training.title}"

                    sender_email = get_organization_email(employee.organization)
                    print("sending email to", employee.email)
                    email_client.send_email(
                        sender=sender_email,
                        recipients=[employee.email],
                        subject=f"Training Invitation: {training.title}",
                        body_html=email_html,
                        body_text=email_text
                    )
                    logger.info(f"Email sent to {employee.email} for training {training.title}")

                except Exception as e:
                    logger.error(f"Failed to send email to {employee.email}: {str(e)}")
                    sentry_sdk.capture_exception(e)

    except Training.DoesNotExist:
        logger.error(f"Training with ID {training_id} does not exist")
    except Exception as e:
        logger.error(f"Error in send_training_sms_notification for training ID {training_id}: {str(e)}")
        sentry_sdk.capture_exception(e)
        raise