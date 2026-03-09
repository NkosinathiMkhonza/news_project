from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.test import client as _test_client
from django.urls import reverse

from .models import (
    Article,
    Category,
    Notification,
    Publisher,
    Subscription,
    UserProfile,
)

# Django's default test client copies rendered template contexts for each
# request. On Python 3.14 this can fail inside Django's Context copy path,
# so we replace the callback with a safe variant that records templates
# without copying the context object.


def _safe_store_rendered_templates(store, signal, sender, template, context, **kwargs):
    store.setdefault("templates", []).append(template)
    store.setdefault("context", []).append(None)


_test_client.store_rendered_templates = _safe_store_rendered_templates


def set_role(user, role):
    profile = UserProfile.objects.get(user=user)
    profile.role = role
    profile.save()
    return profile


class RegistrationTests(TestCase):
    def test_user_can_register_with_supported_role(self):
        response = self.client.post(
            reverse("news:register"),
            data={
                "username": "tester",
                "email": "tester@example.com",
                "password1": "complexpass123",
                "password2": "complexpass123",
                "role": UserProfile.ROLE_JOURNALIST,
            },
        )

        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="tester")
        profile = UserProfile.objects.get(user=user)
        self.assertEqual(profile.role, UserProfile.ROLE_JOURNALIST)

    def test_publisher_role_is_rejected(self):
        response = self.client.post(
            reverse("news:register"),
            data={
                "username": "badrole",
                "email": "bad@example.com",
                "password1": "complexpass123",
                "password2": "complexpass123",
                "role": "publisher",
            },
        )

        self.assertContains(response, "Invalid role selected.")


class SettingsConfigTests(TestCase):
    def test_database_configs_are_explicit(self):
        from django.conf import settings

        self.assertIn("default", settings.DATABASES)
        self.assertIn("sqlite", settings.DATABASES)
        self.assertIn("mysql", settings.DATABASES)
        self.assertTrue(settings.DATABASES["default"]["ENGINE"].endswith("sqlite3"))


