from django import forms
from .models import ClubApplication, ClubCategory, Faculty


class ClubFilterForm(forms.Form):
    """Form for filtering clubs"""
    category = forms.ModelChoiceField(
        queryset=ClubCategory.objects.all(),
        required=False,
        empty_label="All Categories"
    )
    faculty = forms.ModelChoiceField(
        queryset=Faculty.objects.all(),
        required=False,
        empty_label="All Faculties"
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Search clubs...'})
    )
    SORT_CHOICES = [
        ('popular', 'Most Popular'),
        ('newest', 'Newest First'),
        ('oldest', 'Oldest First'),
        ('alphabetical', 'A-Z'),
    ]
    sort = forms.ChoiceField(
        choices=SORT_CHOICES,
        required=False,
        initial='popular'
    )


class ClubApplicationForm(forms.ModelForm):
    """Form for creating a new club application"""

    # Override fields to add widgets and validation
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Club Name',
        })
    )

    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Describe your club and its purpose',
            'rows': 4
        })
    )

    founder_faculty = forms.ModelChoiceField(
        queryset=Faculty.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    founder_year = forms.IntegerField(
        min_value=1,
        max_value=6,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Current Year of Study'
        })
    )

    founder_motivation = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Why do you want to create this club?',
            'rows': 3
        })
    )

    goals = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'What are the main goals of this club?',
            'rows': 3
        })
    )

    activities = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'What activities will this club organize?',
            'rows': 3
        })
    )

    meeting_frequency = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'How often will the club meet?'
        })
    )

    min_members = forms.IntegerField(
        min_value=3,
        initial=5,
        widget=forms.NumberInput(attrs={
            'class': 'form-control'
        })
    )

    faculty_advisor = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Faculty Advisor (if any)'
        })
    )

    logo = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        })
    )

    supporting_document = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.doc,.docx'
        })
    )

    class Meta:
        model = ClubApplication
        fields = [
            'name', 'description', 'category',
            'founder_faculty', 'founder_year', 'founder_motivation',
            'goals', 'activities', 'meeting_frequency',
            'min_members', 'faculty_advisor', 'logo', 'supporting_document'
        ]
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name')

        # Check if a club with this name already exists
        from .models import Club
        if Club.objects.filter(name__iexact=name).exists():
            self.add_error('name', 'A club with this name already exists')

        return cleaned_data