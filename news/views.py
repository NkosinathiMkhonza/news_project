"""Views for the News Application."""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import ArticleForm, CommentForm, PublisherForm
from .models import (
    Article,
    Category,
    Publisher,
    ResetToken,
    Subscription,
    UserProfile,
)


def _get_or_create_profile(user):
    """Return a user's profile, creating a reader profile when missing."""
    profile, _ = UserProfile.objects.get_or_create(
        user=user, defaults={"role": UserProfile.ROLE_READER}
    )
    return profile


def _get_default_category():
    """Provide a fallback category so article creation works on a fresh DB."""
    category, _ = Category.objects.get_or_create(
        slug="general",
        defaults={
            "name": "General",
            "description": "Default category for new article submissions.",
        },
    )
    return category


def _redirect_to_login(request):
    """Send anonymous users to the login page and preserve their target."""
    return redirect(f"{reverse('news:login')}?next={request.path}")


def home(request):
    """Display the home page with recent published articles."""
    articles_list = Article.objects.filter(status="published").select_related(
        "author", "category", "publisher"
    )
    paginator = Paginator(articles_list, 10)
    page = request.GET.get("page", 1)
    articles = paginator.get_page(page)
    categories = Category.objects.all()
    publishers = Publisher.objects.all()
    return render(
        request,
        "news/home.html",
        {
            "articles": articles,
            "categories": categories,
            "publishers": publishers,
        },
    )


def article_list(request):
    """Display a list of articles with filtering options."""
    articles = Article.objects.filter(status="published").select_related(
        "author", "category", "publisher"
    )
    category_slug = request.GET.get("category")
    if category_slug:
        articles = articles.filter(category__slug=category_slug)

    publisher_slug = request.GET.get("publisher")
    if publisher_slug:
        articles = articles.filter(publisher__slug=publisher_slug)

    search_query = request.GET.get("q")
    if search_query:
        articles = articles.filter(title__icontains=search_query)

    paginator = Paginator(articles, 12)
    page = request.GET.get("page", 1)
    articles = paginator.get_page(page)
    return render(
        request,
        "news/article_list.html",
        {
            "articles": articles,
            "categories": Category.objects.all(),
            "publishers": Publisher.objects.all(),
        },
    )


def article_detail(request, pk):
    """Display a single published article and its comments."""
    article = get_object_or_404(
        Article.objects.select_related(
            "author", "author__profile", "category", "publisher"
        ),
        pk=pk,
        status="published",
    )
    comments = article.comments.select_related("author")
    reader_profile = None
    is_author_subscribed = False
    is_publisher_subscribed = False

    if request.user.is_authenticated:
        reader_profile = _get_or_create_profile(request.user)
        if reader_profile.is_reader():
            is_author_subscribed = Subscription.objects.filter(
                user=request.user, journalist=article.author
            ).exists()
            is_publisher_subscribed = Subscription.objects.filter(
                user=request.user, publisher=article.publisher
            ).exists()

    if request.method == "POST":
        if not request.user.is_authenticated:
            return _redirect_to_login(request)

        if reader_profile is None or not reader_profile.is_reader():
            return HttpResponseForbidden("Only readers can comment on articles.")

        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.article = article
            comment.author = request.user
            comment.save()
            messages.success(request, "Comment added successfully!")
            return redirect("news:article_detail", pk=article.pk)
    else:
        comment_form = CommentForm()

    return render(
        request,
        "news/article_detail.html",
        {
            "article": article,
            "comment_form": comment_form,
            "comments": comments,
            "is_author_subscribed": is_author_subscribed,
            "is_publisher_subscribed": is_publisher_subscribed,
            "preview_mode": False,
            "reader_profile": reader_profile,
        },
    )


