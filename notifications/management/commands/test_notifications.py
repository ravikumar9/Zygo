import json
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils import timezone

from notifications.services import NotificationService


class Command(BaseCommand):
    help = "Send test email/SMS via NotificationService (Phase 1 infra dry-run friendly)."

    def add_arguments(self, parser):
        parser.add_argument("--email", dest="email", help="Destination email address")
        parser.add_argument("--phone", dest="phone", help="Destination phone with country code (e.g., 919876543210)")
        parser.add_argument("--subject", dest="subject", default="GoExplorer Test Notification")
        parser.add_argument(
            "--template",
            dest="template",
            default="notifications/email/test_email.html",
            help="Django template path for email body",
        )
        parser.add_argument(
            "--template-id",
            dest="template_id",
            help="MSG91 template ID for SMS (required for SMS send)",
        )
        parser.add_argument(
            "--var",
            dest="vars",
            action="append",
            default=[],
            help="Template variable in key=value form (can be repeated)",
        )
        parser.add_argument("--dry-run", dest="dry_run", action="store_true", help="Force dry-run (no external calls)")
        parser.add_argument("--user-id", dest="user_id", type=int, help="User ID to attribute notifications to")

    def handle(self, *args, **options):
        email = options.get("email")
        phone = options.get("phone")
        template_id = options.get("template_id")
        dry_run = options.get("dry_run")
        user = self._resolve_user(options.get("user_id"))

        variables = self._parse_vars(options.get("vars") or [])
        # Baseline context for email rendering
        context = {
            "name": variables.get("name", "GoExplorer User"),
            "message": variables.get("message", "This is a test notification from GoExplorer."),
            "extras": {k: v for k, v in variables.items() if k not in {"name", "message"}},
            "timestamp": timezone.now(),
        }

        if not email and not (phone and template_id):
            raise CommandError("Provide --email or both --phone and --template-id to send a test notification.")

        if email:
            notification = NotificationService.send_email(
                to=email,
                subject=options.get("subject"),
                template=options.get("template"),
                context=context,
                user=user,
                dry_run=dry_run,
            )
            self.stdout.write(self.style.SUCCESS(f"Email queued: status={notification.status}, recipient={notification.recipient}"))

        if phone and template_id:
            notification = NotificationService.send_sms(
                phone=phone,
                template_id=template_id,
                variables=variables,
                user=user,
                dry_run=dry_run,
            )
            self.stdout.write(self.style.SUCCESS(f"SMS queued: status={notification.status}, recipient={notification.recipient}"))

    def _parse_vars(self, items):
        parsed = {}
        for item in items:
            if "=" not in item:
                continue
            key, value = item.split("=", 1)
            parsed[key.strip()] = value.strip()
        return parsed

    def _resolve_user(self, user_id):
        if not user_id:
            return None
        User = get_user_model()
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise CommandError(f"User with id={user_id} does not exist")
