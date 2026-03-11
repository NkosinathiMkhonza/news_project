"""Models for the News Application."""

import uuid

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


def _get_profile(user):
    """Return the profile for a user when one exists."""
    if user is None:
        return None
    return UserProfile.objects.filter(user=user).first()


def _is_editor_user(user):
    """Allow editor actions for editor profiles and Django admins."""
    if user is None:
        return False
    if user.is_staff or user.is_superuser:
        return True
    profile = _get_profile(user)
    return profile is not None and profile.is_editor()


class UserProfile(models.Model):
    """Extended user profile with role-based access control."""

    ROLE_READER = "reader"
    ROLE_JOURNALIST = "journalist"
    ROLE_EDITOR = "editor"

    ROLE_CHOICES = [
        (ROLE_READER, "Reader"),
        (ROLE_JOURNALIST, "Journalist"),
        (ROLE_EDITOR, "Editor"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_READER)
    bio = models.TextField(max_length=500, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    def is_reader(self):
        return self.role == self.ROLE_READER

    def is_journalist(self):
        return self.role == self.ROLE_JOURNALIST

    def is_editor(self):
        return self.role == self.ROLE_EDITOR


class Publisher(models.Model):
    """News publisher/organization model."""

    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to="publishers/", blank=True, null=True)
    website = models.URLField(blank=True)
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="created_publishers"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_subscriber_count(self):
        return self.subscriptions.count()

    def clean(self):
        super().clean()
        if not self.created_by_id:
            return

        if not _is_editor_user(self.created_by):
            raise ValidationError(
                {"created_by": "Publishers must be created by an editor."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Category(models.Model):
    """Article category for organization."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Article(models.Model):
    """News article model with editorial workflow."""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("pending", "Pending Review"),
        ("published", "Published"),
        ("rejected", "Rejected"),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique_for_date="published_at")
    content = models.TextField()
    excerpt = models.TextField(max_length=300, blank=True)
    featured_image = models.ImageField(upload_to="articles/", blank=True, null=True)

    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="articles")
    publisher = models.ForeignKey(
        Publisher, on_delete=models.CASCADE, related_name="articles"
    )
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, related_name="articles"
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(blank=True, null=True)

    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_articles",
    )
    rejection_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()

        if self.author_id:
            author_profile = _get_profile(self.author)
            if author_profile is None or not author_profile.is_journalist():
                raise ValidationError(
                    {"author": "Articles must be authored by journalists."}
                )

        if self.reviewed_by_id and not _is_editor_user(self.reviewed_by):
            raise ValidationError({"reviewed_by": "Only editors can review articles."})

    def save(self, *args, **kwargs):
        if self.status == "published" and not self.published_at:
            self.published_at = timezone.now()
        self.full_clean()
        super().save(*args, **kwargs)

    def submit_for_review(self):
        if self.status in ["draft", "rejected"]:
            self.status = "pending"
            self.reviewed_by = None
            self.rejection_reason = ""
            self.save(update_fields=["status", "reviewed_by", "rejection_reason"])

    def approve(self, reviewer):
        if self.status == "pending":
            self.status = "published"
            self.reviewed_by = reviewer
            self.save()

    def reject(self, reviewer, reason=""):
        if self.status == "pending":
            self.status = "rejected"
            self.reviewed_by = reviewer
            self.rejection_reason = reason
            self.save()

    def get_comment_count(self):
        return self.comments.count()


class Comment(models.Model):
    """Reader comment on articles."""

    article = models.ForeignKey(
        Article, on_delete=models.CASCADE, related_name="comments"
    )
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")
    content = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Comment by {self.author.username} on {self.article.title}"

    def clean(self):
        super().clean()

        if self.author_id:
            author_profile = _get_profile(self.author)
            if author_profile is None or not author_profile.is_reader():
                raise ValidationError(
                    {"author": "Only readers can comment on articles."}
                )

        if self.article_id and self.article.status != "published":
            raise ValidationError(
                {"article": "Comments are only allowed on published articles."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Subscription(models.Model):
    """Reader subscription to either a publisher or a journalist."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="subscriptions"
    )
    publisher = models.ForeignKey(
        Publisher,
        on_delete=models.CASCADE,
        related_name="subscriptions",
        blank=True,
        null=True,
    )
    journalist = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="journalist_subscriptions",
        blank=True,
        null=True,
    )
    subscribed_at = models.DateTimeField(auto_now_add=True)
    receive_notifications = models.BooleanField(default=True)

    class Meta:
        ordering = ["-subscribed_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "publisher"],
                condition=Q(publisher__isnull=False),
                name="unique_reader_publisher_subscription",
            ),
            models.UniqueConstraint(
                fields=["user", "journalist"],
                condition=Q(journalist__isnull=False),
                name="unique_reader_journalist_subscription",
            ),
            models.CheckConstraint(
                condition=(
                    Q(publisher__isnull=False, journalist__isnull=True)
                    | Q(publisher__isnull=True, journalist__isnull=False)
                ),
                name="subscription_requires_single_target",
            ),
        ]

    def __str__(self):
        return f"{self.user.username} subscribed to {self.target_name}"

    @property
    def target_name(self):
        if self.publisher_id:
            return self.publisher.name
        if self.journalist_id:
            return self.journalist.username
        return "Unknown"

    @property
    def target_type(self):
        return "publisher" if self.publisher_id else "journalist"

    def clean(self):
        super().clean()

        if bool(self.publisher_id) == bool(self.journalist_id):
            raise ValidationError(
                "Select either a publisher or a journalist subscription."
            )

        subscriber_profile = UserProfile.objects.filter(user_id=self.user_id).first()
        if subscriber_profile is None or not subscriber_profile.is_reader():
            raise ValidationError("Only readers can subscribe.")

        if self.journalist_id:
            journalist_profile = UserProfile.objects.filter(
                user_id=self.journalist_id
            ).first()
            if journalist_profile is None or not journalist_profile.is_journalist():
                raise ValidationError(
                    "Journalist subscriptions must target a journalist."
                )

            if self.journalist_id == self.user_id:
                raise ValidationError("You cannot subscribe to yourself.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Notification(models.Model):
    """In-app notification for a newly published article."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications"
    )
    article = models.ForeignKey(
        Article, on_delete=models.CASCADE, related_name="notifications"
    )
    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ["user", "article"]

    def __str__(self):
        return f"Notification for {self.user.username}: {self.article.title}"


class Newsletter(models.Model):
    """Newsletter sent by a publisher to subscribers."""

    publisher = models.ForeignKey(
        Publisher, on_delete=models.CASCADE, related_name="newsletters"
    )
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    is_sent = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} - {self.publisher.name}"


class ResetToken(models.Model):
    """Token for password reset functionality."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="reset_tokens"
    )
    token = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Reset token for {self.user.username}"

    @classmethod
    def create_token(cls, user):
        token = str(uuid.uuid4())
        expires_at = timezone.now() + timezone.timedelta(hours=24)
        return cls.objects.create(user=user, token=token, expires_at=expires_at)

    def is_valid(self):
        if self.used:
            return False
        return timezone.now() < self.expires_at

    def mark_used(self):
        self.used = True
        self.save(update_fields=["used"])
