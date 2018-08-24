# basket

![A fun fact about the humble egg](egg.jpg)

Did you know that egg is one of the most popular forms of child to eat?
Manage and control all of your cybernetic eggs with Basket™.

# Dependencies

- [Python 3](https://python.org/)
- [Flask](http://flask.pocoo.org/)
- [uWSGI](https://github.com/unbit/uwsgi)
- [Flask-uWSGI-WebSocket](https://github.com/zeekay/flask-uwsgi-websocket)
- [uwsgi-capture](https://github.com/milkey-mouse/uwsgi-capture)
- [netifaces](https://github.com/al45tair/netifaces)

For Bluetooth support (necessary to actually control eggs):

- [Adafruit_BluefruitLE](https://github.com/adafruit/Adafruit_Python_BluefruitLE) (⚠️ requires a [patch](https://github.com/milkey-mouse/basket/blob/666cfbb8dc21b3c750d0addbaf0d06cd280814b4/sw/Makefile#L32-L35) for newer versions of BlueZ)

(It's likely that you can skip manually installing these, as there is a Makefile that can automatically install them & prepare the server. See [the server README](sw/README.md).)
