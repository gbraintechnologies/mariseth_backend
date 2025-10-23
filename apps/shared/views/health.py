from django.http import HttpResponse

def health_check(request):
    """
    A simple health check endpoint that returns a 200 OK response.
    """
    return HttpResponse(status=200)