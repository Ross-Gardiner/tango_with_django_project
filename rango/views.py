from django.shortcuts import render


# Create your views here.
from django.http import HttpResponse

from rango.models import Category
from rango.models import Page
from rango.forms import CategoryForm, PageForm, UserForm, UserProfileForm

from django.contrib.auth import authenticate, login
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from datetime import datetime

def index(request):
	# Query the database for a list of ALL categories currently stored
	# Order the categories by no. likes in descending order.
	# REtrieve the top 5 only - or all if less than 5.
	# Place the list in our context_dict dictionary
	# that will be passed to the template engine
	request.session.set_test_cookie()
	category_list = Category.objects.order_by('-likes')[:5]
	page_list = Page.objects.order_by('-views')[:5]
	context_dict = {'categories':category_list, 'pages':page_list}

	visitor_cookie_handler(request)
	context_dict['visits'] = request.session['visits']

	#render the response and send it back!
	response = render(request, 'rango/index.html', context_dict)
	
	return response
def about(request):
	if request.session.test_cookie_worked():
		print("TEST COOKIE WORKED!")
		request.session.delete_test_cookie()
	visitor_cookie_handler(request)
	context_dict = {'visits':request.session['visits']}
	return render(request, 'rango/about.html', context_dict)
def show_category(request, category_name_slug):
    #Create a context dictionary which we can pass
    #to the template rendering engine
    context_dict = {}

    try:
        #Can we find a category name slug with the given name?
        #If we cant , the .get() method raises a DoesNotExist Exception.
        #So the .get() method returns one model instance or raises an exception
        category = Category.objects.get(slug=category_name_slug)

        #Retrieve all of the associated pages
        #Note that filter() will just return a list of page objects or an empty list
        pages = Page.objects.filter(category=category)
        
        #Adds our results list to the template context under name pages.
        context_dict['pages'] = pages
        #we also add the category object from
        #the database to the context dictionary.
        #we'll use this in the template to verify that the category exists.
        context_dict['category'] = category
    except Category.DoesNotExist:
        #We get here if we didn't find the specified category.
        #Don't do anything -
        #the template will display the "no category" message for us.
        context_dict['category'] = None
        context_dict['pages'] = None
     #Go render the response and return it to the client.
    return render(request, 'rango/category.html', context_dict)
@login_required
def add_category(request):
    form = CategoryForm()
    # A HTTP POST?
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        
        #Have we been provided with a valid form?
        if form.is_valid():
            #Save the new category is saved
            #We could give a confirmation messgae
            # but since te most recent category is added on the index page
            # we can direct the user back to the index page
            return index(request)
        else:
            # the supplied form contained errors 
            # just print to the terminal
            print(form.errors)
    #Will handle the bad form, new formm or no form supplied cases.
    #Render the form with error messages (if any)
    return render(request, 'rango/add_category.html',{'form':form})
@login_required
def add_page(request, category_name_slug):
	try:
		category = Category.objects.get(slug=category_name_slug)
	except Category.DoesNotExist:
		category = None
	form = PageForm()
	if request.method == 'POST':
		form = PageForm(request.POST)
		if form.is_valid():
			if category:
				page = form.save(commit=False)
				page.category = category
				page.views = 0
				page.save()
				return show_category(request, category_name_slug)
		else:
			print(form.errors)
	context_dict = {'form':form, 'category':category}
	return render(request, 'rango/add_page.html', context_dict)
