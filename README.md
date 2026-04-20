**PhotoPollApp**

A web app to share your photos with your friends to find the preferred one!

Functionality:
- Upload your photos;
- Vote your photos to find that one that most people like;
- Download, remove and comment your photo;
- Filter your photo by Most Recent, Less Recent, Most Voted.

All you need is your password and you can access the archive.


**SETUP**

You'll need a streamlit and a supabase account.
- _Supabase_:

    Create a public bucket called "PhotoPollApp".
  
    Set the policies "Give anon users access to JPG images in folder" in the policies section for all the operation.
  
    Copy your Project URL and your Secret Key (Project Settings -> API Keys -> Secret Keys)
  
    Go to "SQL Editor" and execute the sql_entry.sql query. 

- _Streamlit_:

  Create an app called photopollapp (or whatever you want) and link it with the main.py file.

  Go to the app settings and paste the secrets:

      SUPABASE_URL = "your_supabese_project_url"
  
      SUPABASE_KEY = "your_supabase_secret_key"
  
      PASSWORD_ACCESSO = "the_password_to_access_the_archive"


**ENJOY YOUR APP WITH YOUR FRIENDS**
  
