from rest_framework import serializers
from .models import Package, PackageImage, PackageItinerary, PackageDeparture


class PackageImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PackageImage
        fields = ['id', 'image', 'caption', 'is_primary']


class PackageItinerarySerializer(serializers.ModelSerializer):
    class Meta:
        model = PackageItinerary
        fields = ['id', 'day_number', 'title', 'description', 'activities', 'meals_included', 'accommodation']


class PackageDepartureSerializer(serializers.ModelSerializer):
    class Meta:
        model = PackageDeparture
        fields = ['id', 'departure_date', 'return_date', 'available_slots', 'price_per_person', 'is_active']


class PackageListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Package
        fields = [
            'id', 'name', 'package_type', 'duration_days', 'duration_nights',
            'starting_price', 'image', 'is_featured', 'rating', 'review_count', 'itinerary_text'
        ]


class PackageDetailSerializer(serializers.ModelSerializer):
    images = PackageImageSerializer(many=True, read_only=True)
    itinerary = PackageItinerarySerializer(many=True, read_only=True)
    departures = PackageDepartureSerializer(many=True, read_only=True)
    destination_city_names = serializers.SerializerMethodField()
    
    class Meta:
        model = Package
        fields = [
            'id', 'name', 'description', 'package_type', 'destination_cities',
            'destination_city_names', 'duration_days', 'duration_nights',
            'starting_price', 'image', 'images', 'includes_hotel',
            'includes_transport', 'includes_meals', 'includes_sightseeing',
            'includes_guide', 'breakfast_included', 'lunch_included',
            'dinner_included', 'max_group_size', 'min_group_size',
            'is_featured', 'rating', 'review_count', 'itinerary_text', 'itinerary', 'departures'
        ]
    
    def get_destination_city_names(self, obj):
        return [city.name for city in obj.destination_cities.all()]