@login_required
def article_preview(request, pk):
    """Allow authors and editors to preview unpublished articles."""
    article = get_object_or_404(
        Article.objects.select_related(
            "author", "author__profile", "category", "publisher"
        ),
        pk=pk,
    )
    profile = _get_or_create_profile(request.user)
    if not (profile.is_editor() or article.author == request.user):
        return HttpResponseForbidden("You don't have permission.")

    return render(
        request,
        "news/article_detail.html",
        {
            "article": article,
            "comment_form": None,
            "comments": [],
            "preview_mode": True,
            "reader_profile": None,
            "is_author_subscribed": False,
            "is_publisher_subscribed": False,
        },
    )


def register(request):
    """User registration view."""
    valid_roles = [
        UserProfile.ROLE_READER,
        UserProfile.ROLE_JOURNALIST,
        UserProfile.ROLE_EDITOR,
    ]

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password1 = request.POST.get("password1", "")
        password2 = request.POST.get("password2", "")
        role = request.POST.get("role", UserProfile.ROLE_READER)

        errors = []

        if not username:
            errors.append("Username is required.")
        elif User.objects.filter(username=username).exists():
            errors.append(
                "Username already exists. "
                "If this is your account, please log in instead."
            )

        if not email:
            errors.append("Email is required.")
        elif User.objects.filter(email=email).exists():
            errors.append(
                "Email already registered. "
                "If this is your account, please log in instead."
            )

        if not password1:
            errors.append("Password is required.")
        elif len(password1) < 8:
            errors.append("Password must be at least 8 characters long.")

        if password1 != password2:
            errors.append("Passwords do not match.")

        if role not in valid_roles:
            errors.append("Invalid role selected.")

        if errors:
            return render(
                request,
                "news/register.html",
                {
                    "errors": errors,
                    "username": username,
                    "email": email,
                    "role": role,
                },
            )

        try:
            user = User.objects.create_user(
                username=username, email=email, password=password1
            )
            UserProfile.objects.update_or_create(user=user, defaults={"role": role})
            login(request, user)
            messages.success(request, "Account created successfully! Welcome!")
            return redirect("news:dashboard")
        except IntegrityError:
            errors.append("An error occurred. Username or email may already exist.")
            return render(
                request,
                "news/register.html",
                {
                    "errors": errors,
                    "username": username,
                    "email": email,
                    "role": role,
                },
            )

    return render(request, "news/register.html")


def user_login(request):
    """User login view."""
    next_url = request.POST.get("next") or request.GET.get("next")
    safe_next_url = None
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        safe_next_url = next_url

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        auth_username = username

        if "@" in username:
            matched_user = User.objects.filter(email__iexact=username).first()
            if matched_user is not None:
                auth_username = matched_user.username

        user = authenticate(request, username=auth_username, password=password)
        if user is not None:
            login(request, user)
            _get_or_create_profile(user)
            messages.success(request, f"Welcome back, {user.username}!")
            if safe_next_url:
                return redirect(safe_next_url)
            return redirect("news:dashboard")

        messages.error(request, "Invalid username or password.")
        return render(
            request,
            "news/login.html",
            {
                "error": "Invalid username or password.",
                "next": safe_next_url,
            },
        )

    return render(request, "news/login.html", {"next": safe_next_url})


@login_required
def user_logout(request):
    """Handle user logout."""
    logout(request)
    messages.success(request, "You have been successfully logged out.")
    return redirect("news:home")


def forgot_password(request):
    """Handle password reset request."""
    if request.method == "POST":
        email = request.POST.get("email")
        try:
            user = User.objects.get(email=email)
            token = ResetToken.create_token(user)
            reset_url = (
                f"{request.scheme}://{request.get_host()}"
                f"/reset-password/{token.token}/"
            )
            send_mail(
                "Password Reset",
                f"Click to reset: {reset_url}",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
            )
            messages.success(request, "Password reset email sent.")
            return redirect("news:login")
        except User.DoesNotExist:
            messages.error(request, "No account found with that email.")
    return render(request, "news/forgot_password.html")


