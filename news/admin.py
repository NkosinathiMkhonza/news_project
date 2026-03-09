"""Admin configuration for the News Application."""

from django.contrib import admin

from .models import (
    Article,
    Category,
    Comment,
    Newsletter,
    Notification,
    Publisher,
    ResetToken,
    Subscription,
    UserProfile,
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "role", "created_at"]
    list_filter = ["role", "created_at"]
    search_fields = ["user__username", "user__email"]


@admin.register(Publisher)
class PublisherAdmin(admin.ModelAdmin):
    list_display = ["name", "created_by", "created_at"]
    search_fields = ["name", "created_by__username"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ["title", "author", "status", "created_at"]
    list_filter = ["status", "category", "created_at"]
    search_fields = ["title", "content", "author__username"]
    prepopulated_fields = {"slug": ("title",)}
    actions = ["approve_articles"]

    def approve_articles(self, request, queryset):
        count = 0
        for article in queryset.filter(status="pending"):
            article.approve(request.user)
            count += 1
        self.message_user(request, f"{count} articles approved.")

    approve_articles.short_description = "Approve selected pending articles"


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ["author", "article", "created_at"]
    search_fields = ["content", "author__username"]


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ["user", "target_type", "target_name", "subscribed_at"]
    list_filter = ["subscribed_at"]

    @admin.display(description="Target Type")
    def target_type(self, obj):
        return obj.target_type

    @admin.display(description="Target")
    def target_name(self, obj):
        return obj.target_name


@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    list_display = ["title", "publisher", "is_sent", "created_at"]
    list_filter = ["is_sent", "publisher"]


@admin.register(ResetToken)
class ResetTokenAdmin(admin.ModelAdmin):
    list_display = ["user", "created_at", "used"]
    list_filter = ["used", "created_at"]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["user", "article", "created_at", "is_read"]
    list_filter = ["is_read", "created_at"]
    search_fields = ["user__username", "article__title", "message"]
