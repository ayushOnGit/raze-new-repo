from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from razexOne.settings import DEBUG
from django.shortcuts import redirect
from django.db import connection


class HealthCheckView(APIView):
    """
    A health check endpoint that performs a simple '1 + 1 = 2' sum directly in the database.
    """

    def get(self, request):
        try:
            # Perform the simple sum query directly in the database
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 + 1 AS result")
                row = cursor.fetchone()

            # Check if the result is as expected
            if row and row[0] == 2:
                return Response(
                    {"status": "OK", "message": "Service is running", "1+1": row[0]},
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {
                        "status": "Error",
                        "message": "Unexpected result from database computation",
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        except Exception as e:
            return Response(
                {"status": "Error", "message": f"Health check failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class RootView(APIView):
    """
    This is the root endpoint, you can return general information or app status here.
    """

    def get(self, request):
        if DEBUG:
            # Redirect to API documentation.
            return redirect("/swagger/")
        else:
            # In future, redirect to homepage.
            return Response(
                {
                    "status": "ok",
                },
                status=status.HTTP_200_OK,
            )


def custom_404_handler(request, exception=None):
    return Response(
        {"detail": "Not Found"},
        status=status.HTTP_404_NOT_FOUND,
    )
