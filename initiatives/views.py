import io
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DetailView, View
from django.urls import reverse_lazy, reverse
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.db.models import Sum, Count, F, ExpressionWrapper, FloatField, Q
from django.db.models.functions import TruncMonth, Coalesce
import json
from .models import Initiative, RealizedBenefit, WebhookAuditLog, AuditLog
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from datetime import datetime
import pandas as pd
import csv

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')

def log_audit(request, action, obj_type, obj_name, source='Portal', details=None):
    user = request.user.username if hasattr(request, 'user') and request.user.is_authenticated else "AnonymousUser"
    AuditLog.objects.create(
        action=action,
        object_type=obj_type,
        object_name=obj_name,
        user=user,
        ip_address=get_client_ip(request),
        source=source,
        details=details or {}
    )

class DashboardView(View):
    def get(self, request):
        initiatives = Initiative.objects.all()
        
        # Helper for common annotations
        prod_gain_expr = Coalesce(Sum(
            F('realized_benefits__kpi_value') * 
            F('multiplier_minutes') * 
            F('multiplier_dollars'),
            output_field=FloatField()
        ), 0.0)
        
        rev_impact_expr = Coalesce(Sum('realized_benefits__revenue_impact'), 0.0)

        # 1. Functional View (Department)
        dept_stats = list(initiatives.values('department').annotate(
            count=Count('id', distinct=True),
            prod_gain=prod_gain_expr,
            rev_impact=rev_impact_expr
        ).order_by('department'))

        # 2. Status View
        status_stats = list(initiatives.values('status').annotate(
            count=Count('id', distinct=True),
            prod_gain=prod_gain_expr,
            rev_impact=rev_impact_expr
        ).order_by('status'))

        # 3. Technology View
        tech_stats = list(initiatives.values('technology').annotate(
            count=Count('id', distinct=True),
            prod_gain=prod_gain_expr,
            rev_impact=rev_impact_expr
        ).order_by('technology'))
        
        # High-level Totals
        total_productivity = RealizedBenefit.objects.filter(
            initiative__benefit_name='Productivity Gain'
        ).aggregate(
            total=Sum(F('kpi_value') * F('initiative__multiplier_minutes') * F('initiative__multiplier_dollars'))
        )['total'] or 0
        
        total_revenue = RealizedBenefit.objects.filter(
            initiative__benefit_name='New Business'
        ).aggregate(Sum('revenue_impact'))['revenue_impact__sum'] or 0

        # Shared Color Palette for UI Consistency
        COLORS = [
            '#4285F4', # Google Blue
            '#34A853', # Google Green
            '#FBBC05', # Google Yellow
            '#EA4335', # Google Red
            '#8F00FF', # Purple
            '#00C7BE', # Teal
            '#FF9500', # Orange
            '#5856D6', # Indigo
            '#AF52DE', # Pink
            '#5AC8FA'  # Sky
        ]
        
        # Attach colors to stats for template use
        for i, item in enumerate(dept_stats):
            item['color'] = COLORS[i % len(COLORS)]
        for i, item in enumerate(status_stats):
            item['color'] = COLORS[i % len(COLORS)]
        for i, item in enumerate(tech_stats):
            item['color'] = COLORS[i % len(COLORS)]
        
        context = {
            'total_initiatives': initiatives.count(),
            'total_productivity': total_productivity,
            'total_revenue': total_revenue,
            'total_overall': float(total_productivity) + float(total_revenue),
            'live_systems': initiatives.filter(status='Live').count(),
            'dept_stats': dept_stats,
            'status_stats': status_stats,
            'tech_stats': tech_stats,
            'dept_data': {'labels': [i['department'] for i in dept_stats], 'counts': [i['count'] for i in dept_stats]},
            'status_data': {'labels': [i['status'] for i in status_stats], 'counts': [i['count'] for i in status_stats]},
            'tech_data': {'labels': [i['technology'] for i in tech_stats], 'counts': [i['count'] for i in tech_stats]},
            'COLORS': COLORS,
        }
        return render(request, 'initiatives/dashboard.html', context)

