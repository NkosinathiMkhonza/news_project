"""API URL configuration for the News Application."""

from django.urls import path

from . import api_views

urlpatterns = [
    path("articles/", api_views.article_list_api, name="api_article_list"),
    path(
        "articles/<int:pk>/",
        api_views.article_detail_api,
        name="api_article_detail",
    ),
    path("categories/", api_views.category_list_api, name="api_category_list"),
    path("publishers/", api_views.publisher_list_api, name="api_publisher_list"),
    path("comments/", api_views.comment_create_api, name="api_comment_create"),
    path(
        "subscriptions/",
        api_views.subscription_list_api,
        name="api_subscription_list",
    ),
]
