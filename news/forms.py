"""Forms for the News Application."""

from django import forms

from .models import Article, Comment, Publisher, UserProfile


class ArticleForm(forms.ModelForm):
    """Form for creating and editing articles."""

    def __init__(self, *args, allowed_publishers=None, **kwargs):
        """Make optional fields behave like the underlying model."""
        super().__init__(*args, **kwargs)
        self.fields["category"].required = False
        queryset = allowed_publishers or Publisher.objects.none()
        self.fields["publisher"].queryset = queryset.order_by("name")

    class Meta:
        model = Article
        fields = [
            "title",
            "slug",
            "content",
            "excerpt",
            "featured_image",
            "publisher",
            "category",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "slug": forms.TextInput(attrs={"class": "form-control"}),
            "content": forms.Textarea(attrs={"class": "form-control", "rows": 10}),
            "excerpt": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "publisher": forms.Select(attrs={"class": "form-select"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "featured_image": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }


class CommentForm(forms.ModelForm):
    """Form for adding comments."""

    class Meta:
        model = Comment
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class UserProfileForm(forms.ModelForm):
    """Form for editing user profile."""

    class Meta:
        model = UserProfile
        fields = ["bio", "avatar", "phone"]
        widgets = {
            "bio": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
        }


class PublisherForm(forms.ModelForm):
    """Form for editors to create publishers."""

    class Meta:
        model = Publisher
        fields = ["name", "slug", "description", "website", "logo"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "slug": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "website": forms.URLInput(attrs={"class": "form-control"}),
            "logo": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }
