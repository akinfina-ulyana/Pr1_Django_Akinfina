from django.urls import include, path


urlpatterns = [
    path("auth/", include("users.urls")),
    path("invitations/", include("invitations.urls")),
]
