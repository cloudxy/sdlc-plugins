from django.http import HttpResponse

from .export import build_csv


def export_orders(request):
    filename = f"订单导出-{request.GET.get('date', 'all')}.csv"
    response = HttpResponse(build_csv(request.user, request.GET), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