def register(request):
	#a boolean value for telling te template
	#whether the registration was successful
	#set to false initially. code changes value to 
	#true when registration succeeds
	registered = False
	
	#If its a HTTP POST, we're interested in processing form data.
	if request.method == 'POST':
		#attempt to grab information from raw form information.
		#Note that we make use of both UserForm and UserProfileForm.
		user_form = UserForm(data=request.POST)
		profile_form = UserProfileForm(data=request.POST)
		
		#if the two forms are valid...
		if user_form.is_valid() and profile_form.is_valid():
			#Save the user's form data to the database.
			user = user_form.save()
			
			#Now we hash the password with the set_password method.
			#Once hashed, we can update the user object.
					
			user.set_password(user.password)
			user.save()
			#now sort out the UserProfile instance.
			#Since we need to set the user attribute ourselves, 
			#we set commit=False. This delays saving the model
			#until we're ready to avoid integrity problems.
			profile = profile_form.save(commit=False)
			profile.user = user
			
			#Did the user provide a profile picture?
			#If so , we need to get it from the input form and 
			#put it in the UserProfile model.
			if 'picture' in request.FILES:
				profile.picture = request.FILES['picture']
			#now we save the UserProfile model instance
			profile.save()
			
			#update our variable to indicate that the template 
			#registration was successful
			registered = True
		else:
			#invalid form or forms - mistakes or something else?
			# print problems to the terminal.
			print(user_form.errors, profile_form.errors)
	else:
		#not a HTTP POST, so we render our form using two ModelForm instances. 
		#These forms will be blank, ready for user input.
		user_form = UserForm()
		profile_form = UserProfileForm()
	#render the template depending on the context.
	return render(request,
				  'rango/register.html',
				  {'user_form': user_form,
				   'profile_form': profile_form,
				   'registered' : registered})
@login_required
def restricted(request):
	return HttpResponse("Since you're logged in, you can see this text!")
def user_login(request):
	#if the request is a HTTP POST, try to pull out the relevant information
	if request.method == 'POST':
		#Gather the username and password provided by the user.
		#this information is obtained from the login form.
		#we use request.POST['<variable>'] as opposed 
		#to request.POST.get('<variable>') returns None if the 
		#value does not exist, while request.POST['<variable>']
		#will raise a KeyError exception
		username = request.POST.get('username')
		password = request.POST.get('password')
		
		#use django's machinery to attempt to see is the username/password
		#combonation is valid - a user object is returned if it is.
		user = authenticate(username=username, password=password)
		
		#if we have a user object, the details are correct.
		#if none , no user with matching credentials 
		#was found
		if user:
			#is the account active? It could have been disabled.
			if user.is_active:
				#if the account is valid and active, we can log the user in.
				#we'll send the user back to the homepage
				login(request, user)
				return HttpResponseRedirect(reverse('index'))
			else:
				#An inactive account was used - no logging in!
				return HttpResponse("Your Rango account is disabled.")
		else:
			#bad login details were provided. so we cant log the user in
			print("Invalid login details: {0}, {1}".format(username, password))
			return HttpResponse("Invalid login details supplied.")
		#The request is not a HTTP POST, so display the login form.
		#this scenario would most likely be a HTTP GET
	else:
		#no context variables to pass to the template system, hence the
		#blank dictionary object
		return render(request, 'rango/login.html', {})
@login_required
def user_logout(request):
	# since we know the user is logged in, we can now just log them out 
	logout(request)
	#take the user back to the homepage
	return HttpResponseRedirect(reverse('index'))
def get_server_side_cookie(request, cookie, default_val=None):
	val = request.session.get(cookie)
	if not val:
		val = default_val
	return val

#updated the function
def visitor_cookie_handler(request):
	#get the number of visitors to the site
	#we use the COOKIES.get() function to obtain the visits cookie
	#if the cookie exists, the value returned is castedto an integer
	#if the cookie doesnt exist, then the default value of 1 is used.
	visits = int(get_server_side_cookie(request,'visits','1'))
	last_visit_cookie = get_server_side_cookie(request,
												'last_visit',
												str(datetime.now()))
	last_visit_time = datetime.strptime(last_visit_cookie[:-7],
										'%Y-%m-%d %H:%M:%S')
	#if its been more than a day since the last visit...
	if (datetime.now() - last_visit_time).days >0:
		visits = visits + 1
		#update the last visit cookie now that we have updated the count
		request.session['last_visit'] = str(datetime.now())
	else:
		visits = 1
		#set the last visit cookie 
		request.session['last_visit'] = last_visit_cookie
	#update/set the visits cookie
	request.session['visits'] = visits








