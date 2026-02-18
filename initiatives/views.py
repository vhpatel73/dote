import io
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DetailView, View
from django.urls import reverse_lazy, reverse
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.db.models import Sum, Count, F, ExpressionWrapper, FloatField, Q
from django.db.models.functions import TruncMonth, Coalesce
import json
from .models import Initiative, RealizedBenefit
from datetime import datetime
import pandas as pd
import csv

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

class InitiativeUpdateView(UpdateView):
    model = Initiative
    fields = '__all__'
    template_name = 'initiatives/initiative_form.html'
    success_url = reverse_lazy('initiative_list')

class InitiativeDeleteView(View):
    def post(self, request, pk):
        initiative = get_object_or_404(Initiative, pk=pk)
        initiative.delete()
        messages.success(request, "Initiative deleted successfully.")
        return redirect('initiative_list')

class RealizedBenefitEntryView(View):
    def get(self, request, pk):
        initiative = get_object_or_404(Initiative, pk=pk)
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
        
        RealizedBenefit.objects.update_or_create(
            initiative=initiative,
            month=month,
            defaults={
                'kpi_value': kpi_value,
                'revenue_impact': revenue_impact
            }
        )
        
        messages.success(request, "Monthly tracking updated.")
        return redirect('benefit_entry', pk=pk)

class RealizedBenefitDeleteView(View):
    def post(self, request, pk):
        benefit = get_object_or_404(RealizedBenefit, pk=pk)
        initiative_pk = benefit.initiative.pk
        benefit.delete()
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
                    'multiplier_dollars': float(column[13] or 0)
                }
            )
            
        messages.success(request, "CSV imported successfully.")
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
        return response
