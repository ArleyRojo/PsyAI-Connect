from django.db import models


class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True, db_index=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "NewsletterSubscribers"
        ordering = ["-created_at"]

    def __str__(self):
        return self.email

    def to_dict(self):
        return {
            "id": self.pk,
            "email": self.email,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