class BenefitAnalysisView(View):
    def get(self, request):
        # 1. Monthly Data for Stacked Bar Chart
        monthly_stats = RealizedBenefit.objects.annotate(
            month_trunc=TruncMonth('month')
        ).values('month_trunc').annotate(
            prod_gain=Coalesce(Sum(F('kpi_value') * F('initiative__multiplier_minutes') * F('initiative__multiplier_dollars')), 0.0),
            rev_impact=Coalesce(Sum('revenue_impact'), 0.0)
        ).order_by('month_trunc')

        labels = [stat['month_trunc'].strftime('%b %Y') for stat in monthly_stats]
        prod_data = [float(stat['prod_gain']) for stat in monthly_stats]
        rev_data = [float(stat['rev_impact']) for stat in monthly_stats]

        # 2. Tabular Data - Group by Initiative
        initiative_stats = RealizedBenefit.objects.values(
            'initiative__name', 
            'initiative__department'
        ).annotate(
            prod_gain=Coalesce(Sum(F('kpi_value') * F('initiative__multiplier_minutes') * F('initiative__multiplier_dollars')), 0.0),
            rev_impact=Coalesce(Sum('revenue_impact'), 0.0)
        ).annotate(
            total_impact=F('prod_gain') + F('rev_impact')
        )

        # Dynamic sorting based on parameter
        sort_by = request.GET.get('sort', 'total')
        if sort_by == 'prod':
            initiative_stats = initiative_stats.order_by('-prod_gain')
        elif sort_by == 'rev':
            initiative_stats = initiative_stats.order_by('-rev_impact')
        else:
            initiative_stats = initiative_stats.order_by('-total_impact')

        context = {
            'chart_data': {
                'labels': labels,
                'prod_data': prod_data,
                'rev_data': rev_data,
            },
            'table_by_month': monthly_stats,
            'table_by_initiative': list(initiative_stats),
            'active_tab': request.GET.get('tab', 'month'),
        }
        return render(request, 'initiatives/benefit_analysis.html', context)



from django.db.models.functions import Coalesce

class InitiativeListView(ListView):
    model = Initiative
    context_object_name = 'initiatives'
    template_name = 'initiatives/initiative_list.html'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Annotate with calculated benefits
        queryset = queryset.annotate(
            total_productivity=Coalesce(Sum(
                F('realized_benefits__kpi_value') * 
                F('multiplier_minutes') * 
                F('multiplier_dollars'),
                output_field=FloatField()
            ), 0.0),
            total_revenue=Coalesce(Sum(
                'realized_benefits__revenue_impact',
                output_field=FloatField()
            ), 0.0)
        )
        
        # Search filter
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(department__icontains=query) |
                Q(status__icontains=query) |
                Q(technology__icontains=query) |
                Q(benefit_name__icontains=query)
            )
            
        # Department filter
        dept = self.request.GET.get('department')
        if dept:
            queryset = queryset.filter(department=dept)
            
        # Status filter
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
            
        # Technology filter
        tech = self.request.GET.get('technology')
        if tech:
            queryset = queryset.filter(technology=tech)
            
        # Sorting
        sort = self.request.GET.get('sort')
        if sort == 'name':
            queryset = queryset.order_by('name')
        elif sort == '-name':
            queryset = queryset.order_by('-name')
        elif sort == 'dept':
            queryset = queryset.order_by('department')
        elif sort == '-dept':
            queryset = queryset.order_by('-department')
        else:
            queryset = queryset.order_by('-created_at') # Default sort
            
        return queryset

