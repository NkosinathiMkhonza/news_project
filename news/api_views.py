"""API Views for the News Application."""

from django.core.exceptions import ValidationError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Article, Category, Publisher, Subscription, UserProfile
from .serializers import (
    ArticleDetailSerializer,
    ArticleListSerializer,
    CategorySerializer,
    CommentSerializer,
    PublisherSerializer,
    SubscriptionSerializer,
)


@api_view(["GET"])
@permission_classes([AllowAny])
def article_list_api(request):
    """API endpoint to list all published articles."""
    articles = Article.objects.filter(status="published")
    serializer = ArticleListSerializer(articles, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([AllowAny])
def article_detail_api(request, pk):
    """API endpoint to retrieve a single article."""
    try:
        article = Article.objects.get(pk=pk, status="published")
        serializer = ArticleDetailSerializer(article)
        return Response(serializer.data)
    except Article.DoesNotExist:
        return Response({"error": "Article not found"}, status=404)


@api_view(["GET"])
@permission_classes([AllowAny])
def category_list_api(request):
    """API endpoint to list all categories."""
    categories = Category.objects.all()
    serializer = CategorySerializer(categories, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([AllowAny])
def publisher_list_api(request):
    """API endpoint to list all publishers."""
    publishers = Publisher.objects.all()
    serializer = PublisherSerializer(publishers, many=True)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def comment_create_api(request):
    """API endpoint to create a comment."""
    profile, _ = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={"role": UserProfile.ROLE_READER},
    )
    if not profile.is_reader():
        return Response(
            {"error": "Only readers can comment on published articles."},
            status=403,
        )

    serializer = CommentSerializer(data=request.data)
    if serializer.is_valid():
        try:
            serializer.save(author=request.user)
        except ValidationError as exc:
            return Response({"error": exc.message_dict}, status=400)
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def subscription_list_api(request):
    """API endpoint to list user's subscriptions."""
    subscriptions = Subscription.objects.filter(user=request.user).select_related(
        "publisher", "journalist"
    )
    serializer = SubscriptionSerializer(subscriptions, many=True)
    return Response(serializer.data)
