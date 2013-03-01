This is an example app to talk back to a shotgun server from a Heroku web dyno.
The resulting app can be used as the target of a Shotgun ActionMenuItem on Shots.
When you select some shots and launch the ActionMenuItem, the app will generate
a zip file containing a set of simple pdf reports for the shots.

Quick Install
-------------
Follow the instructions to setup a dev environment for Heroku here:
https://devcenter.heroku.com/articles/python

The short version
```bash
# Setup a Heroku account at https://www.heroku.com/
# Install the Heroku Toolbelf from https://toolbelt.heroku.com/

# Setup dependencies
cd $CLONED_GIT_DIRECTORY
heroku login
virtualenv venv --distribute
source venv/bin/activate
pip install -r requirements.txt

# Deploy the app
heroku create
git push heroku master

# Start up a Heroku dyno
heroku ps:scale web=1

# Setup config needed to connect to your Shotgun
# Full details at https://devcenter.heroku.com/articles/config-vars
heroku plugins:install git://github.com/ddollar/heroku-config.git
cp dot.env.sample .env
vi .env
heroku config:push

# Test out that you can hit up the app (this is a good way to get the target url)
heroku open

# Tail the logs and hit it up from the Shotgun ActionMenuItem
heroku logs -t
```
