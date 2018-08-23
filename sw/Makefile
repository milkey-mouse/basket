.PHONY: run bluefruit-le db cert clean

BLUETOOTH_DEPENDENCIES := $(shell command -v bluetoothd > /dev/null && echo bluefruit-le || true)
VIDEO_DEPENDENCIES := $(shell [ -e /dev/video0 ] && echo capture_plugin.so || true)

BLUETOOTH_MULE := --mule=basket.worker:$(shell (command -v bluetoothd > /dev/null && echo run_worker) || echo run_dummy_worker)
VIDEO_MULE := $(shell [ -e /dev/video0 ] && echo --plugin capture --v4l-device /dev/video0 || true)

run: venv instance ${BLUETOOTH_DEPENDENCIES} ${VIDEO_DEPENDENCIES}
	venv/bin/uwsgi --master --http 0.0.0.0:5000 --http-websockets --wsgi basket.run:app --processes 4 --threads 2 \
	--mule-msg-size=4096 ${BLUETOOTH_MULE} ${BLUETOOTH_MULE} ${BLUETOOTH_MULE} ${BLUETOOTH_MULE} ${BLUETOOTH_MULE} ${VIDEO_MULE}

uwsgi-capture:
	rm -rf uwsgi-capture *-uwsgi-capture-*
	curl -L https://api.github.com/repos/milkey-mouse/uwsgi-capture/tarball/master | tar -zx
	mv *-uwsgi-capture-* uwsgi-capture

capture_plugin.so: venv uwsgi-capture
	cd uwsgi-capture && ../venv/bin/uwsgi --build-plugin . && cp *.so ..

Adafruit_BluefruitLE: venv
	rm -rf Adafruit_BluefruitLE *-Adafruit_Python_BluefruitLE-*
	curl -L https://api.github.com/repos/adafruit/Adafruit_Python_BluefruitLE/tarball/master | tar -zx
        ifeq (1,$(shell (command -v bluetoothd && bluetoothd -v) | awk '{print (0$1 > 5.37)}'))
		# https://github.com/adafruit/Adafruit_Python_BluefruitLE/issues/23
		cd *-Adafruit_Python_BluefruitLE-* && curl -L https://github.com/adafruit/Adafruit_Python_BluefruitLE/files/1129534/gatt_fix_characteristics_bluez_5.38.patch.txt | patch -p1
        endif
	mv *-Adafruit_Python_BluefruitLE-* Adafruit_BluefruitLE

bluefruit-le: venv Adafruit_BluefruitLE
	(venv/bin/python3 -c 'from importlib.util import find_spec;from sys import exit;exit(find_spec("Adafruit_BluefruitLE") is None)' && venv/bin/python3 -m pip install -U Adafruit_BluefruitLE) || true

instance: venv
        ifeq (,$(wildcard instance/basket.sqlite))
		mkdir -p instance
		FLASK_APP=basket venv/bin/flask init-db
        endif

venv:
	python3 -m venv venv --system-site-packages
	venv/bin/python3 -m pip install -Ur requirements.txt
	# only install bluetooth stuff if bluez userland tools are already installed
	(command -v bluetoothd > /dev/null && venv/bin/python3 -m pip install -Ur requirements.d/bluetooth.txt) || true

cert: instance
	openssl req -x509 -nodes -sha256 -days 365 -newkey rsa:4096 -keyout instance/self-signed.key -out instance/self-signed.crt -subj "/CN=`hostname`"

clean:
	rm -rf venv instance uwsgi-capture *-uwsgi-capture-* capture_plugin.so Adafruit_BluefruitLE *-Adafruit_Python_BluefruitLE-*