def reset_password(request, token):
    """Handle password reset with token."""
    try:
        reset_token = ResetToken.objects.get(token=token)
        if not reset_token.is_valid():
            messages.error(request, "This reset link has expired.")
            return redirect("news:forgot_password")

        if request.method == "POST":
            password1 = request.POST.get("password1")
            password2 = request.POST.get("password2")
            if password1 != password2:
                messages.error(request, "Passwords do not match.")
            elif len(password1) < 8:
                messages.error(request, "Password must be at least 8 characters.")
            else:
                user = reset_token.user
                user.set_password(password1)
                user.save()
                reset_token.mark_used()
                messages.success(request, "Password reset successfully!")
                return redirect("news:login")
    except ResetToken.DoesNotExist:
        messages.error(request, "Invalid reset link.")
        return redirect("news:forgot_password")

    return render(request, "news/reset_password.html", {"token": token})


@login_required
def reader_dashboard(request):
    """Display the reader dashboard."""
    profile = _get_or_create_profile(request.user)
    if not profile.is_reader():
        return HttpResponseForbidden("You don't have permission.")

    subscriptions = request.user.subscriptions.select_related("publisher", "journalist")
    comments = request.user.comments.select_related("article")[:10]
    notifications = request.user.notifications.select_related("article")[:10]
    return render(
        request,
        "news/dashboard/reader.html",
        {
            "subscriptions": subscriptions,
            "comments": comments,
            "notifications": notifications,
        },
    )


@login_required
def journalist_dashboard(request):
    """Display the journalist dashboard."""
    profile = _get_or_create_profile(request.user)
    if not profile.is_journalist():
        return HttpResponseForbidden("You don't have permission.")

    articles = request.user.articles.select_related("publisher", "category")
    return render(
        request,
        "news/dashboard/journalist.html",
        {
            "articles": articles,
            "draft_count": articles.filter(status="draft").count(),
            "pending_count": articles.filter(status="pending").count(),
            "published_count": articles.filter(status="published").count(),
        },
    )


@login_required
def editor_dashboard(request):
    """Display the editor dashboard."""
    profile = _get_or_create_profile(request.user)
    if not profile.is_editor():
        return HttpResponseForbidden("You don't have permission.")

    pending_articles = Article.objects.filter(status="pending").select_related(
        "author", "category", "publisher"
    )
    managed_articles = Article.objects.select_related(
        "author", "category", "publisher", "reviewed_by"
    )
    publishers = Publisher.objects.select_related("created_by")
    return render(
        request,
        "news/dashboard/editor.html",
        {
            "pending_articles": pending_articles,
            "managed_articles": managed_articles,
            "publishers": publishers,
        },
    )


@login_required
def create_publisher(request):
    """Allow editors to create publishers."""
    profile = _get_or_create_profile(request.user)
    if not profile.is_editor():
        return HttpResponseForbidden("Only editors can create publishers.")

    if request.method == "POST":
        form = PublisherForm(request.POST, request.FILES)
        if form.is_valid():
            publisher = form.save(commit=False)
            publisher.created_by = request.user
            publisher.save()
            messages.success(request, "Publisher created successfully!")
            return redirect("news:editor_dashboard")
        messages.error(request, "Please correct the errors below.")
    else:
        form = PublisherForm()

    return render(request, "news/publisher_form.html", {"form": form})


@login_required
def create_article(request):
    """Handle article creation."""
    profile = _get_or_create_profile(request.user)
    if not profile.is_journalist():
        return HttpResponseForbidden("Only journalists can create articles.")

    publishers = Publisher.objects.all()
    if not publishers.exists():
        messages.error(
            request,
            "No publishers are available yet. Ask an editor to create one.",
        )
        return redirect("news:journalist_dashboard")

    default_category = _get_default_category()
    if request.method == "POST":
        form = ArticleForm(
            request.POST,
            request.FILES,
            allowed_publishers=publishers,
        )
        if form.is_valid():
            article = form.save(commit=False)
            article.author = request.user
            article.category = article.category or default_category
            article.save()
            messages.success(request, "Article created successfully!")
            return redirect("news:journalist_dashboard")
        messages.error(request, "Please correct the errors below.")
    else:
        form = ArticleForm(
            allowed_publishers=publishers,
            initial={"category": default_category.pk},
        )

    return render(request, "news/article_form.html", {"form": form})


