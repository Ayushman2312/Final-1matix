from django.utils.deprecation import MiddlewareMixin
from .models import Device

class DeviceRecognitionMiddleware(MiddlewareMixin):
    def process_request(self, request):
        device_id = request.COOKIES.get('device_id')

        if device_id:
            try:
                device = Device.objects.get(device_id=device_id)
                request.device = device
            except Device.DoesNotExist:
                request.device = None
        else:
            request.device = None
