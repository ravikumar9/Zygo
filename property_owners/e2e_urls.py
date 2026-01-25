from django.urls import path

from . import e2e_views

app_name = "owner_e2e"

urlpatterns = [
    path("dashboard/", e2e_views.owner_dashboard, name="owner-dashboard"),
    path("properties/create/", e2e_views.owner_property_create, name="owner-property-create"),
    path("properties/<int:property_id>/", e2e_views.owner_property_detail, name="owner-property-detail"),
    path(
        "properties/<int:property_id>/rooms/create/",
        e2e_views.owner_room_create,
        name="owner-room-create",
    ),
    path(
        "properties/<int:property_id>/meal-plans/",
        e2e_views.owner_meal_plans,
        name="owner-meal-plans",
    ),
    path(
        "properties/<int:property_id>/submit/",
        e2e_views.owner_submit_for_approval,
        name="owner-submit",
    ),
]
