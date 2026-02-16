import csv
import io
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DetailView, View
from django.urls import reverse_lazy, reverse
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.db.models import Sum, Count
import json
from .models import Initiative, RealizedBenefit
from datetime import datetime
import pandas as pd

class DashboardView(View):
    def get(self, request):
        initiatives = Initiative.objects.all()
        
        # Aggregations
        dept_stats = list(initiatives.values('department').annotate(count=Count('id')).order_by('department'))
        status_stats = list(initiatives.values('status').annotate(count=Count('id')).order_by('status'))
        tech_stats = list(initiatives.values('technology').annotate(count=Count('id')).order_by('technology'))
        
        # Total realized benefit by Department
        benefit_by_dept = list(RealizedBenefit.objects.values('initiative__department')
                               .annotate(total=Sum('amount'), count=Count('initiative', distinct=True))
                               .order_by('initiative__department'))
        
        # Total overall benefit
        total_benefit = RealizedBenefit.objects.aggregate(Sum('amount'))['amount__sum'] or 0
        
        context = {
            'total_initiatives': initiatives.count(),
            'total_benefit': total_benefit,
            'dept_stats': dept_stats,
            'status_stats': status_stats,
            'tech_stats': tech_stats,
            'benefit_by_dept': benefit_by_dept,
            'dept_data': {'labels': [i['department'] for i in dept_stats], 'counts': [i['count'] for i in dept_stats]},
            'status_data': {'labels': [i['status'] for i in status_stats], 'counts': [i['count'] for i in status_stats]},
            'tech_data': {'labels': [i['technology'] for i in tech_stats], 'counts': [i['count'] for i in tech_stats]},
        }
        return render(request, 'initiatives/dashboard.html', context)

class InitiativeListView(ListView):
    model = Initiative
    context_object_name = 'initiatives'
    template_name = 'initiatives/initiative_list.html'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        dept = self.request.GET.get('department')
        if dept:
            queryset = queryset.filter(department=dept)
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

class RealizedBenefitEntryView(View):
    def get(self, request, pk):
        initiative = Initiative.objects.get(pk=pk)
        history = RealizedBenefit.objects.filter(initiative=initiative).order_by('-month')[:12]
        return render(request, 'initiatives/benefit_entry.html', {
            'initiative': initiative,
            'history': history,
            'benefit_types': [c[0] for c in RealizedBenefit.BENEFIT_TYPE_CHOICES]
        })

    def post(self, request, pk):
        initiative = Initiative.objects.get(pk=pk)
        month_str = request.POST.get('month')
        benefit_type = request.POST.get('benefit_type')
        amount = request.POST.get('amount')
        
        month = datetime.strptime(month_str, '%Y-%m').date()
        
        RealizedBenefit.objects.update_or_create(
            initiative=initiative,
            month=month,
            benefit_type=benefit_type,
            defaults={'amount': amount}
        )
        
        messages.success(request, "Realized benefit recorded successfully.")
        return redirect('benefit_entry', pk=pk)

class RealizedBenefitDeleteView(View):
    def post(self, request, pk):
        benefit = get_object_or_404(RealizedBenefit, pk=pk)
        initiative_pk = benefit.initiative.pk
        benefit.delete()
        messages.success(request, "Benefit entry deleted.")
        return redirect('benefit_entry', pk=initiative_pk)

class CSVDownloadView(View):
    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="initiatives_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Requester Name', 'Description', 'LOB Owner', 'IT Owner', 
            'Department', 'Status', 'Technology', 'Value', 
            'Benefit Name', 'Benefit'
        ])
        
        for initiative in Initiative.objects.all():
            writer.writerow([
                initiative.requester_name, initiative.description, initiative.lob_owner, initiative.it_owner,
                initiative.department, initiative.status, initiative.technology, initiative.value,
                initiative.benefit_name, initiative.benefit
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
            _, created = Initiative.objects.update_or_create(
                requester_name=column[0],
                defaults={
                    'description': column[1],
                    'lob_owner': column[2],
                    'it_owner': column[3],
                    'department': column[4],
                    'status': column[5],
                    'technology': column[6],
                    'value': column[7],
                    'benefit_name': column[8],
                    'benefit': column[9]
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
            'Requester Name', 'Description', 'LOB Owner', 'IT Owner', 
            'Department', 'Status', 'Technology', 'Value', 
            'Benefit Name', 'Benefit'
        ])
        writer.writerow([
            'John Doe', 'AI Chatbot for customer support', 'Claims', 'IT Team',
            'Claims', 'In-progress', 'OpenAI GPT-4', 'Reduce response time by 50%',
            'FTE Savings', '150000.0'
        ])
        return response
