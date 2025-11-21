# real-time chat system
a primitive but charming chat system put together with thoughts and prayers.

## technologies involved:
- backend: python
    - flask
    - socket.io
- frontend: vanilla HTML/CSS/Javascript
- db: sqlite *i needed something quick, forgive me*

## features:
- real-time messaging with websockets
- user authentication with password hashing
- multiple chatrooms
- complete markdown support
- emojis

# how to run
simply activate the virtual environment and run `app.py`

windows
```bash
./Scripts/Activate.ps1
python app.py
```
linux
```bash
source ./Scripts/activate
python app.py
```
your chat is now (hopefully) accessible at http://localhost

## considerations
this repository was made hastily because of an epiphanic realization that its worth having these dumb -- but charming -- projects on github. as a consequence of that, **this is in no way even CLOSE to production ready**. this repository's main purpose is to showcase a personal project.
