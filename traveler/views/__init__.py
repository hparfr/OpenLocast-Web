import codecs
import settings

from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.contrib.sites.models import get_current_site
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.utils import simplejson

from locast import get_model

from traveler.forms import EditProfileForm, RegisterForm, RegisterProfileForm
from traveler.models import Cast, UserActivity, UserConfirmation, Boundry

def frontpage(request):
    fragment = request.GET.get('_escaped_fragment_')
    if fragment:
        return content_page(request, fragment)

    login_form = AuthenticationForm(request)
    edit_profile_form = None
    if request.user.is_authenticated:
        edit_profile_form = EditProfileForm(user = request.user)

    return render_to_response('frontpage.django.html', locals(), context_instance = RequestContext(request))


def content_page(request, fragment):
    fragment = fragment.split('/');
    if len(fragment) < 2:
        raise Http404

    model = get_model(fragment[0])
    if not model or (not model == Cast):
        raise Http404

    try:
        id = int(fragment[1])
    except ValueError:
        raise Http404

    cast = get_object_or_404(model, id=id)

    return render_to_response('cast_view.django.html', locals(), context_instance = RequestContext(request))


def register(request):
    form = None
    profile_form = None

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        profile_form = RegisterProfileForm(request.POST)
        if form.is_valid() and profile_form.is_valid():
            user = form.save()

            # Create a UserActivity
            UserActivity.objects.create_activity(user, user, 'joined')

            # IF confirmation is turned on, the user is inactive until they confirm
            if settings.USER_CONFIRMATION:
                user.is_active = False

            user.save()

            # Create a profile
            profile = profile_form.save(commit = False)
            profile.user = user
            profile.save()

            uc = None
            # Send confirmation email
            if settings.USER_CONFIRMATION:
                uc = UserConfirmation.objects.create_confirmation(user)
                site_name = get_current_site(request).name
                uc.send_confirmation_email('Welcome to ' + site_name + '!')

            user_image = request.FILES.get('user_image', None)
            if user_image:
                profile.user_image.save(user_image.name, user_image, save=True)
            
            profile.save()

            # If user confirmation is off, redirect to the login url
            if not uc:
                return HttpResponseRedirect(settings.LOGIN_URL)

    elif request.method == 'GET':
        form = RegisterForm()
        profile_form = RegisterProfileForm

    return render_to_response('registration/register.django.html', locals(), context_instance = RequestContext(request))


def edit_profile(request):
    form = None
    success = False

    if request.method == 'POST': # If the form has been submitted...
        form = EditProfileForm(data = request.POST, user = request.user) # A form bound to the POST data
        if form.is_valid():
            form.save()
            success = True
            #return HttpResponseRedirect(settings.FULL_BASE_URL)

    elif request.method == 'GET':
        form = EditProfileForm()

    return render_to_response('registration/edit_profile.django.html', locals(), context_instance = RequestContext(request))


def traveler_js(request):
    boundry_obj = Boundry.objects.get_default_boundry()
    boundry = 'null';

    if boundry_obj:
        boundry = boundry_obj.bounds.geojson

    return render_to_response('traveler.django.js', locals(), 
        context_instance = RequestContext(request), mimetype='text/javascript')


def templates_js(request):

    # TODO: Do this in a not terrible way
    template_dir = settings.STATIC_ROOT + 'js/templates/'

    template_files = [
        'castAddForm.js.html',
        'castClusterPopup.js.html',
        'castComments.js.html',
        'castHeaderList.js.html',
        'castPopup.js.html',
        'collectionHeaderList.js.html',
        'collectionPopup.js.html',
        'mapCastList.js.html',
        'searchResults.js.html',
        'userOpen.js.html'
    ]

    templates = {}
    for tf in template_files:
        try:
            ofile = codecs.open(template_dir + tf, encoding='utf8')
            templates[tf] = ofile.read()
        except IOError:
            pass
        
    content = 'var templates = ' + simplejson.dumps(templates);

    return HttpResponse(status=200, mimetype='application/json; charset=utf-8', content=content)
