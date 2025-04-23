from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse, resolve
from django.http import HttpResponseRedirect
from django.core.paginator import Paginator
from django.db import transaction
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login

from post.models import Post, Follow, Stream
from authy.models import Profile
from .forms import EditProfileForm, UserRegisterForm


@login_required
def UserProfile(request, username):
    # Ensure the logged-in user has a profile
    Profile.objects.get_or_create(user=request.user)

    user = get_object_or_404(User, username=username)
    profile = Profile.objects.get(user=user)
    url_name = resolve(request.path).url_name

    # Get user's posts or their favorites
    if url_name == 'profile':
        posts = Post.objects.filter(user=user).order_by('-posted')
    else:
        posts = profile.favourite.all()

    # Profile statistics
    posts_count = posts.count()
    following_count = Follow.objects.filter(follower=user).count()
    followers_count = Follow.objects.filter(following=user).count()
    follow_status = Follow.objects.filter(following=user, follower=request.user).exists()

    # Pagination
    paginator = Paginator(posts, 8)
    page_number = request.GET.get('page')
    posts_paginator = paginator.get_page(page_number)

    context = {
        'posts': posts_paginator,
        'profile': profile,
        'posts_count': posts_count,
        'following_count': following_count,
        'followers_count': followers_count,
        'follow_status': follow_status,
    }
    return render(request, 'profile.html', context)


@login_required
def EditProfile(request):
    # Ensure the profile exists for the logged-in user
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = EditProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('editprofile')  # Redirect after saving
        else:
            print("Form errors:", form.errors)  # Debugging (remove in production)
    else:
        form = EditProfileForm(instance=profile)

    return render(request, 'editprofile.html', {'form': form})

    


@login_required
def follow(request, username, option):
    following = get_object_or_404(User, username=username)

    try:
        f, created = Follow.objects.get_or_create(follower=request.user, following=following)

        if int(option) == 0:
            f.delete()
            Stream.objects.filter(following=following, user=request.user).delete()
        else:
            posts = Post.objects.filter(user=following)[:25]
            with transaction.atomic():
                Stream.objects.bulk_create([
                    Stream(post=post, user=request.user, date=post.posted, following=following)
                    for post in posts
                ])
        return HttpResponseRedirect(reverse('profile', args=[username]))

    except User.DoesNotExist:
        return HttpResponseRedirect(reverse('profile', args=[username]))


def register(request):
    if request.method == "POST":
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            new_user = form.save()
            Profile.objects.get_or_create(user=new_user)
            messages.success(request, "Hurray, your account was created!")

            # Auto login
            new_user = authenticate(username=new_user.username, password=request.POST['password1'])
            if new_user:
                login(request, new_user)

            return redirect('index')

    elif request.user.is_authenticated:
        return redirect('index')

    else:
        form = UserRegisterForm()

    context = {'form': form}
    return render(request, 'sign-up.html', context)
