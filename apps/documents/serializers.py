from rest_framework import serializers


class AutorizacionToggleSerializer(serializers.Serializer):
    idProfesional = serializers.IntegerField()
