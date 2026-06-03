from django.urls import path

from .views import InvitationCreateView


urlpatterns = [
    path("", InvitationCreateView.as_view()),
]
