from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic.base import TemplateView
from .models import Request, Volunteer, DistrictManager, Contributor, DistrictNeed, Person, RescueCamp, NGO, Announcements
import django_filters
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import JsonResponse
from django.http import HttpResponseRedirect
from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.db.models import Count, QuerySet
from django.core.cache import cache
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.http import Http404
from mainapp.admin import create_csv_response

PER_PAGE = 100
PAGE_LEFT = 5
PAGE_RIGHT = 5
PAGE_INTERMEDIATE = "50"

class CreateRequest(CreateView):
    model = Request
    template_name='mainapp/request_form.html'
    fields = [
        'district',
        'location',
        'requestee',
        'requestee_phone',
        'is_request_for_others',
        'latlng',
        'latlng_accuracy',
        'needrescue',
        'detailrescue',
        'needwater',
        'detailwater',
        'needfood',
        'detailfood',
        'needcloth',
        'detailcloth',
        'needmed',
        'detailmed',
        'needkit_util',
        'detailkit_util',
        'needtoilet',
        'detailtoilet',
        'needothers'
    ]
    success_url = '/req_sucess/'


class RegisterVolunteer(CreateView):
    model = Volunteer
    fields = ['name', 'district', 'phone', 'organisation', 'area', 'address']
    success_url = '/reg_success/'


class RegisterNGO(CreateView):
    model = NGO
    fields = ['organisation', 'organisation_type','organisation_address', 'name', 'phone', 'description', 'area',
              'location']
    success_url = '/reg_success'


def download_ngo_list(request):
    district = request.GET.get('district', None)
    filename = 'ngo_list.csv'
    if district is not None:
        filename = 'ngo_list_{0}.csv'.format(district)
        qs = NGO.objects.filter(district=district).order_by('district','name')
    else:
        qs = NGO.objects.all().order_by('district','name')
    header_row = ['Organisation',
                  'Type',
                  'Address',
                  'Name',
                  'Phone',
                  'Description',
                  'District',
                  'Area',
                  'Location',
                  ]
    body_rows = qs.values_list(
        'organisation',
        'organisation_type',
        'organisation_address',
        'name',
        'phone',
        'description',
        'district',
        'area',
        'location',
    )
    return create_csv_response(filename, header_row, body_rows)

class RegisterContributor(CreateView):
    model = Contributor
    fields = ['name', 'district', 'phone', 'address',  'commodities']
    success_url = '/contrib_success/'


class HomePageView(TemplateView):
    template_name = "home.html"


class NgoVolunteerView(TemplateView):
    template_name = "ngo_volunteer.html"


class MapView(TemplateView):
    template_name = "mapview.html"


class ReqSuccess(TemplateView):
    template_name = "mainapp/req_success.html"

class RegSuccess(TemplateView):
    template_name = "mainapp/reg_success.html"


class ContribSuccess(TemplateView):
    template_name = "mainapp/contrib_success.html"

class DisclaimerPage(TemplateView):
    template_name = "mainapp/disclaimer.html"

class AboutIEEE(TemplateView):
    template_name = "mainapp/aboutieee.html"

class DistNeeds(TemplateView):
    template_name = "mainapp/district_needs.html"

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        # Add in a QuerySet of all the books
        context['district_data'] = DistrictNeed.objects.all()
        return context

class RescueCampFilter(django_filters.FilterSet):
    class Meta:
        model = RescueCamp
        fields = ['district']

    def __init__(self, *args, **kwargs):
        super(RescueCampFilter, self).__init__(*args, **kwargs)
        # at startup user doen't push Submit button, and QueryDict (in data) is empty
        if self.data == {}:
            self.queryset = self.queryset.none()

def relief_camps(request):
    filter = RescueCampFilter(request.GET, queryset=RescueCamp.objects.all())
    relief_camps = filter.qs.annotate(count=Count('person')).order_by('district','name').all()

    return render(request, 'mainapp/relief_camps.html', {'filter': filter , 'relief_camps' : relief_camps, 'district_chosen' : len(request.GET.get('district') or '')>0 })

class RequestFilter(django_filters.FilterSet):
    class Meta:
        model = Request
        # fields = ['district', 'status', 'needwater', 'needfood', 'needcloth', 'needmed', 'needkit_util', 'needtoilet', 'needothers',]

        fields = {
                    'district' : ['exact'],
                    'requestee' : ['icontains'],
                    'requestee_phone' : ['exact'],
                    'location' : ['icontains']
                 }

    def __init__(self, *args, **kwargs):
        super(RequestFilter, self).__init__(*args, **kwargs)
        # at startup user doen't push Submit button, and QueryDict (in data) is empty
        if self.data == {}:
            self.queryset = self.queryset.none()


def request_list(request):
    filter = RequestFilter(request.GET, queryset=Request.objects.all() )
    req_data = filter.qs.order_by('-id')
    paginator = Paginator(req_data, PER_PAGE)
    page = request.GET.get('page')
    req_data = paginator.get_page(page)
    req_data.min_page = req_data.number - PAGE_LEFT
    req_data.max_page = req_data.number + PAGE_RIGHT
    req_data.lim_page = PAGE_INTERMEDIATE
    return render(request, 'mainapp/request_list.html', {'filter': filter , "data" : req_data })