@login_required
def edit_article(request, pk):
    """Handle article editing."""
    article = get_object_or_404(Article, pk=pk)
    profile = _get_or_create_profile(request.user)

    if profile.is_editor():
        redirect_name = "news:editor_dashboard"
    elif (
        profile.is_journalist()
        and article.author == request.user
        and article.status in ["draft", "rejected"]
    ):
        redirect_name = "news:journalist_dashboard"
    else:
        return HttpResponseForbidden("You don't have permission.")

    publishers = Publisher.objects.all()
    if request.method == "POST":
        form = ArticleForm(
            request.POST,
            request.FILES,
            instance=article,
            allowed_publishers=publishers,
        )
        if form.is_valid():
            article = form.save(commit=False)
            article.category = article.category or _get_default_category()
            article.save()
            messages.success(request, "Article updated successfully!")
            return redirect(redirect_name)
        messages.error(request, "Please correct the errors below.")
    else:
        form = ArticleForm(instance=article, allowed_publishers=publishers)

    return render(request, "news/article_form.html", {"form": form, "article": article})


@login_required
@require_POST
def delete_article(request, pk):
    """Allow editors to delete an article."""
    profile = _get_or_create_profile(request.user)
    if not profile.is_editor():
        return HttpResponseForbidden("Only editors can delete articles.")

    article = get_object_or_404(Article, pk=pk)
    article.delete()
    messages.success(request, "Article deleted successfully.")
    return redirect("news:editor_dashboard")


@login_required
@require_POST
def submit_article(request, pk):
    """Submit an article for review."""
    article = get_object_or_404(Article, pk=pk)
    profile = _get_or_create_profile(request.user)
    if not profile.is_journalist() or article.author != request.user:
        return HttpResponseForbidden("You can only submit your own articles.")

    article.submit_for_review()
    messages.success(request, "Article submitted for review!")
    return redirect("news:journalist_dashboard")


@login_required
def approve_article(request, pk):
    """Approve an article for publication."""
    profile = _get_or_create_profile(request.user)
    if not profile.is_editor():
        return HttpResponseForbidden("Only editors can approve articles.")

    article = get_object_or_404(Article, pk=pk, status="pending")
    if request.method == "POST":
        article.approve(request.user)
        messages.success(request, f'Article "{article.title}" approved!')
        return redirect("news:editor_dashboard")

    return render(request, "news/approve_article.html", {"article": article})


@login_required
def reject_article(request, pk):
    """Reject an article."""
    profile = _get_or_create_profile(request.user)
    if not profile.is_editor():
        return HttpResponseForbidden("Only editors can reject articles.")

    article = get_object_or_404(Article, pk=pk, status="pending")
    if request.method == "POST":
        reason = request.POST.get("reason", "")
        article.reject(request.user, reason)
        messages.warning(request, f'Article "{article.title}" rejected.')
        return redirect("news:editor_dashboard")

    return render(request, "news/approve_article.html", {"article": article})


def publisher_list(request):
    """Display list of all publishers."""
    publishers = Publisher.objects.all()
    return render(request, "news/publisher_list.html", {"publishers": publishers})


def publisher_detail(request, slug):
    """Display a single publisher's page."""
    publisher = get_object_or_404(Publisher, slug=slug)
    articles = publisher.articles.filter(status="published").select_related(
        "author", "category"
    )
    can_subscribe = False
    is_subscribed = False

    if request.user.is_authenticated:
        profile = _get_or_create_profile(request.user)
        can_subscribe = profile.is_reader()
        if can_subscribe:
            is_subscribed = Subscription.objects.filter(
                user=request.user, publisher=publisher
            ).exists()

    return render(
        request,
        "news/publisher_detail.html",
        {
            "publisher": publisher,
            "articles": articles,
            "can_subscribe": can_subscribe,
            "is_subscribed": is_subscribed,
        },
    )


