from apps.core.models import NewsletterSubscriber


class CoreRepository:
    def set_subscriber_active(self, subscriber, is_active):
        subscriber.is_active = is_active
        subscriber.save(update_fields=["is_active"])
        return subscriber
    def get_or_create_subscriber(self, email):
        return NewsletterSubscriber.objects.get_or_create(
            email=email,
            defaults={"is_active": True},
        )

    def get_active_subscriber_emails(self):
        return list(
            NewsletterSubscriber.objects.filter(is_active=True).values_list("email", flat=True)
        )