class InitiativeCreateView(CreateView):
    model = Initiative
    fields = '__all__'
    template_name = 'initiatives/initiative_form.html'
    success_url = reverse_lazy('initiative_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        log_audit(self.request, 'Create', 'Initiative', self.object.name)
        return response

class InitiativeUpdateView(UpdateView):
    model = Initiative
    fields = '__all__'
    template_name = 'initiatives/initiative_form.html'
    success_url = reverse_lazy('initiative_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        log_audit(self.request, 'Update', 'Initiative', self.object.name)
        return response

class InitiativeDeleteView(View):
    def post(self, request, pk):
        initiative = get_object_or_404(Initiative, pk=pk)
        name = initiative.name
        initiative.delete()
        log_audit(request, 'Delete', 'Initiative', name)
        messages.success(request, "Initiative deleted successfully.")
        return redirect('initiative_list')

class RealizedBenefitEntryView(View):
    def get(self, request, pk):
        initiative = get_object_or_404(Initiative, pk=pk)
        log_audit(request, 'View', 'Initiative', f"{initiative.name} (Benefit Entry)")
        history = RealizedBenefit.objects.filter(initiative=initiative).order_by('-month')[:12]
        return render(request, 'initiatives/benefit_entry.html', {
            'initiative': initiative,
            'history': history,
        })

    def post(self, request, pk):
        initiative = get_object_or_404(Initiative, pk=pk)
        month_str = request.POST.get('month')
        kpi_value = float(request.POST.get('kpi_value') or 0)
        revenue_impact = float(request.POST.get('revenue_impact') or 0)
        
        month = datetime.strptime(month_str, '%Y-%m').date()
        
        benefit, created = RealizedBenefit.objects.update_or_create(
            initiative=initiative,
            month=month,
            defaults={
                'kpi_value': kpi_value,
                'revenue_impact': revenue_impact
            }
        )
        
        action = 'Create' if created else 'Update'
        log_audit(request, action, 'Benefit', f"Benefit for {initiative.name} ({month_str})")
        
        messages.success(request, "Monthly tracking updated.")
        return redirect('benefit_entry', pk=pk)

class RealizedBenefitDeleteView(View):
    def post(self, request, pk):
        benefit = get_object_or_404(RealizedBenefit, pk=pk)
        initiative_pk = benefit.initiative.pk
        name = f"Benefit for {benefit.initiative.name} ({benefit.month})"
        benefit.delete()
        log_audit(request, 'Delete', 'Benefit', name)
        messages.success(request, "Entry deleted.")
        return redirect('benefit_entry', pk=initiative_pk)

class CSVDownloadView(View):
    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="initiatives_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Initiative Name', 'Requester Name', 'LOB Owner', 'Description', 'IT Owner', 
            'IT Owner Email', 'Department', 'Status', 'Technology', 'Value', 
            'Benefit Name', 'KPI Name', 'Multiplier Minutes', 'Multiplier Dollars'
        ])
        
        for initiative in Initiative.objects.all():
            writer.writerow([
                initiative.name, initiative.requester_name, initiative.lob_owner, initiative.description, 
                initiative.it_owner, initiative.it_owner_email, initiative.department, initiative.status, 
                initiative.technology, initiative.value, initiative.benefit_name,
                initiative.kpi_name, initiative.multiplier_minutes, initiative.multiplier_dollars
            ])
            
        log_audit(request, 'Export', 'Initiative', 'Full System Export', details={'count': Initiative.objects.count()})
        return response

class CSVUploadView(View):
    def post(self, request):
        csv_file = request.FILES.get('csv_file')
        if not csv_file:
            messages.error(request, "No file uploaded.")
            return redirect('initiative_list')
        
        decoded_file = csv_file.read().decode('utf-8')
        io_string = io.StringIO(decoded_file)
        next(io_string) # Skip header
        
        count = 0
        for column in csv.reader(io_string, delimiter=',', quotechar='"'):
            if len(column) < 14:
                continue

            Initiative.objects.update_or_create(
                name=column[0],
                defaults={
                    'requester_name': column[1],
                    'lob_owner': column[2],
                    'description': column[3],
                    'it_owner': column[4],
                    'it_owner_email': column[5],
                    'department': column[6],
                    'status': column[7],
                    'technology': column[8],
                    'value': column[9],
                    'benefit_name': column[10],
                    'kpi_name': column[11],
                    'multiplier_minutes': float(column[12] or 0),
                }
            )
            count += 1
            
        log_audit(request, 'Import', 'Initiative', 'Bulk CSV Data Upload', details={'imported_rows': count})
        messages.success(request, f"CSV imported successfully ({count} initiatives).")
        return redirect('initiative_list')

