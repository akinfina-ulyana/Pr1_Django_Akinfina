from django.urls import include, path


urlpatterns = [
    path("auth/", include("users.urls")),
    path("invitations/", include("invitations.urls")),
    path("cars/", include("cars.urls")),
    path("suppliers/", include("suppliers.urls")),
    path("buyers/", include("buyers.urls")),
    path("dealership/", include("dealership.urls")),
]
