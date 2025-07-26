from django.urls import include, path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from .settings import DEBUG
from django.http import JsonResponse
from django.contrib import admin
from base.models import User

schema_view = get_schema_view(
    openapi.Info(
        title="RazexOne API",
        default_version="v1",
        description="API documentation for RazexOne",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

def health_check(request):
    return JsonResponse({"message": "Hello, server is running!"})

urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/health/", health_check),
    path("api/", include("base.urls")),
    path("api/", include("booking.urls")),
]

handler404 = "base.views.custom_404_handler"

if DEBUG:
    urlpatterns += [
        path("swagger/", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
        path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
    ]