class SampleCSVDownloadView(View):
    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="sample_initiatives.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Initiative Name', 'Requester Name', 'LOB Owner', 'Description', 'IT Owner', 
            'IT Owner Email', 'Department', 'Status', 'Technology', 'Value', 
            'Benefit Name', 'KPI Name', 'Multiplier Minutes', 'Multiplier Dollars'
        ])
        writer.writerow([
            'Customer Support Chatbot', 'John Doe', 'Claims', 'AI Chatbot for customer support', 'IT Team',
            'it-claims@example.com', 'Claims', 'In-progress', 'OpenAI GPT-4', 'Reduce response time by 50%',
            'Productivity Gain', 'Calls Handled', '5.0', '25.0'
        ])
        
        log_audit(request, 'Export', 'Initiative', 'Sample Template Format')
        return response
@method_decorator(csrf_exempt, name='dispatch')
class RealtimeReportingWebhookView(View):
    def post(self, request):
        ip = request.META.get('REMOTE_ADDR')
        payload = {}
        initiative = None
        
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            log = WebhookAuditLog.objects.create(
                status_code=400,
                payload={'raw_body': request.body.decode('utf-8', errors='replace')},
                error_message="Invalid JSON payload",
                ip_address=ip
            )
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        # Extraction logic
        webhook_key = payload.get('webhook_key')
        kpi_value = payload.get('kpi_value')
        revenue_impact = payload.get('revenue_impact')
        month_str = payload.get('month') # Optional, defaults to current month

        if not webhook_key:
            WebhookAuditLog.objects.create(
                status_code=401,
                payload=payload,
                error_message="Missing webhook_key",
                ip_address=ip
            )
            return JsonResponse({'error': 'Missing webhook_key'}, status=401)

        initiative = Initiative.objects.filter(webhook_key=webhook_key).first()
        if not initiative:
            WebhookAuditLog.objects.create(
                status_code=403,
                payload=payload,
                error_message=f"Invalid webhook_key: {webhook_key}",
                ip_address=ip
            )
            return JsonResponse({'error': 'Invalid webhook_key'}, status=403)

        # Date handling
        try:
            if month_str:
                month = datetime.strptime(month_str, '%Y-%m').date()
            else:
                month = datetime.now().replace(day=1).date()
        except ValueError:
            WebhookAuditLog.objects.create(
                initiative=initiative,
                status_code=400,
                payload=payload,
                error_message=f"Invalid date format: {month_str}. Use YYYY-MM",
                ip_address=ip
            )
            return JsonResponse({'error': 'Invalid month format. Use YYYY-MM'}, status=400)

        # Valid payload processing
        try:
            benefit, created = RealizedBenefit.objects.update_or_create(
                initiative=initiative,
                month=month,
                defaults={
                    'kpi_value': float(kpi_value or 0),
                    'revenue_impact': float(revenue_impact or 0)
                }
            )
            
            WebhookAuditLog.objects.create(
                initiative=initiative,
                status_code=200,
                payload=payload,
                response_body={'success': True, 'initiative': initiative.name, 'month': str(month)},
                ip_address=ip
            )
            
            action = 'Create' if created else 'Update'
            log_audit(request, action, 'Benefit', f"Benefit for {initiative.name} ({month_str})", source='API')

            return JsonResponse({'success': True, 'message': 'Benefit reported successfully'})
        
        except Exception as e:
            WebhookAuditLog.objects.create(
                initiative=initiative,
                status_code=500,
                payload=payload,
                error_message=str(e),
                ip_address=ip
            )
            return JsonResponse({'error': 'Internal server error'}, status=500)

class WebhookDocsView(View):
    def get(self, request, pk=None):
        initiative = None
        if pk:
            initiative = get_object_or_404(Initiative, pk=pk)
            # Generate the webhook_key dynamically if it hasn't been set yet
            if not initiative.webhook_key:
                initiative.save()
        
        base_url = request.build_absolute_uri('/')[:-1]
        webhook_url = base_url + reverse('webhook_report')
        
        context = {
            'initiative': initiative,
            'webhook_url': webhook_url,
            'base_url': base_url
        }
        return render(request, 'initiatives/webhook_docs.html', context)

class AuditLogListView(ListView):
    model = AuditLog
    template_name = 'initiatives/audit_list.html'
    context_object_name = 'audit_logs'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Simple search filtering
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(action__icontains=query) |
                Q(object_type__icontains=query) |
                Q(object_name__icontains=query) |
                Q(user__icontains=query) |
                Q(source__icontains=query)
            )
            
        return queryset