def request_details(request, request_id=None):
    if not request_id:
        return HttpResponseRedirect("/error?error_text={}".format('Page not found!'))
    filter = RequestFilter(None)
    try:
        req_data = Request.objects.get(id=request_id)
    except:
        return HttpResponseRedirect("/error?error_text={}".format('Sorry, we couldnt fetch details for that request'))
    return render(request, 'mainapp/request_details.html', {'filter' : filter, 'req': req_data })

class DistrictManagerFilter(django_filters.FilterSet):
    class Meta:
        model = DistrictManager
        fields = ['district']

    def __init__(self, *args, **kwargs):
        super(DistrictManagerFilter, self).__init__(*args, **kwargs)
        # at startup user doen't push Submit button, and QueryDict (in data) is empty
        if self.data == {}:
            self.queryset = self.queryset.none()

def districtmanager_list(request):
    filter = DistrictManagerFilter(request.GET, queryset=DistrictManager.objects.all())
    return render(request, 'mainapp/districtmanager_list.html', {'filter': filter})

class Maintenance(TemplateView):
    template_name = "mainapp/maintenance.html"


def mapdata(request):
    district = request.GET.get("district", "all")
    data = cache.get("mapdata:" + district)
    if data:
        return JsonResponse(list(data) , safe=False)
    if district != "all":
        data = Request.objects.exclude(latlng__exact="").filter(district=district).values()
    else:
        data = Request.objects.exclude(latlng__exact="").values()
    cache.set("mapdata:" + district, data, settings.CACHE_TIMEOUT)
    return JsonResponse(list(data) , safe=False)

def mapview(request):
    return render(request,"map.html")

def dmodash(request):
    return render(request , "dmodash.html")

def dmoinfo(request):
    if("district" not in request.GET.keys()):return HttpResponseRedirect("/")
    dist = request.GET.get("district")
    reqserve = Request.objects.all().filter(status = "sup" , district = dist).count()
    reqtotal = Request.objects.all().filter(district = dist).count()
    volcount = Volunteer.objects.all().filter(district = dist).count()
    conserve = Contributor.objects.all().filter(status = "ful" , district = dist).count()
    contotal = Contributor.objects.all().filter(district = dist).count()
    return render(request ,"dmoinfo.html",{"reqserve" : reqserve , "reqtotal" : reqtotal , "volcount" : volcount , "conserve" : conserve , "contotal" : contotal })

def error(request):
    error_text = request.GET.get('error_text')
    return render(request , "mainapp/error.html", {"error_text" : error_text})

def logout_view(request):
    logout(request)
    # Redirect to camps page instead
    return redirect('/relief_camps')

class PersonForm(forms.ModelForm):
    class Meta:
       model = Person
       fields = [
        'camped_at',
        'name',
        'phone',
        'age',
        'gender',
        'district',
        'address',
        'notes'
        ]

       widgets = {
           'address': forms.Textarea(attrs={'rows':3}),
           'notes': forms.Textarea(attrs={'rows':3}),
           'gender': forms.RadioSelect(),
        }


    def __init__(self, *args, **kwargs):
       camp_id = kwargs.pop('camp_id')
       super(PersonForm, self).__init__(*args, **kwargs)
       rescue_camp_qs = RescueCamp.objects.filter(id=camp_id)
       self.fields['camped_at'].queryset = rescue_camp_qs
       self.fields['camped_at'].initial = rescue_camp_qs.first()