def journalist_detail(request, username):
    """Display a journalist profile and published articles."""
    journalist = get_object_or_404(
        User.objects.select_related("profile"),
        username=username,
        profile__role=UserProfile.ROLE_JOURNALIST,
    )
    articles = journalist.articles.filter(status="published").select_related(
        "publisher", "category"
    )
    can_subscribe = False
    is_subscribed = False

    if request.user.is_authenticated:
        profile = _get_or_create_profile(request.user)
        can_subscribe = profile.is_reader()
        if can_subscribe:
            is_subscribed = Subscription.objects.filter(
                user=request.user, journalist=journalist
            ).exists()

    return render(
        request,
        "news/journalist_detail.html",
        {
            "journalist": journalist,
            "articles": articles,
            "can_subscribe": can_subscribe,
            "is_subscribed": is_subscribed,
        },
    )


@login_required
@require_POST
def subscribe_publisher(request, slug):
    """Subscribe to a publisher."""
    publisher = get_object_or_404(Publisher, slug=slug)
    profile = _get_or_create_profile(request.user)
    if not profile.is_reader():
        return HttpResponseForbidden("Only readers can subscribe.")

    try:
        Subscription.objects.get_or_create(user=request.user, publisher=publisher)
        messages.success(request, f"Subscribed to {publisher.name}!")
    except ValidationError as exc:
        messages.error(request, str(exc))
    return redirect("news:publisher_detail", slug=slug)


@login_required
@require_POST
def unsubscribe_publisher(request, slug):
    """Unsubscribe from a publisher."""
    publisher = get_object_or_404(Publisher, slug=slug)
    profile = _get_or_create_profile(request.user)
    if not profile.is_reader():
        return HttpResponseForbidden("Only readers can unsubscribe.")

    Subscription.objects.filter(user=request.user, publisher=publisher).delete()
    messages.success(request, f"Unsubscribed from {publisher.name}.")
    return redirect("news:publisher_detail", slug=slug)


@login_required
@require_POST
def subscribe_journalist(request, username):
    """Subscribe to a journalist."""
    journalist = get_object_or_404(
        User.objects.select_related("profile"),
        username=username,
        profile__role=UserProfile.ROLE_JOURNALIST,
    )
    profile = _get_or_create_profile(request.user)
    if not profile.is_reader():
        return HttpResponseForbidden("Only readers can subscribe.")

    try:
        Subscription.objects.get_or_create(user=request.user, journalist=journalist)
        messages.success(request, f"Subscribed to {journalist.username}!")
    except ValidationError as exc:
        messages.error(request, str(exc))
    return redirect("news:journalist_detail", username=username)


@login_required
@require_POST
def unsubscribe_journalist(request, username):
    """Unsubscribe from a journalist."""
    journalist = get_object_or_404(
        User.objects.select_related("profile"),
        username=username,
        profile__role=UserProfile.ROLE_JOURNALIST,
    )
    profile = _get_or_create_profile(request.user)
    if not profile.is_reader():
        return HttpResponseForbidden("Only readers can unsubscribe.")

    Subscription.objects.filter(user=request.user, journalist=journalist).delete()
    messages.success(request, f"Unsubscribed from {journalist.username}.")
    return redirect("news:journalist_detail", username=username)


@login_required
def subscriptions(request):
    """Display a reader's subscriptions."""
    profile = _get_or_create_profile(request.user)
    if not profile.is_reader():
        return HttpResponseForbidden("Only readers can view subscriptions.")

    subscription_list = request.user.subscriptions.select_related(
        "publisher", "journalist"
    )
    return render(
        request,
        "news/subscriptions.html",
        {"subscriptions": subscription_list},
    )


@login_required
def dashboard(request):
    """Redirect to the appropriate dashboard based on the user's role."""
    profile = _get_or_create_profile(request.user)
    if profile.is_journalist():
        return redirect("news:journalist_dashboard")
    if profile.is_editor():
        return redirect("news:editor_dashboard")
    return redirect("news:reader_dashboard")
