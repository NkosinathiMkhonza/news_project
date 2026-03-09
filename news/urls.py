"""URL configuration for the news app."""

from django.urls import path

from . import views

app_name = "news"

urlpatterns = [
    path("", views.home, name="home"),
    path("articles/", views.article_list, name="article_list"),
    path("article/<int:pk>/", views.article_detail, name="article_detail"),
    path("article/<int:pk>/preview/", views.article_preview, name="article_preview"),
    path("register/", views.register, name="register"),
    path("login/", views.user_login, name="login"),
    path("logout/", views.user_logout, name="logout"),
    path("forgot-password/", views.forgot_password, name="forgot_password"),
    path(
        "reset-password/<str:token>/",
        views.reset_password,
        name="reset_password",
    ),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/reader/", views.reader_dashboard, name="reader_dashboard"),
    path(
        "dashboard/journalist/",
        views.journalist_dashboard,
        name="journalist_dashboard",
    ),
    path("dashboard/editor/", views.editor_dashboard, name="editor_dashboard"),
    path("publishers/create/", views.create_publisher, name="create_publisher"),
    path("article/create/", views.create_article, name="create_article"),
    path("article/<int:pk>/edit/", views.edit_article, name="edit_article"),
    path("article/<int:pk>/delete/", views.delete_article, name="delete_article"),
    path("article/<int:pk>/submit/", views.submit_article, name="submit_article"),
    path(
        "article/<int:pk>/approve/",
        views.approve_article,
        name="approve_article",
    ),
    path("article/<int:pk>/reject/", views.reject_article, name="reject_article"),
    path("publishers/", views.publisher_list, name="publisher_list"),
    path(
        "publisher/<slug:slug>/",
        views.publisher_detail,
        name="publisher_detail",
    ),
    path(
        "publisher/<slug:slug>/subscribe/",
        views.subscribe_publisher,
        name="subscribe_publisher",
    ),
    path(
        "publisher/<slug:slug>/unsubscribe/",
        views.unsubscribe_publisher,
        name="unsubscribe_publisher",
    ),
    path(
        "journalist/<str:username>/",
        views.journalist_detail,
        name="journalist_detail",
    ),
    path(
        "journalist/<str:username>/subscribe/",
        views.subscribe_journalist,
        name="subscribe_journalist",
    ),
    path(
        "journalist/<str:username>/unsubscribe/",
        views.unsubscribe_journalist,
        name="unsubscribe_journalist",
    ),
    path("subscriptions/", views.subscriptions, name="subscriptions"),
]
