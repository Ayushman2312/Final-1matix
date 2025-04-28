from rest_framework import serializers
from .models import *


class MeetingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meeting
        fields = '__all__'

class AgentUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentUser
        fields = '__all__'

