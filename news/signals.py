"""Django signals for the News Application."""

from django.contrib.auth.models import User
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Article, Notification, Subscription, UserProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a UserProfile automatically when a new User is created."""
    if created:
        UserProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save the UserProfile when the User is saved."""
    try:
        profile = UserProfile.objects.get(user=instance)
        profile.save()
    except UserProfile.DoesNotExist:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=Article)
def notify_subscribers_on_publication(sender, instance, **kwargs):
    """Create notifications when a subscribed article is published."""
    if instance.status != "published":
        return

    user_ids = (
        Subscription.objects.filter(
            Q(publisher=instance.publisher) | Q(journalist=instance.author),
            receive_notifications=True,
        )
        .values_list("user_id", flat=True)
        .distinct()
    )

    for user_id in user_ids:
        Notification.objects.get_or_create(
            user_id=user_id,
            article=instance,
            defaults={
                "message": (
                    f'New article published: "{instance.title}" '
                    f"by {instance.author.username}"
                )
            },
        )
