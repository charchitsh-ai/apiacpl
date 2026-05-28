# Import all models here so that Alembic's target_metadata can discover them.
from app.models.base import Base  # noqa
from app.models.user import User  # noqa
from app.models.otp import OtpVerification  # noqa
from app.models.token import RefreshToken  # noqa
from app.models.session import DeviceSession  # noqa
from app.models.symptom import Symptom  # noqa
from app.models.speciality import Speciality  # noqa
from app.models.doctor import Doctor, DoctorAvailability, DoctorReview  # noqa
from app.models.appointment import Appointment, AppointmentStatusLog  # noqa
from app.models.notification import Notification, NotificationTemplate, ReminderJob  # noqa