class AddPerson(SuccessMessageMixin,LoginRequiredMixin,CreateView):
    login_url = '/login/'
    model = Person
    template_name='mainapp/add_person.html'
    form_class = PersonForm
    success_message = "'%(name)s' registered successfully"

    def get_success_url(self):
        return reverse('add_person', args=(self.camp_id,))

    def dispatch(self, request, *args, **kwargs):
        self.camp_id = kwargs.get('camp_id','')

        try:
            self.camp = RescueCamp.objects.get(id=int(self.camp_id))
        except ObjectDoesNotExist:
            raise Http404

        # Commented to allow all users to edit all camps
        # if request.user!=self.camp.data_entry_user:
        #     raise PermissionDenied

        return super(AddPerson, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(AddPerson, self).get_form_kwargs()
        kwargs['camp_id'] = self.camp_id
        return kwargs


class CampRequirementsForm(forms.ModelForm):
    class Meta:
       model = RescueCamp
       fields = [
        'name',
        'total_people',
        'total_males',
        'total_females',
        'total_infants',
        'food_req',
        'clothing_req',
        'sanitary_req',
        'medical_req',
        'other_req'
        ]
       read_only = ('name',)
       widgets = {
           'name': forms.Textarea(attrs={'rows':1,'readonly':True}),
           'food_req': forms.Textarea(attrs={'rows':3}),
           'clothing_req': forms.Textarea(attrs={'rows':3}),
           'medical_req': forms.Textarea(attrs={'rows':3}),
           'sanitary_req': forms.Textarea(attrs={'rows':3}),
           'other_req': forms.Textarea(attrs={'rows':3}),
       }

class CampRequirements(SuccessMessageMixin,LoginRequiredMixin,UpdateView):
    login_url = '/login/'
    model = RescueCamp
    template_name='mainapp/camp_requirements.html'  
    form_class = CampRequirementsForm
    success_url = '/coordinator_home/'
    success_message = "Updated requirements saved!"

    # Commented to allow all users to edit all camps
    # def dispatch(self, request, *args, **kwargs):
    #     if request.user!=self.get_object().data_entry_user:
    #         raise PermissionDenied
    #     return super(CampDetails, self).dispatch(
    #         request, *args, **kwargs)


class CampDetailsForm(forms.ModelForm):
    class Meta:
       model = RescueCamp
       fields = [
        'name',
        'location',
        'district',
        'taluk',
        'village',
        'contacts',
        'map_link',
        'latlng',
        ]

class CampDetails(SuccessMessageMixin,LoginRequiredMixin,UpdateView):
    login_url = '/login/'
    model = RescueCamp
    template_name='mainapp/camp_details.html'
    form_class = CampDetailsForm
    success_url = '/coordinator_home/'
    success_message = "Details saved!"

    # Commented to allow all users to edit all camps
    # def dispatch(self, request, *args, **kwargs):
    #     if request.user!=self.get_object().data_entry_user:
    #         raise PermissionDenied
    #     return super(CampDetails, self).dispatch(
    #         request, *args, **kwargs)


class PeopleFilter(django_filters.FilterSet):
    fields = ['name', 'phone','address','district','notes','gender','camped_at']

    class Meta:
        model = Person
        fields = {
            'name' : ['icontains'],
            'phone' : ['icontains'],
            'address' : ['icontains'],
            'district' : ['exact'],
            'notes':['icontains'],
            'gender':['exact'],
            'camped_at':['exact']
        }

        # TODO - field order seems to not be working!
        # field_order = ['name', 'phone', 'address','district','notes','gender','camped_at']

    def __init__(self, *args, **kwargs):
        super(PeopleFilter, self).__init__(*args, **kwargs)
        if self.data == {}:
            self.queryset = self.queryset.all()

def find_people(request):
    filter = PeopleFilter(request.GET, queryset=Person.objects.all())
    people = filter.qs.order_by('name','-added_at')
    paginator = Paginator(people, 50)
    page = request.GET.get('page')
    people = paginator.get_page(page)
    return render(request, 'mainapp/people.html', {'filter': filter , "data" : people })

class AnnouncementFilter(django_filters.FilterSet):
    class Meta:
        model = Announcements
        fields = ['district', 'category']

    def __init__(self, *args, **kwargs):
        super(AnnouncementFilter, self).__init__(*args, **kwargs)
        if self.data == {}:
            self.queryset = self.queryset.none()

def announcements(request):
    filter = AnnouncementFilter(request.GET, queryset=Announcements.objects.all())
    link_data = filter.qs.order_by('-id')
    # As per the discussions orddering by id hoping they would be addded in order
    paginator = Paginator(link_data, 10)
    page = request.GET.get('page')
    link_data = paginator.get_page(page)
    return render(request, 'announcements.html', {'filter': filter, "data" : link_data})

class CoordinatorCampFilter(django_filters.FilterSet):
    class Meta:
        model = RescueCamp
        fields = {
            'district' : ['exact'],
            'name' : ['icontains']
        }
    
    def __init__(self, *args, **kwargs):
        super(CoordinatorCampFilter, self).__init__(*args, **kwargs)
        if self.data == {}:
            self.queryset = self.queryset.none()

@login_required(login_url='/login/')
def coordinator_home(request):
    filter = CoordinatorCampFilter(request.GET, queryset=RescueCamp.objects.all())
    data = filter.qs.annotate(count=Count('person')).order_by('district','name').all()
    paginator = Paginator(data, 50)
    page = request.GET.get('page')
    data = paginator.get_page(page)

    return render(request, "mainapp/coordinator_home.html", {'filter': filter , 'data' : data})

class CampRequirementsFilter(django_filters.FilterSet):
    class Meta:
        model = RescueCamp
        fields = {
            'district' : ['exact'],
            'name' : ['icontains']
        }

    def __init__(self, *args, **kwargs):
        super(CampRequirementsFilter, self).__init__(*args, **kwargs)
        if self.data == {}:
            self.queryset = self.queryset.none()

def camp_requirements_list(request):
    filter = CampRequirementsFilter(request.GET, queryset=RescueCamp.objects.all())
    camp_data = filter.qs.order_by('name')
    paginator = Paginator(camp_data, 50)
    page = request.GET.get('page')
    data = paginator.get_page(page)
    return render(request, "mainapp/camp_requirements_list.html", {'filter': filter , 'data' : data})
