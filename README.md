# Record Reviews
Record Reviews is a Python app that runs Flask and a MySQL database. It heavily relies on the Spotify API. It is formatted in Bootstrap and my own CSS. Its features include:

**Login Screen**
A standard login screen. Uses BCrypt to verify password and backend validations. Users may access the site without logging in but may not write reviews

**Home Page**
Displays the twelve most popular records according to the Spotify API. 

**Show Record**
Page for an individual record. Displays name, primary artist, and album artwork. Users may review the record from here. Displays other user's reviews and the average score of all reviews. 

**Other Features**
User page - displays all reviews from a given user. Search - most pages have a section where users can search for records by name. Show Review - displays full text of an individual review. Other users can like the review, and the author can delete it. No Album - displays when the URI for a nonexistent album into the route. 

