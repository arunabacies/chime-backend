## Add the User Roles
```
from app.models import *
from app import db
for r in ["Admin", "Manger", "Client", "Engineer", "Crew", "Presenter", "Bot"]:
    u = UserRole(name=r)
    db.session.add(u)   
    db.session.commit()

```
##Add default time zone
```
t = TimeZone(zone="Asia/Kolkata",value="+5:30")
db.session.add(t)
db.session.commit()
```

```
# Add one Admin
```
from app.models import *
from app import db
user = User(name='Prabhu Rajan', user_role=1, email='prabhu@abacies.com', registered=True)
db.session.add(user)
db.session.commit()
user.hash_password("Abacies@Test@123")
db.session.add(user)
db.session.commit()
# Add default area
<!-- from app.models import *
from app import db
a = Area(name='empty')
db.session.add(a)
db.session.commit() -->
# Add Project Manager
user = User(name='Smijith', user_role=2, email='smijith@abacies.com', registered=True)
db.session.add(user)
db.session.commit()
user.hash_password("Abacies@Test@123")
db.session.add(user)
db.session.commit()

# Add Engineer
user = User(name='Arun', user_role=1, email='arun_n_a@abacies.com', registered=True)
db.session.add(user)
db.session.commit()
user.hash_password("Abacies@123")
db.session.add(user)
db.session.commit()
