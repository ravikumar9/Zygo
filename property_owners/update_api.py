"""
Owner update request APIs and admin approval endpoints.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.transaction import atomic
from django.shortcuts import get_object_or_404

from property_owners.models import (
    Property,
    PropertyRoomType,
    PropertyUpdateRequest,
    RoomUpdateRequest,
    PropertyOwner,
    AdminApprovalLog,
)


# -------------------- Owner Endpoints --------------------

@api_view(["POST"])
@permission_classes([IsAuthenticated])
@atomic
def create_update_request(request, property_id):
    """Owner submits an update request for a property or room."""
    prop = get_object_or_404(Property, id=property_id)
    owner_profile = get_object_or_404(PropertyOwner, user=request.user)
    if prop.owner != owner_profile:
        return Response({"error": "Not authorized for this property"}, status=status.HTTP_403_FORBIDDEN)

    change_type = request.data.get("change_type")
    owner_remark = request.data.get("owner_remark", "")
    room_id = request.data.get("room_id")
    new_data = request.data.get("new_data", {})

    # Snapshot old data
    old_data = {}
    room_obj = None
    if room_id:
        room_obj = get_object_or_404(PropertyRoomType, id=room_id, property=prop)
        old_data = {
            "base_price": str(room_obj.base_price),
            "discount_type": room_obj.discount_type,
            "discount_value": str(room_obj.discount_value),
            "amenities": room_obj.amenities,
            "meal_plans": room_obj.meal_plans,
            "room_size": room_obj.room_size,
            "number_of_beds": room_obj.number_of_beds,
            "max_occupancy": room_obj.max_occupancy,
            "total_rooms": room_obj.total_rooms,
        }
    else:
        old_data = {
            "property_rules": prop.property_rules,
            "amenities": prop.amenities,
            "base_price": str(prop.base_price) if prop.base_price else None,
            "gst_percentage": prop.gst_percentage,
        }

    title = request.data.get("title") or f"Update {change_type}" if change_type else "Update Request"
    description = request.data.get("description", owner_remark or "Owner submitted update")

    update_req = PropertyUpdateRequest.objects.create(
        owner=owner_profile,
        property=prop,
        room_type=room_obj,
        change_type=change_type or "rules",
        owner_remark=owner_remark,
        title=title,
        description=description,
        old_data=old_data,
        new_data=new_data,
    )

    return Response({
        "id": update_req.id,
        "status": update_req.status,
        "old_data": update_req.old_data,
        "new_data": update_req.new_data,
    }, status=status.HTTP_201_CREATED)


# -------------------- Admin Endpoints --------------------

def _is_property_admin(user):
    if user.is_superuser:
        return True
    groups = set(user.groups.values_list("name", flat=True))
    return "PROPERTY ADMIN" in groups or "SUPER ADMIN" in groups


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_list_update_requests(request):
    if not _is_property_admin(request.user):
        return Response({"error": "Admin access required"}, status=status.HTTP_403_FORBIDDEN)
    status_filter = request.query_params.get("status", "pending")
    qs = PropertyUpdateRequest.objects.all()
    if status_filter in ["pending", "approved", "rejected"]:
        qs = qs.filter(status=status_filter)
    data = []
    for item in qs.order_by("-created_at")[:200]:
        data.append({
            "id": item.id,
            "property_id": item.property_id,
            "room_type_id": item.room_type_id,
            "change_type": item.change_type,
            "status": item.status,
            "old_data": item.old_data,
            "new_data": item.new_data,
            "owner_remark": item.owner_remark,
            "title": item.title,
        })
    return Response({"results": data})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@atomic
def admin_approve_update_request(request, request_id):
    if not _is_property_admin(request.user):
        return Response({"error": "Admin access required"}, status=status.HTTP_403_FORBIDDEN)
    update_req = get_object_or_404(PropertyUpdateRequest, id=request_id)
    admin_remark = request.data.get("admin_remark", "")
    update_req.admin_remark = admin_remark
    update_req.approve(request.user)
    AdminApprovalLog.objects.create(
        admin=request.user,
        approval_type="update_request",
        subject=f"{update_req.owner.business_name} - {update_req.change_type}",
        details={"request_id": update_req.id, "change_type": update_req.change_type},
        decision="approved",
        reason=admin_remark,
    )
    return Response({"status": "approved", "id": update_req.id})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@atomic
def admin_reject_update_request(request, request_id):
    if not _is_property_admin(request.user):
        return Response({"error": "Admin access required"}, status=status.HTTP_403_FORBIDDEN)
    update_req = get_object_or_404(PropertyUpdateRequest, id=request_id)
    admin_remark = request.data.get("admin_remark", "")
    update_req.admin_remark = admin_remark
    update_req.reject(request.user, admin_remark)
    AdminApprovalLog.objects.create(
        admin=request.user,
        approval_type="update_request",
        subject=f"{update_req.owner.business_name} - {update_req.change_type}",
        details={"request_id": update_req.id, "change_type": update_req.change_type},
        decision="rejected",
        reason=admin_remark,
    )
    return Response({"status": "rejected", "id": update_req.id})
