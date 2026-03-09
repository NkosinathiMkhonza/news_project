"""Serializers for the News Application API."""

from django.contrib.auth.models import User
from rest_framework import serializers

from .models import (
    Article,
    Category,
    Comment,
    Publisher,
    Subscription,
)


class UserSerializer(serializers.ModelSerializer):
    """Serialize basic public fields for Django users."""

    class Meta:
        model = User
        fields = ["id", "username", "email"]


class CategorySerializer(serializers.ModelSerializer):
    """Serialize article category metadata."""

    class Meta:
        model = Category
        fields = ["id", "name", "slug"]


class PublisherSerializer(serializers.ModelSerializer):
    """Serialize publisher details for list and detail API responses."""

    class Meta:
        model = Publisher
        fields = ["id", "name", "slug", "description", "website"]


class ArticleListSerializer(serializers.ModelSerializer):
    """Serialize article fields required for collection/list endpoints."""

    author_name = serializers.CharField(source="author.username", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Article
        fields = [
            "id",
            "title",
            "slug",
            "excerpt",
            "author_name",
            "category_name",
            "status",
            "created_at",
        ]


class ArticleDetailSerializer(serializers.ModelSerializer):
    """Serialize a full article payload including related objects."""

    author = UserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    publisher = PublisherSerializer(read_only=True)

    class Meta:
        model = Article
        fields = [
            "id",
            "title",
            "slug",
            "content",
            "excerpt",
            "author",
            "category",
            "publisher",
            "status",
            "created_at",
            "published_at",
        ]


class CommentSerializer(serializers.ModelSerializer):
    """Validate and serialize reader comments for article APIs."""

    author_name = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "article", "author_name", "content", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_article(self, value):
        """Ensure comments are attached only to published articles."""
        if value.status != "published":
            raise serializers.ValidationError(
                "Comments are only allowed on published articles."
            )
        return value


class SubscriptionSerializer(serializers.ModelSerializer):
    """Serialize subscriptions with computed target information."""

    target_name = serializers.CharField(read_only=True)
    target_type = serializers.CharField(read_only=True)

    class Meta:
        model = Subscription
        fields = ["id", "target_type", "target_name", "subscribed_at"]
        read_only_fields = ["id", "subscribed_at"]
