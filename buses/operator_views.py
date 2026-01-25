"""
Bus Operator Registration Views - Session 3
Registration workflow: DRAFT -> PENDING_VERIFICATION -> APPROVED/REJECTED
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.db import transaction
from .models import BusOperator
from .operator_forms import OperatorRegistrationForm


@login_required
def operator_create_draft(request):
    """Create or update operator registration draft"""
    # Get or create operator
    operator, created = BusOperator.objects.get_or_create(
        user=request.user,
        defaults={'approval_status': 'draft'}
    )
    
    # Only draft operators can edit
    if operator.approval_status != 'draft':
        messages.warning(request, "Only draft registrations can be edited. Contact admin if you need to change submitted data.")
        return redirect('buses:operator_detail', pk=operator.pk)
    
    if request.method == 'POST':
        form = OperatorRegistrationForm(request.POST, instance=operator)
        if form.is_valid():
            # Save to database
            with transaction.atomic():
                operator = form.save(commit=False)
                # Don't auto-submit - leave as DRAFT
                operator.save()
            
            messages.success(request, "Registration saved as draft. Complete all sections to submit for approval.")
            return redirect('buses:operator_detail', pk=operator.pk)
    else:
        form = OperatorRegistrationForm(instance=operator)
    
    # Calculate completion
    _, all_required = operator.has_required_fields()
    completion = operator.completion_percentage
    
    context = {
        'form': form,
        'operator': operator,
        'completion': completion,
        'page_title': 'Register as Bus Operator',
        'is_draft': True,
    }
    return render(request, 'buses/operator_form.html', context)


@login_required
def operator_submit(request, pk):
    """Submit draft registration for approval"""
    operator = get_object_or_404(BusOperator, pk=pk, user=request.user)
    
    # Only draft operators can submit
    if operator.approval_status != 'draft':
        messages.warning(request, "This registration has already been submitted.")
        return redirect('buses:operator_detail', pk=operator.pk)
    
    if request.method == 'POST':
        # Validate all required fields
        checks, has_all = operator.has_required_fields()
        if not has_all:
            missing = [k.replace('_', ' ').title() for k, v in checks.items() if not v]
            messages.error(request, f"Cannot submit. Incomplete sections: {', '.join(missing)}")
            return redirect('buses:operator_detail', pk=operator.pk)
        
        # Change status to PENDING_VERIFICATION
        with transaction.atomic():
            operator.approval_status = 'pending_verification'
            operator.submitted_at = timezone.now()
            operator.save()
        
        messages.success(request, "Registration submitted for admin approval. You'll receive an email when reviewed.")
        return redirect('buses:operator_detail', pk=operator.pk)
    
    # GET: Show confirmation page
    checks, has_all = operator.has_required_fields()
    context = {
        'operator': operator,
        'checks': checks,
        'completion': operator.completion_percentage,
        'can_submit': has_all,
    }
    return render(request, 'buses/operator_submit.html', context)


@login_required
def operator_detail(request, pk):
    """View operator registration status and details"""
    operator = get_object_or_404(BusOperator, pk=pk, user=request.user)
    
    checks, has_all = operator.has_required_fields()
    
    context = {
        'operator': operator,
        'completion': operator.completion_percentage,
        'checks': checks,
        'all_complete': has_all,
        'is_draft': operator.approval_status == 'draft',
        'is_pending': operator.approval_status == 'pending_verification',
        'is_approved': operator.approval_status == 'approved',
        'is_rejected': operator.approval_status == 'rejected',
    }
    return render(request, 'buses/operator_detail.html', context)


@login_required
def operator_dashboard(request):
    """Operator dashboard - show all registrations grouped by status"""
    try:
        operators = BusOperator.objects.filter(user=request.user)
    except BusOperator.DoesNotExist:
        operators = []
    
    # Group by status
    draft = operators.filter(approval_status='draft')
    pending = operators.filter(approval_status='pending_verification')
    approved = operators.filter(approval_status='approved')
    rejected = operators.filter(approval_status='rejected')
    
    # Sprint-1: Dashboard Metrics
    from datetime import timedelta
    from django.db.models import Sum, Count, Q
    from .models import BusSchedule, Bus
    
    metrics = {}
    if approved.exists():
        operator = approved.first()
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        # Get all buses for this operator
        operator_buses = Bus.objects.filter(operator=operator)
        
        # Schedules (trips) run in last 30 days
        trips_run = BusSchedule.objects.filter(
            bus__in=operator_buses,
            departure_date__gte=thirty_days_ago.date()
        ).count()
        
        # Total seats sold (30d)
        from bookings.models import BusBooking
        seats_sold = BusBooking.objects.filter(
            schedule__bus__in=operator_buses,
            booking__created_at__gte=thirty_days_ago
        ).count()  # Each BusBooking is one seat
        
        # Load factor (average occupancy %)
        total_schedules = BusSchedule.objects.filter(
            bus__in=operator_buses,
            departure_date__gte=thirty_days_ago.date()
        )
        
        if total_schedules.exists():
            total_capacity = sum([s.bus.total_seats for s in total_schedules])
            load_factor = round((seats_sold / total_capacity) * 100, 1) if total_capacity > 0 else 0
        else:
            load_factor = 0
        
        metrics = {
            'trips_run': trips_run,
            'seats_sold': seats_sold,
            'load_factor': load_factor,
        }
    
    context = {
        'draft_count': draft.count(),
        'pending_count': pending.count(),
        'approved_count': approved.count(),
        'rejected_count': rejected.count(),
        'operators': {
            'draft': draft,
            'pending': pending,
            'approved': approved,
            'rejected': rejected,
        },
        'metrics': metrics,
    }
    return render(request, 'buses/operator_dashboard.html', context)


@login_required
@require_http_methods(["GET"])
def operator_completion_json(request, pk):
    """JSON endpoint for completion percentage (AJAX)"""
    operator = get_object_or_404(BusOperator, pk=pk, user=request.user)
    checks, has_all = operator.has_required_fields()
    
    return JsonResponse({
        'completion': operator.completion_percentage,
        'checks': checks,
        'all_complete': has_all,
        'status': operator.get_approval_status_display(),
    })


from django.utils import timezone


# Sprint-1: Bulk CSV Schedule Import
@login_required
def upload_schedule_csv(request):
    """Upload CSV file for bulk schedule import"""
    from .models import BusScheduleImport
    
    try:
        operator = BusOperator.objects.get(user=request.user, approval_status='approved')
    except BusOperator.DoesNotExist:
        messages.error(request, "Only approved operators can import schedules")
        return redirect('buses:operator_dashboard')
    
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        
        # Basic validation
        if not csv_file.name.endswith('.csv'):
            messages.error(request, "Please upload a CSV file")
            return redirect('buses:upload_schedule_csv')
        
        # Create import record
        import_record = BusScheduleImport.objects.create(
            operator=operator,
            csv_file=csv_file,
            status='pending',
            uploaded_by=request.user
        )
        
        # Redirect to preview
        return redirect('buses:preview_schedule_import', import_id=import_record.id)
    
    # Show upload form
    recent_imports = BusScheduleImport.objects.filter(operator=operator)[:10]
    
    return render(request, 'buses/schedule_upload.html', {
        'operator': operator,
        'recent_imports': recent_imports
    })


@login_required
def preview_schedule_import(request, import_id):
    """Preview and validate CSV import"""
    from .models import BusScheduleImport, Bus, BusSchedule
    import csv
    import io
    from datetime import datetime, time
    from core.models import City
    
    import_record = get_object_or_404(
        BusScheduleImport,
        id=import_id,
        operator__user=request.user
    )
    
    # Validate CSV
    if import_record.status == 'pending':
        errors = []
        valid_rows = []
        row_num = 0
        
        try:
            csv_content = import_record.csv_file.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(csv_content))
            
            required_columns = ['bus_number', 'source_city', 'destination_city', 'departure_date', 'departure_time', 'arrival_time', 'fare']
            
            # Validate headers
            if not all(col in reader.fieldnames for col in required_columns):
                missing = [col for col in required_columns if col not in reader.fieldnames]
                errors.append({'row': 0, 'error': f'Missing columns: {", ".join(missing)}'})
                import_record.status = 'failed'
                import_record.validation_errors = errors
                import_record.save()
            else:
                for row in reader:
                    row_num += 1
                    row_errors = []
                    
                    # Validate bus exists
                    try:
                        bus = Bus.objects.get(bus_number=row['bus_number'], operator=import_record.operator)
                    except Bus.DoesNotExist:
                        row_errors.append(f"Bus {row['bus_number']} not found")
                        bus = None
                    
                    # Validate cities
                    try:
                        source = City.objects.get(name__iexact=row['source_city'])
                    except City.DoesNotExist:
                        row_errors.append(f"City {row['source_city']} not found")
                        source = None
                    
                    try:
                        destination = City.objects.get(name__iexact=row['destination_city'])
                    except City.DoesNotExist:
                        row_errors.append(f"City {row['destination_city']} not found")
                        destination = None
                    
                    # Validate dates and times
                    try:
                        departure_date = datetime.strptime(row['departure_date'], '%Y-%m-%d').date()
                    except:
                        row_errors.append(f"Invalid date format: {row['departure_date']}")
                        departure_date = None
                    
                    try:
                        departure_time = datetime.strptime(row['departure_time'], '%H:%M').time()
                    except:
                        row_errors.append(f"Invalid time format: {row['departure_time']}")
                        departure_time = None
                    
                    try:
                        arrival_time = datetime.strptime(row['arrival_time'], '%H:%M').time()
                    except:
                        row_errors.append(f"Invalid time format: {row['arrival_time']}")
                        arrival_time = None
                    
                    # Validate fare
                    try:
                        fare = float(row['fare'])
                        if fare <= 0:
                            row_errors.append("Fare must be positive")
                    except:
                        row_errors.append(f"Invalid fare: {row['fare']}")
                        fare = None
                    
                    # Check for overlapping schedules
                    if bus and departure_date and departure_time and not row_errors:
                        overlapping = BusSchedule.objects.filter(
                            bus=bus,
                            departure_date=departure_date,
                            departure_time=departure_time
                        ).exists()
                        if overlapping:
                            row_errors.append("Duplicate schedule exists")
                    
                    if row_errors:
                        errors.append({
                            'row': row_num,
                            'data': row,
                            'errors': row_errors
                        })
                    else:
                        valid_rows.append({
                            'row': row_num,
                            'bus': bus,
                            'source': source,
                            'destination': destination,
                            'departure_date': departure_date,
                            'departure_time': departure_time,
                            'arrival_time': arrival_time,
                            'fare': fare,
                            'data': row
                        })
                
                import_record.total_rows = row_num
                import_record.valid_rows = len(valid_rows)
                import_record.invalid_rows = len(errors)
                import_record.validation_errors = errors
                import_record.status = 'validated' if len(errors) == 0 else 'failed'
                import_record.save()
                
        except Exception as e:
            import_record.status = 'failed'
            import_record.error_message = str(e)
            import_record.save()
    
    return render(request, 'buses/schedule_preview.html', {
        'import_record': import_record,
        'can_import': import_record.status == 'validated'
    })


@login_required
def confirm_schedule_import(request, import_id):
    """Confirm and execute the import"""
    from .models import BusScheduleImport, BusSchedule
    import csv
    import io
    from datetime import datetime
    from core.models import City
    
    import_record = get_object_or_404(
        BusScheduleImport,
        id=import_id,
        operator__user=request.user,
        status='validated'
    )
    
    if request.method == 'POST':
        import_record.status = 'importing'
        import_record.save()
        
        try:
            csv_content = import_record.csv_file.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(csv_content))
            
            created_count = 0
            for row in reader:
                try:
                    from .models import Bus
                    bus = Bus.objects.get(bus_number=row['bus_number'], operator=import_record.operator)
                    source = City.objects.get(name__iexact=row['source_city'])
                    destination = City.objects.get(name__iexact=row['destination_city'])
                    departure_date = datetime.strptime(row['departure_date'], '%Y-%m-%d').date()
                    departure_time = datetime.strptime(row['departure_time'], '%H:%M').time()
                    arrival_time = datetime.strptime(row['arrival_time'], '%H:%M').time()
                    fare = float(row['fare'])
                    
                    # Create schedule
                    BusSchedule.objects.create(
                        bus=bus,
                        source_city=source,
                        destination_city=destination,
                        departure_date=departure_date,
                        departure_time=departure_time,
                        arrival_time=arrival_time,
                        fare=fare,
                        available_seats=bus.total_seats
                    )
                    created_count += 1
                except Exception as e:
                    continue
            
            import_record.status = 'completed'
            import_record.created_schedules = created_count
            import_record.save()
            
            messages.success(request, f"Successfully imported {created_count} schedules")
            return redirect('buses:operator_dashboard')
            
        except Exception as e:
            import_record.status = 'failed'
            import_record.error_message = str(e)
            import_record.save()
            messages.error(request, f"Import failed: {str(e)}")
    
    return redirect('buses:preview_schedule_import', import_id=import_id)
