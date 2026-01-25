"""Admin API endpoints for live price updates and property management"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.shortcuts import get_object_or_404
from decimal import Decimal
from .models import RoomType, Hotel
from .serializers import RoomTypeSerializer


class AdminRoomTypeViewSet(viewsets.ModelViewSet):
    """Admin-only API for managing room types and live price updates"""
    queryset = RoomType.objects.all()
    serializer_class = RoomTypeSerializer
    permission_classes = [IsAdminUser]
    
    def partial_update(self, request, pk=None):
        """PATCH /api/admin/rooms/{id}/ - Update room base price"""
        room = get_object_or_404(RoomType, pk=pk)
        
        if 'base_price' in request.data:
            try:
                new_price = Decimal(str(request.data['base_price']))
                if new_price < 0:
                    return Response({'error': 'Price cannot be negative'}, status=status.HTTP_400_BAD_REQUEST)
                
                room.base_price = new_price
                room.save(update_fields=['base_price'])
                
                serializer = self.get_serializer(room)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except (ValueError, TypeError) as e:
                return Response({'error': 'Invalid price format'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Fall back to standard partial update
        return super().partial_update(request, pk=pk)
    
    @action(detail=True, methods=['post'])
    def update_price(self, request, pk=None):
        """POST /api/admin/rooms/{id}/update_price/ - Alternative endpoint for price updates"""
        room = get_object_or_404(RoomType, pk=pk)
        
        try:
            new_price = Decimal(str(request.data.get('base_price')))
            if new_price < 0:
                return Response({'error': 'Price cannot be negative'}, status=status.HTTP_400_BAD_REQUEST)
            
            room.base_price = new_price
            room.save(update_fields=['base_price'])
            
            return Response({
                'id': room.id,
                'name': room.name,
                'base_price': str(room.base_price),
                'effective_price': str(room.get_effective_price()),
            }, status=status.HTTP_200_OK)
        except (ValueError, TypeError, KeyError) as e:
            return Response({'error': 'Invalid price format'}, status=status.HTTP_400_BAD_REQUEST)