class EditorialWorkflowTests(TestCase):
    def setUp(self):
        self.editor = User.objects.create_user(
            username="editor",
            email="editor@example.com",
            password="complexpass123",
        )
        set_role(self.editor, UserProfile.ROLE_EDITOR)

        self.journalist = User.objects.create_user(
            username="journalist",
            email="journalist@example.com",
            password="complexpass123",
        )
        set_role(self.journalist, UserProfile.ROLE_JOURNALIST)

        self.reader = User.objects.create_user(
            username="reader",
            email="reader@example.com",
            password="complexpass123",
        )
        set_role(self.reader, UserProfile.ROLE_READER)

        self.category = Category.objects.create(
            name="General News",
            slug="general-news",
        )
        self.publisher = Publisher.objects.create(
            name="Daily Planet",
            slug="daily-planet",
            description="Metropolis news desk",
            created_by=self.editor,
        )

    def test_editor_can_create_publisher(self):
        self.client.force_login(self.editor)

        response = self.client.post(
            reverse("news:create_publisher"),
            data={
                "name": "Evening Dispatch",
                "slug": "evening-dispatch",
                "description": "Evening coverage",
                "website": "https://dispatch.example.com",
            },
        )

        self.assertRedirects(response, reverse("news:editor_dashboard"))
        new_publisher = Publisher.objects.get(slug="evening-dispatch")
        self.assertEqual(new_publisher.created_by, self.editor)

    def test_journalist_can_create_article_with_existing_publisher(self):
        self.client.force_login(self.journalist)

        response = self.client.post(
            reverse("news:create_article"),
            data={
                "title": "Fresh Setup Article",
                "slug": "fresh-setup-article",
                "content": "This article should be saved successfully.",
                "excerpt": "Short summary",
                "publisher": self.publisher.pk,
                "category": self.category.pk,
            },
        )

        self.assertRedirects(response, reverse("news:journalist_dashboard"))
        article = Article.objects.get()
        self.assertEqual(article.author, self.journalist)
        self.assertEqual(article.publisher, self.publisher)
        self.assertEqual(article.category, self.category)

    def test_editor_cannot_create_articles(self):
        self.client.force_login(self.editor)
        response = self.client.get(reverse("news:create_article"))
        self.assertEqual(response.status_code, 403)

    def test_editor_can_preview_pending_article(self):
        article = Article.objects.create(
            title="Pending Article",
            slug="pending-article",
            content="Pending review content",
            excerpt="Pending review",
            author=self.journalist,
            publisher=self.publisher,
            category=self.category,
            status="pending",
        )
        self.client.force_login(self.editor)

        response = self.client.get(reverse("news:article_preview", args=[article.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Preview")
        self.assertContains(response, "Pending Article")

    def test_comment_submission_redirects_to_namespaced_article_detail(self):
        article = Article.objects.create(
            title="Published Article",
            slug="published-article",
            content="Published content",
            excerpt="Published summary",
            author=self.journalist,
            publisher=self.publisher,
            category=self.category,
            status="published",
        )
        self.client.force_login(self.reader)

        response = self.client.post(
            reverse("news:article_detail", args=[article.pk]),
            data={"content": "First comment"},
        )

        self.assertRedirects(
            response, reverse("news:article_detail", args=[article.pk])
        )
        self.assertEqual(article.comments.count(), 1)

    def test_non_readers_cannot_comment(self):
        article = Article.objects.create(
            title="Published Article",
            slug="published-article-for-journalist-comment",
            content="Published content",
            excerpt="Published summary",
            author=self.journalist,
            publisher=self.publisher,
            category=self.category,
            status="published",
        )
        self.client.force_login(self.journalist)

        response = self.client.post(
            reverse("news:article_detail", args=[article.pk]),
            data={"content": "Journalist comment"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(article.comments.count(), 0)

    def test_only_readers_can_subscribe(self):
        self.client.force_login(self.journalist)
        forbidden_response = self.client.post(
            reverse("news:subscribe_publisher", args=[self.publisher.slug])
        )
        self.assertEqual(forbidden_response.status_code, 403)

        self.client.force_login(self.reader)
        allowed_response = self.client.post(
            reverse("news:subscribe_publisher", args=[self.publisher.slug])
        )
        self.assertRedirects(
            allowed_response,
            reverse("news:publisher_detail", args=[self.publisher.slug]),
        )
        self.assertTrue(
            Subscription.objects.filter(
                user=self.reader, publisher=self.publisher
            ).exists()
        )

    def test_publishing_notifies_subscribed_readers_once(self):
        Subscription.objects.create(user=self.reader, publisher=self.publisher)
        Subscription.objects.create(user=self.reader, journalist=self.journalist)

        article = Article.objects.create(
            title="Pending Article",
            slug="pending-article-for-notifications",
            content="Pending review content",
            excerpt="Pending review",
            author=self.journalist,
            publisher=self.publisher,
            category=self.category,
            status="pending",
        )
        self.client.force_login(self.editor)

        response = self.client.post(reverse("news:approve_article", args=[article.pk]))

        self.assertRedirects(response, reverse("news:editor_dashboard"))
        self.assertEqual(
            Notification.objects.filter(user=self.reader, article=article).count(),
            1,
        )

    def test_editor_can_delete_article(self):
        article = Article.objects.create(
            title="Delete Me",
            slug="delete-me",
            content="Draft content",
            excerpt="Draft summary",
            author=self.journalist,
            publisher=self.publisher,
            category=self.category,
            status="draft",
        )
        self.client.force_login(self.editor)

        response = self.client.post(reverse("news:delete_article", args=[article.pk]))

        self.assertRedirects(response, reverse("news:editor_dashboard"))
        self.assertFalse(Article.objects.filter(pk=article.pk).exists())

    def test_article_author_must_be_journalist(self):
        with self.assertRaises(ValidationError):
            Article.objects.create(
                title="Reader Authored Article",
                slug="reader-authored-article",
                content="This should fail validation.",
                excerpt="Invalid author role",
                author=self.reader,
                publisher=self.publisher,
                category=self.category,
                status="draft",
            )

    def test_login_respects_next_parameter(self):
        article = Article.objects.create(
            title="Published Article",
            slug="published-article-for-login-next",
            content="Published content",
            excerpt="Published summary",
            author=self.journalist,
            publisher=self.publisher,
            category=self.category,
            status="published",
        )

        response = self.client.post(
            reverse("news:login"),
            data={
                "username": self.reader.username,
                "password": "complexpass123",
                "next": reverse("news:article_detail", args=[article.pk]),
            },
        )

        self.assertRedirects(
            response,
            reverse("news:article_detail", args=[article.pk]),
        )

    def test_user_can_log_in_with_email_address(self):
        response = self.client.post(
            reverse("news:login"),
            data={
                "username": self.reader.email,
                "password": "complexpass123",
            },
        )

        self.assertRedirects(
            response,
            reverse("news:dashboard"),
            target_status_code=302,
        )
